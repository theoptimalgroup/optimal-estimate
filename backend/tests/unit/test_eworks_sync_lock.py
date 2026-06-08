"""Tests for database-backed eWorks sync locks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AppError
from app.models.eworks_sync import EworksSyncLock, EworksSyncRun
from app.services.eworks_sync_lock_service import (
    SYNC_LOCK_ACTIVE_MESSAGE,
    clear_stale_sync_locks,
    is_sync_lock_stale,
    try_acquire_sync_lock,
)
from app.services.eworks_sync_runner import schedule_eworks_sync


@pytest.fixture()
def lock_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    EworksSyncLock.__table__.create(engine)
    EworksSyncRun.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _patch_lock_settings(mock_settings):
    mock_settings.eworks_sync_lock_timeout_minutes = 30
    mock_settings.eworks_sync_lock_heartbeat_seconds = 60
    mock_settings.eworks_sync_running_timeout_minutes = 30
    mock_settings.run_background_worker = True


@patch("app.services.eworks_sync_lock_service.settings")
def test_try_acquire_sync_lock_creates_row(mock_settings, lock_db):
    _patch_lock_settings(mock_settings)

    lock = try_acquire_sync_lock(lock_db, "quotes", locked_by="test-worker")

    assert lock is not None
    assert lock.sync_type == "quotes"
    assert lock.status == "running"


@patch("app.services.eworks_sync_lock_service.settings")
def test_duplicate_lock_is_rejected(mock_settings, lock_db):
    _patch_lock_settings(mock_settings)

    first = try_acquire_sync_lock(lock_db, "quotes", locked_by="worker-a")
    assert first is not None

    second = try_acquire_sync_lock(lock_db, "quotes", locked_by="worker-b")
    assert second is None


@patch("app.services.eworks_sync_lock_service.settings")
def test_stale_lock_can_be_recovered(mock_settings, lock_db):
    _patch_lock_settings(mock_settings)

    lock = try_acquire_sync_lock(lock_db, "jobs", locked_by="worker-a")
    assert lock is not None

    stale_time = datetime.now(timezone.utc) - timedelta(minutes=45)
    lock.heartbeat_at = stale_time
    lock.expires_at = stale_time
    lock_db.commit()

    assert is_sync_lock_stale(lock) is True
    cleared = clear_stale_sync_locks(lock_db)
    assert cleared == 1

    recovered = try_acquire_sync_lock(lock_db, "jobs", locked_by="worker-b")
    assert recovered is not None
    assert recovered.locked_by == "worker-b"


@patch("app.services.eworks_sync_lock_service.settings")
def test_manual_sync_respects_active_lock(mock_lock_settings, lock_db):
    _patch_lock_settings(mock_lock_settings)

    try_acquire_sync_lock(lock_db, "quotes", locked_by="background-worker")

    with pytest.raises(AppError) as exc_info:
        schedule_eworks_sync(
            lock_db,
            sync_type="quotes",
            filters={},
            user_id=None,
            actor_email="admin@optimal.example",
        )

    assert exc_info.value.code == "SYNC_ALREADY_RUNNING"
    assert exc_info.value.message == SYNC_LOCK_ACTIVE_MESSAGE


@patch("app.services.background_sync_scheduler.settings")
def test_scheduler_does_not_start_without_worker_flag(mock_settings):
    from app.services.background_sync_scheduler import should_start_scheduler

    mock_settings.eworks_background_sync_enabled = True
    mock_settings.run_background_worker = False
    assert should_start_scheduler() is False


@patch("app.services.background_sync_scheduler.settings")
def test_scheduler_starts_with_worker_flag(mock_settings):
    from app.services.background_sync_scheduler import should_start_scheduler

    mock_settings.eworks_background_sync_enabled = True
    mock_settings.run_background_worker = True
    assert should_start_scheduler() is True
