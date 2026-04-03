from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Any

from config.config import Config


logger = logging.getLogger(__name__)


class DjangoClinicalSummaryClient:
    def __init__(self):
        self.base_url = (Config.DJANGO_API_URL_FLASK or Config.DJANGO_API_URL or "").rstrip("/")
        self.shared_secret = Config.FLASK_API_KEY or ""

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.shared_secret)

    def _sign(self, payload: dict[str, Any]) -> tuple[str, str]:
        request_timestamp = str(int(time.time()))
        canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        signature = hmac.new(
            self.shared_secret.encode("utf-8"),
            f"{request_timestamp}:{canonical_payload}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return request_timestamp, signature

    def get_clinical_summary(self, *, user_id: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        payload = {"user_id": user_id}
        timestamp, signature = self._sign(payload)
        query = urllib.parse.urlencode(payload)
        endpoint = f"{self.base_url}/patients/clinical_summary/?{query}"
        request = urllib.request.Request(
            endpoint,
            method="GET",
            headers={
                "X-Request-Timestamp": timestamp,
                "X-Request-Signature": signature,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=4) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except Exception as exc:
            logger.warning("Could not fetch PatientClinicalSummary from Django: %s", exc)
            return None
