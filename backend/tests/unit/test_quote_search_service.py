"""Unit tests for quote list status/tag filtering helpers."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.eworks_sync import EworksQuote
from app.services.manager_dashboard_service import BOOKED_TAG, MUST_ATTEND_TAG
from app.services.quote_search_service import (
    filter_quotes_in_python,
    paginate_eworks_quotes,
    quote_has_booked_tag,
    quote_is_draft,
    quote_matches_list_filters,
    quote_matches_status_filter,
    quote_matches_tag_filter,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    EworksQuote.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_quote(**kwargs) -> EworksQuote:
    defaults = {"eworks_quote_id": 1, "quote_ref": "Q-1", "customer_name": "Test Co"}
    defaults.update(kwargs)
    return EworksQuote(**defaults)


def _filter_status_one_and_booked(db_session):
    q = db_session.query(EworksQuote)
    rows, _ = paginate_eworks_quotes(
        q,
        status="1",
        tag=BOOKED_TAG,
        limit=200,
        offset=0,
        order_col=EworksQuote.eworks_quote_id,
    )
    return rows


def test_status_one_returns_only_draft_quotes(db_session):
    db_session.add_all(
        [
            _make_quote(eworks_quote_id=101, status="1", status_name="Draft"),
            _make_quote(eworks_quote_id=102, status="5", status_name="Call Back"),
            _make_quote(eworks_quote_id=103, status="4", status_name="Processed"),
        ]
    )
    db_session.commit()

    q = db_session.query(EworksQuote)
    rows, total = paginate_eworks_quotes(
        q,
        status="1",
        tag=None,
        limit=50,
        offset=0,
        order_col=EworksQuote.eworks_quote_id,
    )
    ids = {row.eworks_quote_id for row in rows}

    assert total == 1
    assert ids == {101}


def test_draft_booked_included(db_session):
    """Case 1: Draft + Booked -> included."""
    db_session.add(
        _make_quote(eworks_quote_id=201, status="1", status_name="Draft", tags=[BOOKED_TAG])
    )
    db_session.commit()

    rows = _filter_status_one_and_booked(db_session)
    assert len(rows) == 1
    assert rows[0].eworks_quote_id == 201


def test_call_back_booked_excluded(db_session):
    """Case 2: Call Back + Booked -> excluded."""
    db_session.add(
        _make_quote(
            eworks_quote_id=202,
            status="5",
            status_name="Call Back",
            tags=[BOOKED_TAG],
            raw_payload={"id": 202, "quote_status": {"id": 5, "quote_status": "Call Back"}},
        )
    )
    db_session.commit()

    assert _filter_status_one_and_booked(db_session) == []


def test_processed_booked_excluded(db_session):
    """Case 3: Processed + Booked -> excluded."""
    db_session.add(
        _make_quote(
            eworks_quote_id=203,
            status="4",
            status_name="Processed",
            tags=[BOOKED_TAG],
            raw_payload={"quote_status": {"id": 4, "quote_status": "Processed"}},
        )
    )
    db_session.commit()

    assert _filter_status_one_and_booked(db_session) == []


def test_accepted_booked_excluded(db_session):
    """Case 4: Accepted/Approved + Booked -> excluded."""
    db_session.add(
        _make_quote(
            eworks_quote_id=204,
            status="3",
            status_name="Approved",
            tags=[BOOKED_TAG],
            raw_payload={"quote_status": {"id": 3, "quote_status": "Approved"}},
        )
    )
    db_session.commit()

    assert _filter_status_one_and_booked(db_session) == []


def test_rejected_booked_excluded(db_session):
    """Case 5: Rejected + Booked -> excluded."""
    db_session.add(
        _make_quote(
            eworks_quote_id=205,
            status="6",
            status_name="Rejected",
            tags=[BOOKED_TAG],
            raw_payload={"quote_status": {"id": 6, "quote_status": "Rejected"}},
        )
    )
    db_session.commit()

    assert _filter_status_one_and_booked(db_session) == []


def test_draft_must_attend_excluded_when_tag_booked(db_session):
    """Case 6: Draft + Must Attend -> excluded when tag=Booked."""
    db_session.add(
        _make_quote(
            eworks_quote_id=206,
            status="1",
            status_name="Draft",
            tags=[MUST_ATTEND_TAG],
        )
    )
    db_session.commit()

    assert _filter_status_one_and_booked(db_session) == []


def test_draft_booked_priority_included(db_session):
    """Case 7: Draft + Booked + Priority -> included."""
    db_session.add(
        _make_quote(
            eworks_quote_id=207,
            status="1",
            status_name="Draft",
            tags=[BOOKED_TAG, "Priority (Quotes)"],
        )
    )
    db_session.commit()

    rows = _filter_status_one_and_booked(db_session)
    assert len(rows) == 1
    assert rows[0].eworks_quote_id == 207


def test_unrelated_raw_id_one_status_three_excluded(db_session):
    """Case 8: raw_payload unrelated id=1 but status 3 -> excluded."""
    db_session.add(
        _make_quote(
            eworks_quote_id=208,
            status="3",
            status_name="Approved",
            tags=[BOOKED_TAG],
            raw_payload={"id": 1, "customer_id": 1, "quote_status": {"id": 3}},
        )
    )
    db_session.commit()

    assert _filter_status_one_and_booked(db_session) == []


def test_status_one_and_booked_combined_filter(db_session):
    db_session.add_all(
        [
            _make_quote(eworks_quote_id=301, status="1", status_name="Draft", tags=[BOOKED_TAG]),
            _make_quote(eworks_quote_id=302, status="5", status_name="Call Back", tags=[BOOKED_TAG]),
            _make_quote(
                eworks_quote_id=303,
                status="1",
                status_name="Draft",
                tags=["Awaiting Supplier Info (Quotes)"],
            ),
        ]
    )
    db_session.commit()

    rows = _filter_status_one_and_booked(db_session)
    assert len(rows) == 1
    assert rows[0].eworks_quote_id == 301
    for row in rows:
        assert quote_is_draft(row)
        assert quote_has_booked_tag(row)


def test_tag_only_filter_returns_all_booked(db_session):
    db_session.add_all(
        [
            _make_quote(eworks_quote_id=501, status="1", tags=[BOOKED_TAG]),
            _make_quote(eworks_quote_id=502, status="5", tags=[BOOKED_TAG]),
        ]
    )
    db_session.commit()

    q = db_session.query(EworksQuote)
    rows, total = paginate_eworks_quotes(
        q,
        status=None,
        tag=BOOKED_TAG,
        limit=50,
        offset=0,
        order_col=EworksQuote.eworks_quote_id,
    )
    ids = {row.eworks_quote_id for row in rows}

    assert total == 2
    assert ids == {501, 502}


def test_status_only_filter_returns_all_draft(db_session):
    db_session.add_all(
        [
            _make_quote(eworks_quote_id=601, status="1", tags=[BOOKED_TAG]),
            _make_quote(eworks_quote_id=602, status="1", tags=[]),
            _make_quote(eworks_quote_id=603, status="5", tags=[BOOKED_TAG]),
        ]
    )
    db_session.commit()

    q = db_session.query(EworksQuote)
    rows, total = paginate_eworks_quotes(
        q,
        status="1",
        tag=None,
        limit=50,
        offset=0,
        order_col=EworksQuote.eworks_quote_id,
    )

    assert total == 2
    assert {row.eworks_quote_id for row in rows} == {601, 602}


def test_status_filter_does_not_match_status_name_text():
    quote = _make_quote(status="5", status_name="1")
    assert quote_is_draft(quote) is False
    assert quote_matches_status_filter(quote, "1") is False


def test_status_filter_does_not_match_loose_raw_id(db_session):
    """status=1 must not match unrelated raw_payload id fields (e.g. customer_id: 1)."""
    db_session.add_all(
        [
            _make_quote(
                eworks_quote_id=701,
                status="5",
                status_name="Call Back",
                raw_payload={"id": 701, "customer_id": 1, "quote_status": {"id": 5}},
            ),
            _make_quote(
                eworks_quote_id=710,
                status="5",
                status_name="Call Back",
                raw_payload={"id": 710},
            ),
        ]
    )
    db_session.commit()

    q = db_session.query(EworksQuote)
    rows, total = paginate_eworks_quotes(
        q,
        status="1",
        tag=None,
        limit=50,
        offset=0,
        order_col=EworksQuote.eworks_quote_id,
    )

    assert total == 0
    assert rows == []


def test_status_filter_matches_raw_payload_status_when_column_empty(db_session):
    db_session.add(
        _make_quote(
            eworks_quote_id=801,
            status=None,
            raw_payload={"status": "1", "quote_status": {"id": 1, "quote_status": "Draft"}},
        )
    )
    db_session.commit()

    q = db_session.query(EworksQuote)
    rows, total = paginate_eworks_quotes(
        q,
        status="1",
        tag=None,
        limit=50,
        offset=0,
        order_col=EworksQuote.eworks_quote_id,
    )

    assert total == 1
    assert rows[0].eworks_quote_id == 801


def test_tag_filter_does_not_match_unrelated_raw_payload(db_session):
    db_session.add(
        _make_quote(
            eworks_quote_id=901,
            status="1",
            tags=[],
            raw_payload={"description": "Booked for delivery next week"},
        )
    )
    db_session.commit()

    q = db_session.query(EworksQuote)
    rows, total = paginate_eworks_quotes(
        q,
        status=None,
        tag=BOOKED_TAG,
        limit=50,
        offset=0,
        order_col=EworksQuote.eworks_quote_id,
    )

    assert total == 0
    assert rows == []
    assert quote_matches_tag_filter(_make_quote(tags=[], raw_payload={"description": "Booked for delivery"}), BOOKED_TAG) is False


def test_paginate_eworks_quotes_applies_offset_after_python_filter(db_session):
    db_session.add_all(
        [
            _make_quote(eworks_quote_id=1001, status="1", tags=[BOOKED_TAG]),
            _make_quote(eworks_quote_id=1002, status="1", tags=[BOOKED_TAG]),
            _make_quote(eworks_quote_id=1003, status="1", tags=[BOOKED_TAG]),
        ]
    )
    db_session.commit()

    q = db_session.query(EworksQuote)
    page, total = paginate_eworks_quotes(
        q,
        status="1",
        tag=BOOKED_TAG,
        limit=1,
        offset=1,
        order_col=EworksQuote.eworks_quote_id,
    )

    assert total == 3
    assert len(page) == 1
    assert page[0].eworks_quote_id == 1002


def test_quote_matches_list_filters_requires_strict_and(db_session):
    draft_booked = _make_quote(status="1", tags=[BOOKED_TAG])
    call_back_booked = _make_quote(status="5", tags=[BOOKED_TAG])
    draft_other = _make_quote(status="1", tags=["Awaiting Supplier Info (Quotes)"])

    assert quote_matches_list_filters(draft_booked, "1", BOOKED_TAG) is True
    assert quote_matches_list_filters(call_back_booked, "1", BOOKED_TAG) is False
    assert quote_matches_list_filters(draft_other, "1", BOOKED_TAG) is False

    filtered = filter_quotes_in_python([draft_booked, call_back_booked, draft_other], "1", BOOKED_TAG)
    assert filtered == [draft_booked]
