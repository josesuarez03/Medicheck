import hashlib
import hmac
import json
import logging
import time
import urllib.request

from django.conf import settings

from users.serializers import PatientClinicalSummaryContextSerializer


logger = logging.getLogger(__name__)


def _sign_payload(payload):
    request_timestamp = str(int(time.time()))
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    signature = hmac.new(
        settings.FLASK_API_KEY.encode("utf-8"),
        f"{request_timestamp}:{canonical_payload}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return request_timestamp, signature, canonical_payload


def push_clinical_summary_to_ai(summary):
    if not getattr(settings, "AI_SERVICE_URL", ""):
        return False
    payload = {
        "user_id": str(summary.patient.user_id),
        "patient_id": str(summary.patient_id),
        "clinical_summary_id": str(summary.id),
        "summary_version": summary.summary_version,
        "summary_text": summary.build_summary_text(),
        "clinical_snapshot": PatientClinicalSummaryContextSerializer(summary).data,
    }
    request_timestamp, signature, body = _sign_payload(payload)
    request = urllib.request.Request(
        f"{settings.AI_SERVICE_URL}/inference/internal/user-summary/upsert",
        data=body.encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Request-Timestamp": request_timestamp,
            "X-Request-Signature": signature,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=4):
            return True
    except Exception as exc:
        logger.warning("Could not push PatientClinicalSummary to ai-service: %s", exc)
        return False
