from app.services.eworks_quote_status import resolve_eworks_quote_status_label


def test_resolve_status_id_one_to_draft():
    assert resolve_eworks_quote_status_label(status="1") == "Draft"


def test_resolve_status_id_two_to_pending():
    assert resolve_eworks_quote_status_label(status="2") == "Pending"


def test_resolve_status_id_three_to_approved():
    assert resolve_eworks_quote_status_label(status="3") == "Approved"


def test_resolve_status_id_nine_to_closed():
    assert resolve_eworks_quote_status_label(status="9") == "Closed"


def test_prefers_explicit_status_name_over_id_map():
    assert (
        resolve_eworks_quote_status_label(
            status="1",
            status_name="Awaiting Approval",
        )
        == "Awaiting Approval"
    )


def test_resolves_from_raw_payload_quote_status():
    assert (
        resolve_eworks_quote_status_label(
            status=None,
            raw_payload={"quote_status": {"id": "2", "quote_status": "Pending"}},
        )
        == "Pending"
    )


def test_ignores_numeric_status_name_and_uses_id_map():
    assert resolve_eworks_quote_status_label(status="1", status_name="1") == "Draft"


def test_extract_quote_fields_backfills_status_name():
    from app.services.eworks_sync_service import _extract_quote_fields

    fields = _extract_quote_fields({"id": 100, "quote_ref": "Q-100", "status": "1"})
    assert fields["status"] == "1"
    assert fields["status_name"] == "Draft"
