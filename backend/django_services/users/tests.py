import hashlib
import hmac
import json
import time

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from .models import Patient, PatientHistoryEntry, User
from .serializers import ChatbotAnalysisSerializer
from .utils.audit import create_audit_entry, verify_audit_entry
from common.security.encrypted_fields import ENCRYPTED_VALUE_PREFIX


def _sign_payload(payload, timestamp=None):
    request_timestamp = str(timestamp or int(time.time()))
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    signature = hmac.new(
        settings.FLASK_API_KEY.encode("utf-8"),
        f"{request_timestamp}:{canonical_payload}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return request_timestamp, signature


class ChatbotAnalysisSerializerTests(SimpleTestCase):
    def test_accepts_blank_optional_text_fields(self):
        serializer = ChatbotAnalysisSerializer(
            data={
                "triaje_level": "",
                "pain_scale": 0,
                "medical_context": "Resumen clínico",
                "allergies": "",
                "medications": "",
                "medical_history": "",
                "ocupacion": "",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["triaje_level"], "")
        self.assertEqual(serializer.validated_data["allergies"], "")

    def test_accepts_null_triage_level(self):
        serializer = ChatbotAnalysisSerializer(
            data={
                "triaje_level": None,
                "pain_scale": 4,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)


class SecurityViewsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="patient@example.com",
            username="patient",
            password="Password123!",
            tipo="patient",
            first_name="Pat",
            last_name="Ient",
        )
        self.patient = Patient.objects.create(user=self.user)

    def test_medical_data_update_accepts_valid_hmac_signature(self):
        payload = {
            "user_id": str(self.user.id),
            "medical_data": {
                "triaje_level": "Moderado",
                "pain_scale": 5,
                "medical_context": "Resumen",
                "allergies": "",
                "medications": "",
                "medical_history": "",
                "ocupacion": "",
            },
            "source": "chatbot",
        }
        request_timestamp, signature = _sign_payload(payload)

        response = self.client.post(
            "/api/patients/medical_data_update/",
            payload,
            format="json",
            HTTP_X_REQUEST_TIMESTAMP=request_timestamp,
            HTTP_X_REQUEST_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)

    def test_medical_data_update_rejects_tampered_signature(self):
        payload = {
            "user_id": str(self.user.id),
            "medical_data": {"pain_scale": 3},
            "source": "chatbot",
        }
        request_timestamp, _signature = _sign_payload(payload)

        response = self.client.post(
            "/api/patients/medical_data_update/",
            payload,
            format="json",
            HTTP_X_REQUEST_TIMESTAMP=request_timestamp,
            HTTP_X_REQUEST_SIGNATURE="bad-signature",
        )

        self.assertEqual(response.status_code, 401)

    def test_medical_data_update_rejects_stale_timestamp(self):
        payload = {
            "user_id": str(self.user.id),
            "medical_data": {"pain_scale": 3},
            "source": "chatbot",
        }
        request_timestamp, signature = _sign_payload(payload, timestamp=int(time.time()) - 60)

        response = self.client.post(
            "/api/patients/medical_data_update/",
            payload,
            format="json",
            HTTP_X_REQUEST_TIMESTAMP=request_timestamp,
            HTTP_X_REQUEST_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 401)

    def test_patient_history_token_allows_tokenized_access(self):
        PatientHistoryEntry.objects.create(
            patient=self.patient,
            source="chatbot",
            created_by=self.user,
            notes="entrada",
            triaje_level="Leve",
        )
        self.client.force_authenticate(user=self.user)
        token_response = self.client.get("/patients/me/history/token/")
        self.assertEqual(token_response.status_code, 200)
        token = token_response.json()["token"]

        unauthenticated_client = APIClient()
        history_response = unauthenticated_client.get("/patients/me/history/", {"token": token})

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.json()["count"], 1)

    @override_settings(
        REST_FRAMEWORK={
            **settings.REST_FRAMEWORK,
            "DEFAULT_THROTTLE_RATES": {
                **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
                "login": "1/min",
            },
        }
    )
    def test_login_is_throttled(self):
        first = self.client.post("/login/", {"email": self.user.email, "password": "wrong"}, format="json")
        second = self.client.post("/login/", {"email": self.user.email, "password": "wrong"}, format="json")

        self.assertEqual(first.status_code, 401)
        self.assertEqual(second.status_code, 429)

    def test_options_no_longer_forces_cors_wildcard(self):
        response = self.client.options(
            "/login/",
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )

        self.assertNotEqual(response.headers.get("Access-Control-Allow-Origin"), "*")

    def test_create_audit_entry_signs_actor_and_timestamp_metadata(self):
        entry = create_audit_entry(
            actor_user=self.user,
            actor_service="flask-chatbot",
            actor_ip="127.0.0.1",
            action="patient_medical_data_update",
            resource_type="patient",
            resource_id=str(self.patient.id),
            data_before={"pain_scale": 2},
            data_after={"pain_scale": 4},
        )

        self.assertTrue(verify_audit_entry(entry))
        entry.actor_ip = "10.0.0.5"
        self.assertFalse(verify_audit_entry(entry))

    def test_encrypted_text_field_prep_value_encrypts_plaintext(self):
        raw_db_value = Patient._meta.get_field("medical_context").get_prep_value("Texto clinico sensible")

        self.assertTrue(raw_db_value.startswith(ENCRYPTED_VALUE_PREFIX))
        self.assertNotIn("Texto clinico sensible", raw_db_value)
