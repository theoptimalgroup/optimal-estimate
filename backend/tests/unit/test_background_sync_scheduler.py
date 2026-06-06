"""Tests for background eWorks sync scheduler."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.eworks_sync import EworksSyncRun
from app.services.background_sync_scheduler import (
    _SKIP_RUNNING_MESSAGE,
    build_background_sync_config,
    run_background_quotes_sync,
    should_start_scheduler,
    start_background_sync_scheduler,
    stop_background_sync_scheduler,
)
from app.services.eworks_sync_service import resolve_sync_filters, sync_quotes_from_eworks


@pytest.fixture(autouse=True)
def reset_scheduler():
    stop_background_sync_scheduler()
    yield
    stop_background_sync_scheduler()


def test_should_start_scheduler_requires_both_flags():
    with patch("app.services.background_sync_scheduler.settings") as mock_settings:
        mock_settings.eworks_background_sync_enabled = True
        mock_settings.run_background_worker = False
        assert should_start_scheduler() is False

        mock_settings.run_background_worker = True
        assert should_start_scheduler() is True


@patch("app.services.background_sync_scheduler.BackgroundScheduler")
def test_scheduler_does_not_start_when_disabled(mock_scheduler_cls):
    with patch("app.services.background_sync_scheduler.settings") as mock_settings:
        mock_settings.eworks_background_sync_enabled = False
        mock_settings.run_background_worker = False

        start_background_sync_scheduler()

    mock_scheduler_cls.assert_not_called()


@patch("app.services.background_sync_scheduler.BackgroundScheduler")
def test_scheduler_registers_quote_and_job_jobs_when_enabled(mock_scheduler_cls):
    scheduler = MagicMock()
    mock_scheduler_cls.return_value = scheduler

    with patch("app.services.background_sync_scheduler.settings") as mock_settings:
        mock_settings.eworks_background_sync_enabled = True
        mock_settings.run_background_worker = True
        mock_settings.eworks_background_quotes_enabled = True
        mock_settings.eworks_background_jobs_enabled = True
        mock_settings.eworks_background_products_enabled = False
        mock_settings.eworks_quotes_sync_interval_minutes = 10
        mock_settings.eworks_jobs_sync_interval_minutes = 30

        start_background_sync_scheduler()

    job_ids = [call.kwargs["id"] for call in scheduler.add_job.call_args_list]
    assert "eworks_background_quotes_sync" in job_ids
    assert "eworks_background_jobs_sync" in job_ids
    assert "eworks_background_products_sync" not in job_ids
    scheduler.start.assert_called_once()


@patch("app.services.background_sync_scheduler.schedule_eworks_sync")
@patch("app.services.background_sync_scheduler.SessionLocal")
def test_background_quotes_job_skips_when_sync_running(mock_session_local, mock_schedule):
    db = MagicMock()
    mock_session_local.return_value = db

    running = EworksSyncRun(
        id="00000000-0000-0000-0000-000000000001",
        sync_type="all",
        status="running",
        started_at=datetime.now(timezone.utc),
    )

    with patch("app.services.background_sync_scheduler.settings") as mock_settings:
        mock_settings.eworks_background_quotes_enabled = True
        mock_settings.eworks_api_enabled = True
        mock_settings.eworks_sync_lookback_days = 7

        with patch(
            "app.services.background_sync_scheduler.clear_stale_running_sync_locks"
        ) as mock_clear:
            with patch(
                "app.services.background_sync_scheduler.get_running_sync_run",
                return_value=running,
            ):
                run_background_quotes_sync()

    mock_schedule.assert_not_called()
    mock_clear.assert_called_once_with(db)
    db.close.assert_called_once()


@patch("app.services.background_sync_scheduler.schedule_eworks_sync")
@patch("app.services.background_sync_scheduler.SessionLocal")
def test_background_quotes_job_uses_lookback_filters(mock_session_local, mock_schedule):
    db = MagicMock()
    mock_session_local.return_value = db

    with patch("app.services.background_sync_scheduler.settings") as mock_settings:
        mock_settings.eworks_background_quotes_enabled = True
        mock_settings.eworks_api_enabled = True
        mock_settings.eworks_sync_lookback_days = 9

        with patch("app.services.background_sync_scheduler.clear_stale_running_sync_locks"):
            with patch("app.services.background_sync_scheduler.get_running_sync_run", return_value=None):
                with patch("app.services.eworks_sync_service.settings") as sync_settings:
                    sync_settings.eworks_sync_lookback_days = 9
                    run_background_quotes_sync()

    mock_schedule.assert_called_once()
    filters = mock_schedule.call_args.kwargs["filters"]
    assert filters["date_from"]
    assert filters["date_to"]
    assert mock_schedule.call_args.kwargs["source"] == "background"


@patch("app.services.background_sync_scheduler.schedule_eworks_sync", side_effect=RuntimeError("boom"))
@patch("app.services.background_sync_scheduler.SessionLocal")
def test_background_job_exception_is_caught(mock_session_local, _mock_schedule, caplog):
    db = MagicMock()
    mock_session_local.return_value = db

    with patch("app.services.background_sync_scheduler.settings") as mock_settings:
        mock_settings.eworks_background_quotes_enabled = True
        mock_settings.eworks_api_enabled = True

        with patch("app.services.background_sync_scheduler.clear_stale_running_sync_locks"):
            with patch("app.services.background_sync_scheduler.get_running_sync_run", return_value=None):
                run_background_quotes_sync()

    db.close.assert_called_once()
    assert any("Background quotes sync failed unexpectedly" in rec.message for rec in caplog.records)


def test_build_background_sync_config_has_no_secrets():
    config = build_background_sync_config()
    dumped = str(config).lower()
    assert "api_key" not in dumped
    assert "secret" not in dumped
    assert "password" not in dumped


def test_resolve_sync_filters_uses_configured_lookback_days():
    with patch("app.services.eworks_sync_service.settings") as mock_settings:
        mock_settings.eworks_sync_lookback_days = 12
        filters = resolve_sync_filters(full=False)

    today = datetime.now(timezone.utc).date()
    expected_from = (today - timedelta(days=12)).isoformat()
    assert filters["date_from"] == expected_from
    assert filters["date_to"] == today.isoformat()


def test_skip_running_message_is_safe():
    assert "api_key" not in _SKIP_RUNNING_MESSAGE.lower()
    assert "secret" not in _SKIP_RUNNING_MESSAGE.lower()


@patch("app.services.eworks_sync_service.fetch_all_quotes", side_effect=RuntimeError("timeout"))
def test_sync_run_gets_finished_at_on_failure(mock_fetch):
    del mock_fetch
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
    db = Session()

    with pytest.raises(RuntimeError):
        sync_quotes_from_eworks(db, filters={"date_from": "2026-01-01", "date_to": "2026-01-02"})

    run = db.query(EworksSyncRun).one()
    assert run.status == "failed"
    assert run.finished_at is not None
    db.close()
