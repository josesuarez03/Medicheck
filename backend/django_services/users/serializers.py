from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from .models import Patient, Doctor, DoctorPatientRelation, PatientHistoryEntry

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'password2', 'first_name', 'last_name', 'tipo')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            tipo=validated_data.get('tipo', 'patient')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class DoctorBasicSerializer(serializers.ModelSerializer):
    """Serializador básico para información de doctores"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Doctor
        fields = ('id', 'especialidad', 'full_name')
    
    def get_full_name(self, obj):
        return f"Dr. {obj.user.first_name} {obj.user.last_name}"

class PatientBasicSerializer(serializers.ModelSerializer):
    """Serializador básico para información de pacientes"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = ('id', 'full_name', 'is_data_validated')
    
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

class DoctorPatientRelationSerializer(serializers.ModelSerializer):
    """Serializador para la relación médico-paciente"""
    doctor_name = serializers.SerializerMethodField(read_only=True)
    patient_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = DoctorPatientRelation
        fields = ('id', 'doctor', 'doctor_name', 'patient', 'patient_name', 
                 'is_primary_doctor', 'start_date', 'end_date', 'active', 'notes')
        read_only_fields = ('id', 'doctor_name', 'patient_name')
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.user.first_name} {obj.doctor.user.last_name}"
    
    def get_patient_name(self, obj):
        return f"{obj.patient.user.first_name} {obj.patient.user.last_name}"

class PatientSerializer(serializers.ModelSerializer):
    doctors = DoctorBasicSerializer(many=True, read_only=True)
    data_validator = serializers.SerializerMethodField(read_only=True)
    history_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Patient
        fields = ('id', 'triaje_level', 'ocupacion', 'pain_scale', 'medical_context', 
                  'allergies', 'medications', 'medical_history', 'last_chatbot_analysis',
                  'is_data_validated', 'data_validated_by', 'data_validated_at', 
                  'data_validator', 'doctors', 'history_count')
        read_only_fields = ('id', 'last_chatbot_analysis', 'data_validated_at', 
                           'data_validator', 'doctors', 'history_count')
    
    def get_data_validator(self, obj):
        if obj.data_validated_by:
            return f"Dr. {obj.data_validated_by.user.first_name} {obj.data_validated_by.user.last_name}"
        return None
    
    def get_history_count(self, obj):
        return obj.history_entries.count()

class DoctorSerializer(serializers.ModelSerializer):
    patients = PatientBasicSerializer(many=True, read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Doctor
        fields = ('id', 'especialidad', 'numero_licencia', 'patients', 'full_name')
        read_only_fields = ('id', 'patients', 'full_name')
    
    def get_full_name(self, obj):
        return f"Dr. {obj.user.first_name} {obj.user.last_name}"


class UserProfileSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(required=False)
    doctor = DoctorSerializer(required=False)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'tipo',
                  'fecha_nacimiento', 'genero', 'telefono', 'direccion', 
                  'is_profile_completed', 'patient', 'doctor', 'date_joined', 
                  'last_login', 'is_active')
        read_only_fields = ('id', 'email', 'username', 'is_profile_completed', 
                            'date_joined', 'last_login')

    def update(self, instance, validated_data):
        patient_data = validated_data.pop('patient', None)
        doctor_data = validated_data.pop('doctor', None)
        
        # Actualizar campos del usuario
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Actualizar o crear el perfil de paciente si es necesario
        if instance.tipo == 'patient' and patient_data:
            patient, created = Patient.objects.get_or_create(user=instance)
            for attr, value in patient_data.items():
                setattr(patient, attr, value)
            patient.save()
        
        # Actualizar o crear el perfil de doctor si es necesario
        if instance.tipo == 'doctor' and doctor_data:
            doctor, created = Doctor.objects.get_or_create(user=instance)
            for attr, value in doctor_data.items():
                setattr(doctor, attr, value)
            doctor.save()
        
        instance.save()
        # Verificar si el perfil está completo
        instance.check_profile_completion()
        return instance

class UserProfileSerializerBasic(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 
                 'is_profile_completed', 'is_active', 'date_joined', 'last_login', 'tipo')
        read_only_fields = ('id', 'email', 'username', 'is_profile_completed', 
                           'date_joined', 'last_login')

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        # Verificar si el perfil está completo
        instance.check_profile_completion()
        return instance

class GoogleOAuthUserInfoSerializer(serializers.Serializer):
    """Serializador para recibir información de Google OAuth"""
    token = serializers.CharField(required=True)

class RequiredOAuthUserSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=User.TIPO_USER, required=False)
    fecha_nacimiento = serializers.DateField(required=True)
    telefono = serializers.CharField(required=True)
    direccion = serializers.CharField(required=True)
    genero = serializers.CharField(required=False)
    
    # Campos para pacientes - Estos son los únicos requeridos inicialmente
    allergies = serializers.CharField(required=False)
    ocupacion = serializers.CharField(required=False)
    
    # Campos para médicos
    especialidad = serializers.CharField(required=False)
    numero_licencia = serializers.CharField(required=False)
    
    # Campo para actualizar el estado del perfil
    is_profile_completed = serializers.BooleanField(required=False)
    
    def validate(self, attrs):
 
        request = self.context.get('request')
        if request and request.method in ['PUT', 'PATCH', 'POST'] and 'tipo' not in attrs:

            if request.user and hasattr(request.user, 'tipo') and request.user.tipo:
                return attrs
        
        tipo = attrs.get('tipo')
        
        # Validar campos según el tipo de usuario cuando se proporciona un tipo
        if tipo == 'patient':
            if request and request.method == 'POST':  # Solo validar en creación
                if not attrs.get('allergies') and not any(field in self.initial_data for field in ['allergies', 'ocupacion']):
                    raise serializers.ValidationError({"allergies": "Este campo es requerido para pacientes"})
                if not attrs.get('ocupacion') and not any(field in self.initial_data for field in ['allergies', 'ocupacion']):
                    raise serializers.ValidationError({"ocupacion": "Este campo es requerido para pacientes"})
        
        elif tipo == 'doctor':
            if not attrs.get('especialidad'):
                raise serializers.ValidationError({"especialidad": "Este campo es requerido para médicos"})
            if not attrs.get('numero_licencia'):
                raise serializers.ValidationError({"numero_licencia": "Este campo es requerido para médicos"})
        
        return attrs

class ChatbotAnalysisSerializer(serializers.Serializer):
    """Serializador para validar datos del análisis del chatbot"""
    triaje_level = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    pain_scale = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=10)
    medical_context = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    allergies = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    medications = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    medical_history = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    ocupacion = serializers.CharField(required=False, allow_null=True, allow_blank=True)

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class PasswordResetVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    new_password = serializers.CharField(required=False, allow_blank=False)
    confirm_password = serializers.CharField(required=False, allow_blank=False)
    
    def validate(self, data):
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if bool(new_password) != bool(confirm_password):
            raise serializers.ValidationError(
                {"confirm_password": "Debes proporcionar y confirmar la nueva contraseña."}
            )

        if new_password and new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "Las contraseñas no coinciden"})
        return data
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Las contraseñas no coinciden"})
        return data

class AccountDeleteSerializer(serializers.Serializer):
    password = serializers.CharField(required=False)

class PatientHistoryEntrySerializer(serializers.ModelSerializer):
    """Serializador para las entradas del historial médico del paciente"""
    created_by_name = serializers.SerializerMethodField(read_only=True)
    source_display = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = PatientHistoryEntry
        fields = ('id', 'created_at', 'source', 'source_display', 'created_by', 'created_by_name',
                  'notes', 'triaje_level', 'pain_scale', 'medical_context', 'allergies',
                  'medications', 'medical_history', 'ocupacion')
        read_only_fields = ('id', 'created_at', 'created_by_name', 'source_display')
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            if obj.created_by.tipo == 'doctor':
                return f"Dr. {obj.created_by.first_name} {obj.created_by.last_name}"
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None
    
    def get_source_display(self, obj):
        return dict(PatientHistoryEntry._meta.get_field('source').choices).get(obj.source)
