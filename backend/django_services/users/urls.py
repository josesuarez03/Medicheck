from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from .views import (
    RegisterUserView, GoogleOAuthLoginView, CompleteProfileView,
    UserProfileView, UserViewSet, PasswordResetRequestView, 
    PasswordResetVerifyView, ChangePasswordView, AccountDeleteView, 
    PatientHistoryCreateView, PatientHistoryViewSet, PatientViewSet,
    DoctorViewSet, PatientMeView, 
    PatientMeHistoryView, DoctorPatientRelationViewSet, PatientMedicalDataUpdateView, LoginView, LogoutView,
    PatientHistoryAccessTokenView,
)

router = DefaultRouter()
router.register(r'admin/users', UserViewSet)
router.register(r'patients/(?P<patient_id>[^/.]+)/history', PatientHistoryViewSet, basename='patient-history')
router.register(r'patients', PatientViewSet, basename='patients')
router.register(r'doctors', DoctorViewSet, basename='doctors')
router.register(r'doctor-patient-relations', DoctorPatientRelationViewSet, basename='doctor-patient-relations')

urlpatterns = [
    # Autenticación básica
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterUserView.as_view(), name='register'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Google OAuth
    path('google/login/', GoogleOAuthLoginView.as_view(), name='google_oauth_login'),
    
    # Perfil de usuario
    path('complete/', CompleteProfileView.as_view(), name='complete_profile'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    
    # Gestión de contraseñas
    path('password/reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password/reset/verify/', PasswordResetVerifyView.as_view(), name='password_reset_verify'),
    path('password/change/', ChangePasswordView.as_view(), name='change_password'),
    
    # Eliminación de cuenta
    path('account/delete/', AccountDeleteView.as_view(), name='account_delete'),

    # Historial médico
    path('patients/<uuid:patient_id>/history/create/', PatientHistoryCreateView.as_view(), name='patient-history-create'),
    
    # Vistas específicas para pacientes
    path('patients/me/', PatientMeView.as_view(), name='patient-me'),
    path('patients/me/history/token/', PatientHistoryAccessTokenView.as_view(), name='patient-me-history-token'),
    path('patients/me/history/', PatientMeHistoryView.as_view(), name='patient-me-history'),
    

    # Actualización de datos médicos por Flask
    path('api/patients/medical_data_update/', PatientMedicalDataUpdateView.as_view(), name='medical_data_update'),
    
    # ViewSets
    path('', include(router.urls)),
]
