from django.contrib.auth import get_user_model, authenticate
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
import hmac
import hashlib
import json
import time

from rest_framework import status, viewsets, generics, mixins
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from social_django.utils import load_strategy, load_backend
from social_core.exceptions import MissingBackend, AuthTokenError, AuthForbidden

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.core.cache import cache
import logging

from .serializers import (
    UserSerializer, UserProfileSerializer, UserProfileSerializerBasic,
    GoogleOAuthUserInfoSerializer, RequiredOAuthUserSerializer, 
    PatientSerializer, DoctorSerializer, PatientBasicSerializer, ChatbotAnalysisSerializer,
    PasswordResetRequestSerializer, PasswordResetVerifySerializer,
    ChangePasswordSerializer, AccountDeleteSerializer, PatientHistoryEntrySerializer,
    DoctorPatientRelationSerializer
)
from .models import Patient, Doctor, PatientHistoryEntry, DoctorPatientRelation
from .throttles import LoginRateThrottle, PasswordResetRateThrottle
from .utils.audit import create_audit_entry

User = get_user_model()
logger = logging.getLogger(__name__)


def _request_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    
    def post(self, request):
        # Obtener credenciales
        email_or_username = request.data.get('email') or request.data.get('username')
        password = request.data.get('password')

        if not email_or_username:
            return Response(
                {"error": "Se requiere email o username."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not password:
            return Response(
                {"error": "Se requiere contraseña."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Intentar autenticar con username o email
        user = authenticate(request, username=email_or_username, password=password)
        if user is None:
            try:
                user_obj = User.objects.get(email=email_or_username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        
        if user is not None:
            if not user.is_active:
                return Response(
                    {"error": "La cuenta está desactivada."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
                
            # Login exitoso, generar tokens JWT
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserProfileSerializerBasic(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'profile_complete': user.is_profile_completed,
                'message': 'Usuario autenticado correctamente.'
            }, status=status.HTTP_200_OK)
        
        # Credenciales inválidas
        return Response(
            {"error": "Credenciales inválidas."},
            status=status.HTTP_401_UNAUTHORIZED
        )

class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserProfileSerializerBasic(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'profile_complete': False,
                'message': 'Usuario registrado correctamente. Complete su perfil.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GoogleOAuthLoginView(APIView):
    """Vista para autenticación con Google (login o registro)"""
    permission_classes = [AllowAny]
    serializer_class = GoogleOAuthUserInfoSerializer

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)  # Simplifica la validación

        token = serializer.validated_data['token']
        provider = 'google-oauth2'

        try:
            strategy = load_strategy(request)
            backend = load_backend(strategy, provider, redirect_uri=None)
            user = backend.do_auth(token)

            if not user:
                return Response(
                    {"error": "Error de autenticación con Google."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Actualizar campos del usuario
            user.oauth_provider = 'google'
            user.oauth_uid = getattr(user, 'social_user', {}).get('uid', user.oauth_uid)
            is_new_user = user.date_joined == user.last_login

            if is_new_user and 'tipo' in request.data:
                user.tipo = request.data.get('tipo', 'patient')

            user.save(update_fields=['oauth_provider', 'oauth_uid', 'tipo'])

            refresh = RefreshToken.for_user(user)
            response_data = {
                'user': UserProfileSerializerBasic(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'is_new_user': is_new_user,
                'profile_complete': user.is_profile_completed
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except (MissingBackend, AuthTokenError, AuthForbidden) as e:
            return Response(
                {"error": f"Error en autenticación con Google: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
class CompleteProfileView(generics.GenericAPIView):
    """Vista para completar información adicional después del registro/login con OAuth"""
    serializer_class = RequiredOAuthUserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    # Añadir soporte para método POST
    def post(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
        
    # Mantener soporte para PUT/PATCH
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
        
    def patch(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
    
    def get_serializer_context(self):

        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }
    
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            # Actualizar campos básicos del usuario
            for field in ['fecha_nacimiento', 'telefono', 'direccion', 'genero']:
                if field in serializer.validated_data:
                    setattr(user, field, serializer.validated_data[field])
            
            # Solo actualizar tipo si se proporciona explícitamente
            if 'tipo' in serializer.validated_data:
                user.tipo = serializer.validated_data['tipo']
            
            user.save()
            
            # Actualizar o crear el perfil de paciente si es necesario
            if user.tipo == 'patient':
                patient, created = Patient.objects.get_or_create(user=user)
                # Actualizar campos del paciente
                for field in ['allergies', 'ocupacion']:
                    if field in serializer.validated_data:
                        setattr(patient, field, serializer.validated_data[field])
                patient.save()
            
            # Actualizar o crear el perfil de doctor si es necesario
            if user.tipo == 'doctor':
                doctor, created = Doctor.objects.get_or_create(user=user)
                # Actualizar campos del doctor
                for field in ['especialidad', 'numero_licencia']:
                    if field in serializer.validated_data:
                        setattr(doctor, field, serializer.validated_data[field])
                doctor.save()
                
            # Verificar si el perfil está completo según datos reales
            user.check_profile_completion()
            
            return Response({
                'user': UserProfileSerializer(user).data,
                'profile_complete': user.is_profile_completed,
                'message': 'Perfil actualizado correctamente.'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class UserProfileView(generics.RetrieveUpdateDestroyAPIView):
    """Vista para ver, actualizar y eliminar el perfil del usuario"""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            # Actualizar campos básicos del usuario
            for field in ['first_name', 'last_name', 'telefono', 'direccion', 'genero']:
                if field in serializer.validated_data:
                    setattr(user, field, serializer.validated_data[field])
            
            user.save()
            
            return Response({
                'user': UserProfileSerializer(user).data,
                'message': 'Perfil actualizado correctamente.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.delete()
        return Response({
            'message': 'Cuenta eliminada correctamente.'
        }, status=status.HTTP_204_NO_CONTENT)

class UserViewSet(viewsets.ModelViewSet):
    """ViewSet para administrar usuarios (solo admin)"""
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAdminUser]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserProfileSerializerBasic
        return UserProfileSerializer
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Endpoint para obtener información del usuario actual"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def incomplete_profiles(self, request):
        """Listar usuarios con perfiles incompletos"""
        users = User.objects.filter(is_profile_completed=False)
        page = self.paginate_queryset(users)
        
        if page is not None:
            serializer = UserProfileSerializerBasic(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = UserProfileSerializerBasic(users, many=True)
        return Response(serializer.data)
    
class PatientMedicalDataUpdateView(APIView):
    """
    Vista unificada para recibir y procesar datos médicos
    Utiliza autenticación JWT para mantener consistencia con el resto del sistema
    Permite actualizar datos tanto por servicios internos como por Flask
    """
    permission_classes = [AllowAny]

    def _canonical_payload(self, payload):
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def _is_valid_internal_request(self, request):
        request_timestamp = request.headers.get("X-Request-Timestamp", "")
        request_signature = request.headers.get("X-Request-Signature", "")
        shared_secret = getattr(settings, "FLASK_API_KEY", "") or ""
        if not request_timestamp or not request_signature or not shared_secret:
            return False
        try:
            skew = abs(int(time.time()) - int(request_timestamp))
        except (TypeError, ValueError):
            return False
        if skew > 30:
            return False

        canonical_payload = self._canonical_payload(request.data)
        expected_signature = hmac.new(
            shared_secret.encode("utf-8"),
            f"{request_timestamp}:{canonical_payload}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_signature, request_signature)
    
    def post(self, request):
        authenticated_user = request.user if request.user and request.user.is_authenticated else None
        internal_request = self._is_valid_internal_request(request)

        if not authenticated_user and not internal_request:
            logger.warning("django_internal_auth_rejected path=%s", request.path)
            return Response(
                {"error": "Se requiere autenticación válida (JWT o token de integración interno)."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Obtener datos de la solicitud
        user_id = request.data.get('user_id')
        medical_data = request.data.get('medical_data', {})
        source = request.data.get('source', 'chatbot')
        
        # Si no se proporciona un user_id específico, usar el del usuario autenticado
        if not user_id and authenticated_user and authenticated_user.tipo == 'patient':
            user_id = str(authenticated_user.id)
        
        if not user_id:
            return Response(
                {"error": "Se requiere un ID de usuario"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar permisos - solo el propio usuario o un médico/admin puede actualizar datos
        if authenticated_user and (str(authenticated_user.id) != user_id and authenticated_user.tipo not in ['doctor', 'admin']):
            return Response(
                {"error": "No tiene permisos para actualizar los datos de este paciente"},
                status=status.HTTP_403_FORBIDDEN
            )
        if internal_request and source != 'chatbot':
            return Response(
                {"error": "La integración interna solo permite source='chatbot'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Buscar usuario y su perfil de paciente
        try:
            user = User.objects.get(id=user_id)
            
            # Verificar si es paciente
            if user.tipo != 'patient':
                return Response(
                    {"error": "El usuario no es un paciente"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Obtener o crear perfil de paciente
            patient, created = Patient.objects.get_or_create(user=user)
            
        except User.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validar los datos médicos recibidos
        serializer = ChatbotAnalysisSerializer(data=medical_data)
        
        if not serializer.is_valid():
            return Response(
                {"error": "Datos médicos inválidos", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar información del paciente con los datos validados
        before_snapshot = patient.clinical_snapshot()
        updated = patient.update_from_chatbot_analysis(
            serializer.validated_data,
            created_by=authenticated_user
        )
        
        if updated:
            # Obtener la última entrada de historial creada
            latest_history = patient.history_entries.first()
            patient.refresh_from_db()
            after_snapshot = patient.clinical_snapshot()
            create_audit_entry(
                actor_user=authenticated_user,
                actor_service='flask-chatbot' if internal_request else None,
                actor_ip=_request_ip(request),
                action='patient_medical_data_update',
                resource_type='patient',
                resource_id=str(patient.id),
                data_before=before_snapshot,
                data_after=after_snapshot,
            )
            
            # Verificar si la actualización completó el perfil del usuario
            user.check_profile_completion()
            
            return Response({
                "message": "Información del paciente actualizada correctamente",
                "patient": PatientSerializer(patient).data,
                "profile_complete": user.is_profile_completed,
                "history_entry": PatientHistoryEntrySerializer(latest_history).data if latest_history else None
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "message": "No se realizaron cambios en la información del paciente"
            }, status=status.HTTP_200_OK)

class PatientViewSet(viewsets.ModelViewSet):
    """ViewSet para administrar pacientes (doctor y admin)"""
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination  # Añadir paginación
    
    def get_queryset(self):
        user = self.request.user
        # Los pacientes solo pueden ver su propio perfil
        if user.tipo == 'patient':
            return Patient.objects.filter(user=user)
        # Doctores solo pueden ver sus pacientes asignados
        elif user.tipo == 'doctor':
            try:
                doctor = Doctor.objects.get(user=user)
                return Patient.objects.filter(
                    doctor_relations__doctor=doctor,
                    doctor_relations__active=True
                ).distinct()
            except Doctor.DoesNotExist:
                return Patient.objects.none()
        # Administradores pueden ver todos los pacientes
        elif user.tipo == 'admin':
            return Patient.objects.all()
        return Patient.objects.none()
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        # Incluir información del usuario asociado
        user_data = UserProfileSerializerBasic(instance.user).data
        data = serializer.data
        data['user'] = user_data
        return Response(data)
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Acción para obtener el historial médico de un paciente específico"""
        patient = self.get_object()
        
        # Configurar paginación para el historial
        paginator = PageNumberPagination()
        paginator.page_size = 10  # Puedes ajustar esto según necesites
        
        history_entries = patient.history_entries.all().order_by('-created_at')
        page = paginator.paginate_queryset(history_entries, request)
        
        if page is not None:
            serializer = PatientHistoryEntrySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        serializer = PatientHistoryEntrySerializer(history_entries, many=True)
        return Response(serializer.data)
class PatientHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para acceder al historial médico de un paciente"""
    serializer_class = PatientHistoryEntrySerializer
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination  # Añadir paginación

    def _patient_id_from_token(self):
        token = self.request.query_params.get("token")
        if not token:
            return None
        try:
            data = signing.loads(token, salt="patient-history-access", max_age=300)
        except (BadSignature, SignatureExpired):
            return None
        if data.get("action") != "read_history":
            return None
        return data.get("patient_id")
    
    def get_queryset(self):
        patient_id = self._patient_id_from_token() or self.kwargs.get('patient_id')
        user = self.request.user
        
        # Verificar permisos
        if not patient_id:
            return PatientHistoryEntry.objects.none()
        
        try:
            patient = Patient.objects.get(id=patient_id)
            if self._patient_id_from_token():
                return PatientHistoryEntry.objects.filter(patient=patient).order_by('-created_at')
            
            # Pacientes solo pueden ver su propio historial
            if not getattr(user, "is_authenticated", False):
                return PatientHistoryEntry.objects.none()
            if user.tipo == 'patient' and user.id != patient.user.id:
                return PatientHistoryEntry.objects.none()
                
            # Doctores pueden ver el historial de sus pacientes
            if user.tipo == 'doctor':
                # Verificar si existe una relación doctor-paciente activa
                has_relation = DoctorPatientRelation.objects.filter(
                    doctor__user=user, 
                    patient=patient,
                    active=True
                ).exists()
                
                if not has_relation:
                    return PatientHistoryEntry.objects.none()
            
            # Retornar historial ordenado por fecha (más reciente primero)
            return PatientHistoryEntry.objects.filter(patient=patient).order_by('-created_at')
            
        except Patient.DoesNotExist:
            return PatientHistoryEntry.objects.none()

class PatientHistoryCreateView(APIView):
    """Vista para crear manualmente una entrada en el historial del paciente"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
            before_snapshot = patient.clinical_snapshot()
            
            # Verificar permisos
            user = request.user
            if user.tipo == 'patient' and user.id != patient.user.id:
                return Response(
                    {"error": "No tienes permisos para modificar este paciente"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            if user.tipo == 'doctor':
                # Verificar si es médico del paciente
                has_relation = DoctorPatientRelation.objects.filter(
                    doctor__user=user, 
                    patient=patient,
                    active=True
                ).exists()
                
                if not has_relation:
                    return Response(
                        {"error": "No eres médico asignado a este paciente"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Preparar datos para el historial
            history_data = {
                'patient': patient,
                'source': user.tipo,  # 'patient', 'doctor', 'admin'
                'created_by': user,
                'notes': request.data.get('notes', '')
            }
            
            # Campos médicos que se pueden actualizar
            medical_fields = [
                'triaje_level', 'pain_scale', 'medical_context',
                'allergies', 'medications', 'medical_history', 'ocupacion'
            ]
            
            # Copiar valores actuales al historial
            for field in medical_fields:
                history_data[field] = getattr(patient, field)
            
            # Opcional: actualizar campos si se proporcionan en la solicitud
            update_current = request.data.get('update_current', False)
            fields_to_update = []
            
            if update_current:
                for field in medical_fields:
                    if field in request.data and request.data[field] is not None:
                        # Guardar para actualizar el paciente después
                        setattr(patient, field, request.data[field])
                        fields_to_update.append(field)
            
            # Crear entrada de historial
            history_entry = PatientHistoryEntry.objects.create(**history_data)
            
            # Actualizar datos actuales del paciente si es necesario
            if update_current and fields_to_update:
                # Si es un médico, validar los datos
                if user.tipo == 'doctor':
                    doctor = Doctor.objects.get(user=user)
                    patient.is_data_validated = True
                    patient.data_validated_by = doctor
                    patient.data_validated_at = timezone.now()
                    fields_to_update.extend(['is_data_validated', 'data_validated_by', 'data_validated_at'])
                
                patient.save(update_fields=fields_to_update)
                patient.user.check_profile_completion()

            create_audit_entry(
                actor_user=user,
                actor_service=None,
                actor_ip=_request_ip(request),
                action='patient_history_create',
                resource_type='patient_history_entry',
                resource_id=str(history_entry.id),
                data_before=before_snapshot,
                data_after={
                    'history_entry': history_entry.clinical_snapshot(),
                    'patient': patient.clinical_snapshot(),
                },
            )
            
            return Response(
                PatientHistoryEntrySerializer(history_entry).data,
                status=status.HTTP_201_CREATED
            )
            
        except Patient.DoesNotExist:
            return Response(
                {"error": "Paciente no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Doctor.DoesNotExist:
            return Response(
                {"error": "Perfil de doctor no encontrado"},
                status=status.HTTP_400_BAD_REQUEST
            )

class PatientMeView(generics.RetrieveAPIView):
    """Vista para que un paciente vea su propio perfil médico"""
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        if self.request.user.tipo != 'patient':
            raise PermissionDenied("Solo los pacientes pueden acceder a esta vista")
        
        try:
            return Patient.objects.get(user=self.request.user)
        except Patient.DoesNotExist:
            raise Http404("No tienes un perfil de paciente configurado")

class PatientMeHistoryView(generics.ListAPIView):
    """Vista para que un paciente vea su propio historial médico"""
    serializer_class = PatientHistoryEntrySerializer
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination

    def _patient_from_token(self):
        token = self.request.query_params.get("token")
        if not token:
            return None
        try:
            data = signing.loads(token, salt="patient-history-access", max_age=300)
        except (BadSignature, SignatureExpired):
            return None
        if data.get("action") != "read_history":
            return None
        patient_id = data.get("patient_id")
        if not patient_id:
            return None
        try:
            return Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return None
    
    def get_queryset(self):
        patient = self._patient_from_token()
        if patient:
            return PatientHistoryEntry.objects.filter(patient=patient).order_by('-created_at')
        if not getattr(self.request.user, "is_authenticated", False):
            return PatientHistoryEntry.objects.none()
        if self.request.user.tipo != 'patient':
            return PatientHistoryEntry.objects.none()
        
        try:
            patient = Patient.objects.get(user=self.request.user)
            return PatientHistoryEntry.objects.filter(patient=patient).order_by('-created_at')
        except Patient.DoesNotExist:
            return PatientHistoryEntry.objects.none()


class PatientHistoryAccessTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.tipo != "patient":
            return Response({"error": "Solo los pacientes pueden solicitar este token."}, status=status.HTTP_403_FORBIDDEN)
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({"error": "No tienes un perfil de paciente configurado."}, status=status.HTTP_404_NOT_FOUND)

        token = signing.dumps(
            {"patient_id": str(patient.id), "action": "read_history"},
            salt="patient-history-access",
        )
        return Response({"token": token, "expires_in": 300}, status=status.HTTP_200_OK)
class DoctorViewSet(viewsets.ModelViewSet):
    """ViewSet para administrar doctores"""
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    pagination_class = PageNumberPagination  # Añadir paginación
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    def get_queryset(self):
        user = self.request.user
        # Los doctores solo pueden ver su propio perfil
        if user.tipo == 'doctor':
            return Doctor.objects.filter(user=user)
        # Administradores pueden ver todos los doctores
        elif user.tipo == 'admin':
            return Doctor.objects.all()
        # Pacientes pueden ver la lista de doctores pero sin detalles sensibles
        elif user.tipo == 'patient' and self.action == 'list':
            # Para pacientes, mostrar solo doctores activos
            return Doctor.objects.filter(user__is_active=True)
        return Doctor.objects.none()
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        # Incluir información del usuario asociado
        user_data = UserProfileSerializerBasic(instance.user).data
        data = serializer.data
        data['user'] = user_data
        return Response(data)
    
    @action(detail=True, methods=['get'])
    def patients(self, request, pk=None):
        """Acción para obtener los pacientes de un doctor específico"""
        doctor = self.get_object()
        
        # Verificar permisos
        if request.user.tipo not in ['admin', 'doctor'] or \
           (request.user.tipo == 'doctor' and request.user != doctor.user):
            return Response(
                {"error": "No tienes permisos para ver estos pacientes"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener pacientes activos del doctor
        patients = Patient.objects.filter(
            doctor_relations__doctor=doctor,
            doctor_relations__active=True
        ).distinct()
        
        # Configurar paginación
        paginator = PageNumberPagination()
        paginator.page_size = 10  # Puedes ajustar esto según necesites
        page = paginator.paginate_queryset(patients, request)
        
        if page is not None:
            serializer = PatientBasicSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        serializer = PatientBasicSerializer(patients, many=True)
        return Response(serializer.data)
    
class DoctorPatientRelationViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar relaciones entre doctores y pacientes"""
    serializer_class = DoctorPatientRelationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.tipo == 'patient':
            try:
                patient = Patient.objects.get(user=user)
                return DoctorPatientRelation.objects.filter(patient=patient)
            except Patient.DoesNotExist:
                return DoctorPatientRelation.objects.none()
        elif user.tipo == 'doctor':
            try:
                doctor = Doctor.objects.get(user=user)
                return DoctorPatientRelation.objects.filter(doctor=doctor)
            except Doctor.DoesNotExist:
                return DoctorPatientRelation.objects.none()
        elif user.tipo == 'admin':
            return DoctorPatientRelation.objects.all()
        return DoctorPatientRelation.objects.none()

    def perform_create(self, serializer):
        if self.request.user.tipo == 'doctor':
            doctor = Doctor.objects.get(user=self.request.user)
            serializer.save(doctor=doctor)
            return
        serializer.save()

    def create(self, request, *args, **kwargs):
        if request.user.tipo not in ['doctor', 'admin']:
            return Response(
                {"error": "No tienes permisos para crear relaciones médico-paciente"},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.tipo == 'doctor':
            doctor = Doctor.objects.filter(user=request.user).first()
            if not doctor:
                return Response(
                    {"error": "Perfil de doctor no encontrado"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            requested_doctor_id = request.data.get('doctor')
            if requested_doctor_id and str(requested_doctor_id) != str(doctor.id):
                return Response(
                    {"error": "No puedes crear relaciones para otro doctor"},
                    status=status.HTTP_403_FORBIDDEN
                )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        relation = self.get_object()
        if request.user.tipo == 'doctor':
            doctor = Doctor.objects.filter(user=request.user).first()
            if not doctor or relation.doctor_id != doctor.id:
                return Response(
                    {"error": "No tienes permisos para modificar esta relación"},
                    status=status.HTTP_403_FORBIDDEN
                )
            requested_doctor_id = request.data.get('doctor')
            if requested_doctor_id and str(requested_doctor_id) != str(doctor.id):
                return Response(
                    {"error": "No puedes reasignar esta relación a otro doctor"},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif request.user.tipo != 'admin':
            return Response(
                {"error": "No tienes permisos para modificar esta relación"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        relation = self.get_object()
        if request.user.tipo == 'doctor':
            doctor = Doctor.objects.filter(user=request.user).first()
            if not doctor or relation.doctor_id != doctor.id:
                return Response(
                    {"error": "No tienes permisos para eliminar esta relación"},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif request.user.tipo != 'admin':
            return Response(
                {"error": "No tienes permisos para eliminar esta relación"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    

class PasswordResetRequestView(APIView):
    """Vista para solicitar el restablecimiento de contraseña por código de verificación"""
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer
    throttle_classes = [PasswordResetRateThrottle]
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                
                # Generar un código de verificación de 6 dígitos
                verification_code = get_random_string(6, '0123456789')
                
                # Guardar el código en caché con un tiempo de expiración (15 minutos)
                cache_key = f"pwd_reset_{user.id}"
                cache.set(cache_key, verification_code, timeout=900)  # 900 segundos = 15 minutos
                
                # Enviar correo con el código de verificación
                subject = 'Código de verificación para restablecer tu contraseña'
                html_message = render_to_string('password_reset.html', {
                    'user': user,
                    'code': verification_code,
                    'valid_time': '15 minutos'
                })
                plain_message = f"""
                Hola {user.first_name},
                
                Has solicitado restablecer tu contraseña. Utiliza el siguiente código de verificación:
                
                {verification_code}
                
                Este código es válido por 15 minutos.
                
                Si no has solicitado este cambio, ignora este mensaje.
                
                Saludos,
                El equipo de soporte
                """
                
                send_mail(
                    subject,
                    plain_message,
                    settings.EMAIL_HOST_USER,
                    [email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                return Response(
                    {
                        "message": "Se ha enviado un código de verificación a tu correo electrónico.",
                        "expires_in": "15 minutos"
                    },
                    status=status.HTTP_200_OK
                )
            except User.DoesNotExist:
                # No revelamos si el correo existe o no por seguridad
                return Response(
                    {"message": "Si existe una cuenta con este correo, recibirás un código de verificación."},
                    status=status.HTTP_200_OK
                )
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetVerifyView(APIView):
    """Vista para verificar el código y restablecer la contraseña"""
    permission_classes = [AllowAny]
    serializer_class = PasswordResetVerifySerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            code = serializer.validated_data['code']
            new_password = serializer.validated_data['new_password']
            
            try:
                user = User.objects.get(email=email)
                
                # Recuperar el código de verificación de la caché
                cache_key = f"pwd_reset_{user.id}"
                stored_code = cache.get(cache_key)
                
                if not stored_code or stored_code != code:
                    return Response(
                        {"error": "El código de verificación es inválido o ha expirado."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Establecer la nueva contraseña
                user.set_password(new_password)
                user.save()
                
                # Eliminar el código de la caché
                cache.delete(cache_key)
                
                return Response(
                    {"message": "Tu contraseña ha sido restablecida correctamente. Ahora puedes iniciar sesión."},
                    status=status.HTTP_200_OK
                )
                
            except User.DoesNotExist:
                return Response(
                    {"error": "No se encontró ninguna cuenta con este correo electrónico."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    """Vista para cambiar la contraseña estando autenticado"""
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        user = request.user
        
        # Verificar la contraseña actual
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {"old_password": ["La contraseña actual es incorrecta."]},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Establecer la nueva contraseña
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Generar nuevos tokens para mantener la sesión del usuario
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "message": "Tu contraseña ha sido cambiada correctamente.",
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }, status=status.HTTP_200_OK)

class AccountDeleteView(APIView):
    """Vista para eliminación segura de cuenta mediante solicitudes DELETE"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        user_snapshot = {
            "id": str(request.user.id),
            "email": request.user.email,
            "tipo": request.user.tipo,
            "is_active": request.user.is_active,
        }

        # Para cuentas OAuth, no requiere contraseña
        if request.user.oauth_provider and request.user.oauth_uid:
            create_audit_entry(
                actor_user=request.user,
                actor_ip=_request_ip(request),
                action='account_delete',
                resource_type='user',
                resource_id=str(request.user.id),
                data_before=user_snapshot,
                data_after={"deleted": True},
            )
            request.user.delete()
            return Response(
                {"message": "Tu cuenta ha sido eliminada correctamente."},
                status=status.HTTP_204_NO_CONTENT
            )
        
        # Buscar la contraseña en el cuerpo de la solicitud
        password = None
        if hasattr(request, 'data') and request.data:
            password = request.data.get('password')
        
        # Para cuentas con contraseña, verificar la contraseña
        if not password:
            return Response(
                {"error": "Debes proporcionar tu contraseña para eliminar la cuenta."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not request.user.check_password(password):
            return Response(
                {"error": "La contraseña proporcionada es incorrecta."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Eliminar la cuenta
        create_audit_entry(
            actor_user=request.user,
            actor_ip=_request_ip(request),
            action='account_delete',
            resource_type='user',
            resource_id=str(request.user.id),
            data_before=user_snapshot,
            data_after={"deleted": True},
        )
        request.user.delete()
        return Response(
            {"message": "Tu cuenta ha sido eliminada correctamente."},
            status=status.HTTP_204_NO_CONTENT
        )
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            
            if not refresh_token:

                try:
                    # Get all outstanding tokens for this user
                    tokens = OutstandingToken.objects.filter(user_id=request.user.id)
                    # Blacklist all tokens
                    for token in tokens:
                        BlacklistedToken.objects.get_or_create(token=token)
                    
                    return Response(
                        {"message": "Todas las sesiones han sido cerradas correctamente."},
                        status=status.HTTP_205_RESET_CONTENT
                    )
                except Exception as e:
                    return Response(
                        {"error": "No se proporcionó token de refresh y no se pudieron invalidar todas las sesiones.", 
                         "details": str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # If refresh token is provided, blacklist it
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {"message": "Sesión cerrada correctamente."},
                status=status.HTTP_205_RESET_CONTENT
            )
        except TokenError as e:
            return Response(
                {"error": "Token inválido o ya revocado.", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "Error al cerrar sesión.", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
