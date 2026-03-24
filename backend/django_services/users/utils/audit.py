from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from django.conf import settings
from django.db import transaction

from users.models import AuditLog


def _audit_signing_key() -> str:
    key = getattr(settings, "AUDIT_SIGNING_KEY", "") or ""
    if not key:
        raise ValueError("AUDIT_SIGNING_KEY must be configured.")
    return key


def canonicalize_payload(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def compute_content_hash(payload: Any) -> str:
    return hashlib.sha256(canonicalize_payload(payload).encode("utf-8")).hexdigest()


def compute_signature(content_hash: str) -> str:
    return hmac.new(
        _audit_signing_key().encode("utf-8"),
        content_hash.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _entry_payload(*, actor_user_id, actor_service, actor_ip, action, resource_type, resource_id, data_before, data_after, timestamp) -> dict[str, Any]:
    return {
        "actor_user_id": str(actor_user_id) if actor_user_id else None,
        "actor_service": actor_service,
        "actor_ip": actor_ip,
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id),
        "data_before": data_before,
        "data_after": data_after,
        "timestamp": timestamp.isoformat() if timestamp else None,
    }


def create_audit_entry(
    *,
    actor_user=None,
    actor_service: str | None = None,
    actor_ip: str | None = None,
    action: str,
    resource_type: str,
    resource_id: str,
    data_before: Any = None,
    data_after: Any = None,
) -> AuditLog:
    with transaction.atomic():
        entry = AuditLog.objects.create(
            actor_user=actor_user,
            actor_service=actor_service,
            actor_ip=actor_ip,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            data_before=data_before,
            data_after=data_after,
            content_hash="0" * 64,
            signature="0" * 64,
        )
        payload = _entry_payload(
            actor_user_id=entry.actor_user_id,
            actor_service=entry.actor_service,
            actor_ip=entry.actor_ip,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            data_before=entry.data_before,
            data_after=entry.data_after,
            timestamp=entry.timestamp,
        )
        entry.content_hash = compute_content_hash(payload)
        entry.signature = compute_signature(entry.content_hash)
        entry.save(update_fields=["content_hash", "signature"])
        return entry


def verify_audit_entry(entry: AuditLog) -> bool:
    payload = _entry_payload(
        actor_user_id=entry.actor_user_id,
        actor_service=entry.actor_service,
        actor_ip=entry.actor_ip,
        action=entry.action,
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        data_before=entry.data_before,
        data_after=entry.data_after,
        timestamp=entry.timestamp,
    )
    expected_hash = compute_content_hash(payload)
    expected_signature = compute_signature(expected_hash)
    return hmac.compare_digest(entry.content_hash, expected_hash) and hmac.compare_digest(entry.signature, expected_signature)
