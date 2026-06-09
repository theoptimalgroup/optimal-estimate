"""Tests for the eWorks incremental recent quote sync feature."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.eworks_sync_service import (
    _is_quote_recent,
    _parse_eworks_datetime,
    sync_quotes_incremental_recent,
)


# ---------------------------------------------------------------------------
# _parse_eworks_datetime
# ---------------------------------------------------------------------------

class TestParseEworksDatetime:
    def test_plain_iso_no_timezone_treated_as_utc(self):
        dt = _parse_eworks_datetime("2024-01-15T10:30:00")
        assert dt is not None
        assert dt.tzinfo is not None
        assert dt.hour == 10

    def test_fractional_seconds_stripped_before_parse(self):
        dt = _parse_eworks_datetime("2024-01-15T10:30:00.123456")
        assert dt is not None
        assert dt.second == 0
        assert dt.microsecond == 0

    def test_timezone_aware_iso_preserved(self):
        dt = _parse_eworks_datetime("2024-01-15T10:30:00+00:00")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_none_returns_none(self):
        assert _parse_eworks_datetime(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_eworks_datetime("") is None

    def test_invalid_string_returns_none(self):
        assert _parse_eworks_datetime("not-a-date") is None

    def test_partial_string_returns_none(self):
        assert _parse_eworks_datetime("2024-13-99") is None


# ---------------------------------------------------------------------------
# _is_quote_recent
# ---------------------------------------------------------------------------

class TestIsQuoteRecent:
    @pytest.fixture()
    def cutoff(self):
        return datetime.now(timezone.utc) - timedelta(hours=1)

    def test_created_within_window_is_recent(self, cutoff):
        raw = {
            "created_on": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
            "last_updated_on": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
        }
        is_recent, has_invalid = _is_quote_recent(raw, cutoff)
        assert is_recent is True
        assert has_invalid is False

    def test_last_updated_within_window_is_recent(self, cutoff):
        raw = {
            "created_on": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "last_updated_on": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        }
        is_recent, has_invalid = _is_quote_recent(raw, cutoff)
        assert is_recent is True
        assert has_invalid is False

    def test_old_quote_not_recent(self, cutoff):
        raw = {
            "created_on": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "last_updated_on": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
        }
        is_recent, has_invalid = _is_quote_recent(raw, cutoff)
        assert is_recent is False
        assert has_invalid is False

    def test_invalid_date_returns_has_invalid_true(self, cutoff):
        raw = {"created_on": "not-a-date", "last_updated_on": "also-not-a-date"}
        is_recent, has_invalid = _is_quote_recent(raw, cutoff)
        assert is_recent is False
        assert has_invalid is True

    def test_missing_dates_not_invalid(self, cutoff):
        raw = {"id": 123}
        is_recent, has_invalid = _is_quote_recent(raw, cutoff)
        assert is_recent is False
        assert has_invalid is False

    def test_fractional_seconds_parsed_correctly(self, cutoff):
        raw = {
            "created_on": (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime(
                "%Y-%m-%dT%H:%M:%S.123456"
            ),
            "last_updated_on": None,
        }
        is_recent, has_invalid = _is_quote_recent(raw, cutoff)
        assert is_recent is True


# ---------------------------------------------------------------------------
# sync_quotes_incremental_recent — integration with mocked API
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)
_RECENT_QUOTE = {
    "id": 1001,
    "quote_ref": "Q-RECENT",
    "created_on": (_NOW - timedelta(minutes=20)).isoformat(),
    "last_updated_on": (_NOW - timedelta(minutes=5)).isoformat(),
}
_OLD_QUOTE = {
    "id": 1002,
    "quote_ref": "Q-OLD",
    "created_on": (_NOW - timedelta(days=30)).isoformat(),
    "last_updated_on": (_NOW - timedelta(days=10)).isoformat(),
}
_NEW_QUOTE = {
    "id": 1003,
    "quote_ref": "Q-NEW",
    "created_on": (_NOW - timedelta(minutes=2)).isoformat(),
    "last_updated_on": (_NOW - timedelta(minutes=1)).isoformat(),
}


def _make_page_result(records, current_page=1, last_page=1):
    from app.services.eworks_quotes_jobs_api_service import QuotePageResult
    return QuotePageResult(records=records, current_page=current_page, last_page=last_page)


def _make_db_session():
    """Create an in-memory SQLite session for unit tests."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.models.eworks_sync import EworksSyncRun

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    EworksSyncRun.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    return Session()


class TestSyncQuotesIncrementalRecent:
    def test_only_recent_quotes_upserted(self):
        """Old quotes are skipped; only quotes in the window are passed to upsert."""
        db = _make_db_session()

        page = _make_page_result(
            [_RECENT_QUOTE, _OLD_QUOTE, _NEW_QUOTE], current_page=1, last_page=1
        )

        with patch("app.services.eworks_sync_service.fetch_quote_page", return_value=page):
            with patch("app.services.eworks_sync_service._upsert_quotes") as mock_upsert:
                from app.schemas.eworks_sync_api import EworksSyncBucketSummary
                mock_upsert.return_value = EworksSyncBucketSummary(fetched=2, created=1, updated=1)

                summary, run = sync_quotes_incremental_recent(db, window_minutes=60, timeout_seconds=30)

        upserted_records = mock_upsert.call_args[0][1]
        upserted_ids = {r["id"] for r in upserted_records}
        assert 1001 in upserted_ids  # recent
        assert 1003 in upserted_ids  # new
        assert 1002 not in upserted_ids  # old — must be excluded

    def test_skip_child_sync_always_true_for_incremental(self):
        """Incremental sync always passes skip_child_sync=True to _upsert_quotes."""
        db = _make_db_session()
        page = _make_page_result([_RECENT_QUOTE], current_page=1, last_page=1)

        with patch("app.services.eworks_sync_service.fetch_quote_page", return_value=page):
            with patch("app.services.eworks_sync_service._upsert_quotes") as mock_upsert:
                from app.schemas.eworks_sync_api import EworksSyncBucketSummary
                mock_upsert.return_value = EworksSyncBucketSummary(fetched=1, created=1)

                sync_quotes_incremental_recent(db, window_minutes=60, timeout_seconds=30)

        _, kwargs = mock_upsert.call_args
        assert kwargs.get("skip_child_sync") is True

    def test_metadata_contains_mode_window_timeout(self):
        """Run metadata must carry mode, window, timeout, cutoff, and counts."""
        db = _make_db_session()
        page = _make_page_result([_RECENT_QUOTE], current_page=1, last_page=1)

        with patch("app.services.eworks_sync_service.fetch_quote_page", return_value=page):
            with patch("app.services.eworks_sync_service._upsert_quotes") as mock_upsert:
                from app.schemas.eworks_sync_api import EworksSyncBucketSummary
                mock_upsert.return_value = EworksSyncBucketSummary(fetched=1, created=1)

                _, run = sync_quotes_incremental_recent(db, window_minutes=60, timeout_seconds=120)

        meta = run.metadata_ or {}
        assert meta.get("mode") == "incremental_recent"
        assert meta.get("recent_window_minutes") == 60
        assert meta.get("timeout_seconds") == 120
        assert "started_cutoff" in meta
        assert meta.get("attachments_during_sync") is False
        assert meta.get("quote_appointments_during_sync") is False
        assert "stopped_reason" in meta

    def test_invalid_date_counted_in_metadata(self):
        db = _make_db_session()
        bad_quote = {"id": 9999, "created_on": "not-a-date", "last_updated_on": "also-bad"}
        page = _make_page_result([bad_quote, _OLD_QUOTE], current_page=1, last_page=1)

        with patch("app.services.eworks_sync_service.fetch_quote_page", return_value=page):
            with patch("app.services.eworks_sync_service._upsert_quotes") as mock_upsert:
                from app.schemas.eworks_sync_api import EworksSyncBucketSummary
                mock_upsert.return_value = EworksSyncBucketSummary()

                _, run = sync_quotes_incremental_recent(db, window_minutes=60, timeout_seconds=30)

        meta = run.metadata_ or {}
        assert meta.get("skipped_invalid_date", 0) == 1

    def test_timeout_stops_cleanly_with_partial_status(self):
        """When timeout expires mid-pagination, status is partial and stopped_reason = timeout."""
        db = _make_db_session()

        page1 = _make_page_result([_RECENT_QUOTE], current_page=1, last_page=5)
        page2 = _make_page_result([_OLD_QUOTE], current_page=2, last_page=5)

        call_count = 0

        def _fake_page(page):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return page1
            # Make the deadline expire before second page is processed
            import time as _time
            _time.sleep(0)
            return page2

        with patch("app.services.eworks_sync_service.fetch_quote_page", side_effect=_fake_page):
            with patch("app.services.eworks_sync_service._upsert_quotes") as mock_upsert:
                from app.schemas.eworks_sync_api import EworksSyncBucketSummary
                mock_upsert.return_value = EworksSyncBucketSummary(fetched=1, created=1)

                # Use tiny timeout to force early stop
                with patch("app.services.eworks_sync_service._time") as mock_time:
                    ticks = [0, 0, 999999]  # deadline=120; after page1, time exceeds deadline
                    mock_time.monotonic.side_effect = ticks

                    _, run = sync_quotes_incremental_recent(db, window_minutes=60, timeout_seconds=120)

        assert run.status == "partial"
        meta = run.metadata_ or {}
        assert meta.get("stopped_reason") == "timeout"

    def test_early_stop_when_page_has_no_recent_records(self):
        """When a page returns zero recent records, pagination stops even if more pages exist."""
        db = _make_db_session()

        page1 = _make_page_result([_RECENT_QUOTE], current_page=1, last_page=10)
        page2 = _make_page_result([_OLD_QUOTE, _OLD_QUOTE], current_page=2, last_page=10)

        pages = [page1, page2]

        with patch("app.services.eworks_sync_service.fetch_quote_page", side_effect=pages):
            with patch("app.services.eworks_sync_service._upsert_quotes") as mock_upsert:
                from app.schemas.eworks_sync_api import EworksSyncBucketSummary
                mock_upsert.return_value = EworksSyncBucketSummary(fetched=1, created=1)

                _, run = sync_quotes_incremental_recent(db, window_minutes=60, timeout_seconds=120)

        # Should have stopped after page 2 (which had no recent records)
        meta = run.metadata_ or {}
        assert meta.get("stopped_reason") == "completed"
        assert meta.get("source_records_seen") == 3  # 1 from page1 + 2 from page2

    def test_api_error_marks_run_failed(self):
        """An AppError from the API marks the run as failed."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.models.eworks_sync import EworksSyncRun
        from app.core.exceptions import AppError

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        EworksSyncRun.__table__.create(engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        with patch(
            "app.services.eworks_sync_service.fetch_quote_page",
            side_effect=AppError("EWORKS_API_UNAVAILABLE", "API down", 502),
        ):
            with pytest.raises(AppError):
                sync_quotes_incremental_recent(db, window_minutes=60, timeout_seconds=30)

        run = db.query(EworksSyncRun).one()
        assert run.status == "failed"
        assert run.finished_at is not None

    def test_run_status_success_when_no_failures(self):
        db = _make_db_session()
        page = _make_page_result([_RECENT_QUOTE], current_page=1, last_page=1)

        with patch("app.services.eworks_sync_service.fetch_quote_page", return_value=page):
            with patch("app.services.eworks_sync_service._upsert_quotes") as mock_upsert:
                from app.schemas.eworks_sync_api import EworksSyncBucketSummary
                mock_upsert.return_value = EworksSyncBucketSummary(fetched=1, created=1)

                _, run = sync_quotes_incremental_recent(db, window_minutes=60, timeout_seconds=120)

        assert run.status == "success"


# ---------------------------------------------------------------------------
# Scheduler: incremental mode is selected when mode = incremental_recent
# ---------------------------------------------------------------------------

class TestBackgroundSchedulerIncrementalRouting:
    @patch("app.services.background_sync_scheduler.schedule_eworks_sync")
    @patch("app.services.background_sync_scheduler.SessionLocal")
    def test_incremental_mode_calls_schedule_with_mode_filter(self, mock_session, mock_schedule):
        from app.services.background_sync_scheduler import run_background_quotes_sync

        db = MagicMock()
        mock_session.return_value = db
        mock_schedule.return_value = MagicMock()

        with patch("app.services.background_sync_scheduler.settings") as mock_settings:
            mock_settings.eworks_background_quotes_enabled = True
            mock_settings.eworks_api_enabled = True
            mock_settings.eworks_quotes_sync_mode = "incremental_recent"
            mock_settings.eworks_quotes_sync_recent_window_minutes = 60
            mock_settings.eworks_quotes_sync_timeout_seconds = 120

            with patch("app.services.background_sync_scheduler.clear_stale_running_sync_locks"):
                run_background_quotes_sync()

        mock_schedule.assert_called_once()
        filters = mock_schedule.call_args.kwargs["filters"]
        assert filters["mode"] == "incremental_recent"
        assert filters["recent_window_minutes"] == 60
        assert filters["timeout_seconds"] == 120

    @patch("app.services.background_sync_scheduler.schedule_eworks_sync")
    @patch("app.services.background_sync_scheduler.SessionLocal")
    def test_incremental_mode_uses_check_global_running_false(self, mock_session, mock_schedule):
        """Incremental quotes sync should not block on other sync types running."""
        from app.services.background_sync_scheduler import run_background_quotes_sync

        db = MagicMock()
        mock_session.return_value = db
        mock_schedule.return_value = MagicMock()

        with patch("app.services.background_sync_scheduler.settings") as mock_settings:
            mock_settings.eworks_background_quotes_enabled = True
            mock_settings.eworks_api_enabled = True
            mock_settings.eworks_quotes_sync_mode = "incremental_recent"
            mock_settings.eworks_quotes_sync_recent_window_minutes = 60
            mock_settings.eworks_quotes_sync_timeout_seconds = 120

            with patch("app.services.background_sync_scheduler.clear_stale_running_sync_locks"):
                run_background_quotes_sync()

        assert mock_schedule.call_args.kwargs["check_global_running"] is False

    @patch("app.services.background_sync_scheduler.schedule_eworks_sync")
    @patch("app.services.background_sync_scheduler.SessionLocal")
    def test_full_mode_falls_back_to_standard_sync(self, mock_session, mock_schedule):
        from app.services.background_sync_scheduler import run_background_quotes_sync

        db = MagicMock()
        mock_session.return_value = db
        mock_schedule.return_value = MagicMock()

        with patch("app.services.background_sync_scheduler.settings") as mock_settings:
            mock_settings.eworks_background_quotes_enabled = True
            mock_settings.eworks_api_enabled = True
            mock_settings.eworks_quotes_sync_mode = "full"
            mock_settings.eworks_sync_lookback_days = 7

            with patch("app.services.background_sync_scheduler.clear_stale_running_sync_locks"):
                with patch("app.services.background_sync_scheduler.get_running_sync_run", return_value=None):
                    run_background_quotes_sync()

        filters = mock_schedule.call_args.kwargs["filters"]
        assert filters.get("mode") != "incremental_recent"

    def test_build_background_sync_config_includes_incremental_fields(self):
        from app.services.background_sync_scheduler import build_background_sync_config

        config = build_background_sync_config()
        assert "quotes_sync_mode" in config
        assert "quotes_recent_window_minutes" in config
        assert "quotes_timeout_seconds" in config
        assert "attachments_during_quote_sync" in config
        assert "quote_appointments_during_quote_sync" in config
