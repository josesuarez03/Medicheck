import hashlib
import hmac
import json
import time

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Doctor, DoctorPatientRelation, Patient, PatientClinicalSummary, PatientHistoryEntry, User
from .serializers import ChatbotAnalysisSerializer, DoctorSerializer, PatientSerializer
from .utils.audit import create_audit_entry, verify_audit_entry
from .views import DoctorViewSet, PatientHistoryViewSet, PatientViewSet
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
        self.patient.refresh_from_db()
        summary = PatientClinicalSummary.objects.get(patient=self.patient)
        self.assertEqual(summary.summary.get("triaje_level"), "Moderado")

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
        history_response = unauthenticated_client.get(
            "/patients/me/history/",
            HTTP_X_PATIENT_HISTORY_TOKEN=token,
        )

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

    def test_clinical_summary_internal_endpoint_returns_context(self):
        summary = PatientClinicalSummary.objects.create(
            patient=self.patient,
            known_allergies="penicilina",
            current_medications="ibuprofeno",
        )
        request_timestamp, signature = _sign_payload({"user_id": str(self.user.id)})

        response = self.client.get(
            "/api/patients/clinical_summary/",
            {"user_id": str(self.user.id)},
            HTTP_X_REQUEST_TIMESTAMP=request_timestamp,
            HTTP_X_REQUEST_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(summary.id))
        self.assertEqual(response.json()["patient"], str(self.patient.id))
        self.assertIn("summary_text", response.json())

    def test_clinical_summary_build_summary_text_excludes_identity_fields(self):
        summary = PatientClinicalSummary.objects.create(
            patient=self.patient,
            chief_complaint_current="dolor torácico",
            known_allergies="penicilina",
            current_medications="salbutamol",
        )
        summary_text = summary.build_summary_text()

        self.assertIn("dolor torácico", summary_text)
        self.assertNotIn(self.user.email, summary_text)
        self.assertNotIn(self.user.first_name, summary_text)


class QueryOptimizationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()
        self.admin = User.objects.create_user(
            email="admin@example.com",
            username="admin",
            password="Password123!",
            tipo="admin",
            first_name="Ad",
            last_name="Min",
        )
        self.doctor_user = User.objects.create_user(
            email="doctor@example.com",
            username="doctor",
            password="Password123!",
            tipo="doctor",
            first_name="Doc",
            last_name="Tor",
        )
        self.doctor = Doctor.objects.create(user=self.doctor_user, especialidad="Medicina", numero_licencia="1234")

        self.patient_users = []
        self.patients = []
        for index in range(2):
            patient_user = User.objects.create_user(
                email=f"patient{index}@example.com",
                username=f"patient{index}",
                password="Password123!",
                tipo="patient",
                first_name=f"Pat{index}",
                last_name="Ient",
            )
            patient = Patient.objects.create(user=patient_user)
            DoctorPatientRelation.objects.create(doctor=self.doctor, patient=patient, active=True)
            PatientHistoryEntry.objects.create(
                patient=patient,
                source="chatbot",
                created_by=patient_user,
                notes="entrada",
                triaje_level="Leve",
            )
            self.patient_users.append(patient_user)
            self.patients.append(patient)

    def test_patient_viewset_queryset_avoids_n_plus_one_in_serializer(self):
        request = self.factory.get("/patients/")
        request.user = self.admin
        view = PatientViewSet()
        view.request = Request(request)

        queryset = view.get_queryset()

        with self.assertNumQueries(2):
            data = PatientSerializer(queryset, many=True).data

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["history_count"], 1)
        self.assertEqual(len(data[0]["doctors"]), 1)

    def test_doctor_viewset_queryset_avoids_n_plus_one_in_serializer(self):
        request = self.factory.get("/doctors/")
        request.user = self.admin
        view = DoctorViewSet()
        view.request = Request(request)
        view.action = "list"

        queryset = view.get_queryset()

        with self.assertNumQueries(2):
            data = DoctorSerializer(queryset, many=True).data

        self.assertEqual(len(data), 1)
        self.assertEqual(len(data[0]["patients"]), 2)

    def test_patient_history_queryset_selects_related_models(self):
        request = self.factory.get("/patients/me/history/")
        request.user = self.patient_users[0]
        view = PatientHistoryViewSet()
        view.request = Request(request)
        view.kwargs = {"patient_id": str(self.patients[0].id)}

        queryset = view.get_queryset()

        with self.assertNumQueries(1):
            entries = list(queryset)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].created_by_id, self.patient_users[0].id)


class PatientFlowStabilityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="stable@example.com",
            username="stable",
            password="Password123!",
            tipo="patient",
            first_name="Ana",
            last_name="Paciente",
            fecha_nacimiento="1990-01-01",
            telefono="600123123",
            direccion="Calle Mayor 1",
        )
        self.patient = Patient.objects.create(user=self.user, ocupacion="Docente", allergies="Polen")
        self.user.check_profile_completion()
        self.client.force_authenticate(user=self.user)

    def test_change_password_preserves_profile_completion_and_returns_user_payload(self):
        response = self.client.post(
            "/password/change/",
            {
                "old_password": "Password123!",
                "new_password": "Password456!",
                "confirm_password": "Password456!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_profile_completed)
        self.assertTrue(response.json()["profile_complete"])
        self.assertEqual(response.json()["user"]["id"], str(self.user.id))

    def test_history_serializer_exposes_compact_summary_without_markdown_noise(self):
        entry = PatientHistoryEntry.objects.create(
            patient=self.patient,
            source="chatbot",
            created_by=self.user,
            notes="**Resumen** de seguimiento",
            medical_context="# Dolor de cabeza\\n\\n- intensidad alta",
            triaje_level="Moderado",
        )

        data = PatientHistoryEntrySerializer(entry).data

        self.assertIn("Resumen", data["compact_summary"])
        self.assertNotIn("#", data["compact_summary"])
        self.assertNotIn("**", data["compact_summary"])
