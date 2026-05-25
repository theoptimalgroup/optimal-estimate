"""Unit tests for idempotency key storage and replay."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import AppError
from app.models.support import IdempotencyKey
from app.services.idempotency_service import (
    check_idempotency,
    hash_payload,
    session_idempotency_key,
    store_idempotency,
)
from tests.test_db import make_test_session


def test_hash_payload_is_stable():
    payload = {"b": 2, "a": 1}
    assert hash_payload(payload) == hash_payload({"a": 1, "b": 2})
    assert hash_payload("hello") == hash_payload("hello")
    assert hash_payload(None) == hash_payload("")


def test_session_idempotency_key_format():
    key = session_idempotency_key("eworks", "Q-1", "JOB-2")
    assert key == "eworks.session.eworks.Q-1.JOB-2"


def test_store_and_replay_idempotency():
    db, _ = make_test_session()
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    store_idempotency(
        db,
        key="test-key",
        request_hash=hash_payload({"value": 1}),
        response_payload={"ok": True},
        expires_at=expires,
    )
    db.commit()

    replay = check_idempotency(db, key="test-key", request_hash=hash_payload({"value": 1}))
    assert replay is not None
    assert replay.payload == {"ok": True}
    assert replay.status_code == 200


def test_idempotency_conflict_on_reused_key_with_different_body():
    db, _ = make_test_session()
    store_idempotency(
        db,
        key="conflict-key",
        request_hash=hash_payload({"value": 1}),
        response_payload={"ok": True},
    )
    db.commit()

    with pytest.raises(AppError) as exc:
        check_idempotency(db, key="conflict-key", request_hash=hash_payload({"value": 2}))
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"
    assert exc.value.status_code == 409


def test_expired_idempotency_record_is_ignored():
    db, _ = make_test_session()
    expired = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.add(
        IdempotencyKey(
            key="expired-key",
            request_hash=hash_payload({"value": 1}),
            response_payload={"ok": True},
            expires_at=expired,
        )
    )
    db.commit()

    assert check_idempotency(db, key="expired-key", request_hash=hash_payload({"value": 1})) is None
