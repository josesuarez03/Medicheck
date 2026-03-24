import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from common.security.encrypted_fields import EncryptedTextField
from common.security.utils import sanitize_input

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    oauth_provider = models.CharField(max_length=50, blank=True, null=True)
    oauth_uid = models.CharField(max_length=255, blank=True, null=True)

    TIPO_USER = (
        ('admin', 'Administrador'),
        ('patient', 'Paciente'),
        ('doctor', 'Doctor'),
    )

    tipo = models.CharField(max_length=10, choices=TIPO_USER, default='patient')
    fecha_nacimiento = models.DateField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    #foto = models.ImageField(upload_to='users/', blank=True, null=True)
    genero = models.CharField(max_length=10, blank=True, null=True)
 
    # Control de perfil
    is_profile_completed = models.BooleanField(default=False, verbose_name="Perfil completado")
    date_joined = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('usuario')
        verbose_name_plural = _('usuarios')
        
    def __str__(self):
        return f"{self.email} ({self.get_tipo_display()})"
    
    def check_profile_completion(self, **kwargs):
        """Verifica si el perfil del usuario está completo según su tipo"""
        # Campos base que son requeridos para todos los tipos de usuarios
        base_fields = [self.first_name, self.last_name, self.fecha_nacimiento, self.telefono, self.direccion]
        
        if self.tipo == 'patient':
            # Para pacientes, solo verificamos que los campos base estén completos
            # y que el modelo Patient esté creado (los campos médicos pueden estar vacíos)
            patient = getattr(self, 'patient', None)
            if all(base_fields) and patient is not None:
                # La ocupación y alergias son los únicos campos requeridos inicialmente
                if patient.ocupacion and patient.allergies:
                    self.is_profile_completed = True
                else:
                    self.is_profile_completed = False
            else:
                self.is_profile_completed = False
                
        elif self.tipo == 'doctor':
            # Para doctores, verificamos campos base y profesionales
            doctor = getattr(self, 'doctor', None)
            if all(base_fields) and doctor is not None:
                if doctor.especialidad and doctor.numero_licencia:
                    self.is_profile_completed = True
                else:
                    self.is_profile_completed = False
            else:
                self.is_profile_completed = False
                
        elif self.tipo == 'admin':
            # Para administradores, solo la información básica
            if all(base_fields):
                self.is_profile_completed = True
            else:
                self.is_profile_completed = False
        
        # Guardar solo el campo actualizado para evitar modificar otros campos
        # si este método se llama como parte de otro proceso de guardado
        if 'update_fields' not in kwargs or kwargs['update_fields'] is None:
            self.save(update_fields=['is_profile_completed'])
        elif 'is_profile_completed' not in kwargs['update_fields']:
            kwargs['update_fields'].append('is_profile_completed')
            self.save(**kwargs)
        return self.is_profile_completed
    
    def save(self, *args, **kwargs):
        # Sanitizar los campos sensibles antes de guardar
        if self.first_name:
            self.first_name = sanitize_input(self.first_name)
        if self.last_name:
            self.last_name = sanitize_input(self.last_name)
        if self.telefono:
            self.telefono = sanitize_input(self.telefono)
        if self.direccion:
            self.direccion = sanitize_input(self.direccion)
        if self.oauth_provider:
            self.oauth_provider = sanitize_input(self.oauth_provider)
        if self.oauth_uid:
            self.oauth_uid = sanitize_input(self.oauth_uid)
        super().save(*args, **kwargs)

class Doctor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor')

    # Información profesional (si es médico)
    especialidad = models.CharField(max_length=100, blank=True, null=True)
    numero_licencia = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        verbose_name = _('doctor')
        verbose_name_plural = _('doctores')
        
    def __str__(self):
        return f"{self.user.email} ({self.user.get_tipo_display()})"
    
    def save(self, *args, **kwargs):
        # Asegurar que el tipo de usuario es doctor
        if self.user.tipo != 'doctor':
            self.user.tipo = 'doctor'
            self.user.save(update_fields=['tipo'])

        if self.especialidad:
            self.especialidad = sanitize_input(self.especialidad)
        if self.numero_licencia:
            self.numero_licencia = sanitize_input(self.numero_licencia)
        super().save(*args, **kwargs)

class Patient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient')
    

    # Campos que pueden ser completados por el chatbot
    triaje_level = models.CharField(max_length=20, blank=True, null=True)
    ocupacion = models.CharField(max_length=100, blank=True, null=True)
    pain_scale = models.IntegerField(blank=True, null=True)
    medical_context = EncryptedTextField(blank=True, null=True)
    allergies = EncryptedTextField(blank=True, null=True)
    medications = EncryptedTextField(blank=True, null=True)
    medical_history = EncryptedTextField(blank=True, null=True)
    
    # Campos para validación de datos por médicos
    data_validated_by = models.ForeignKey('Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='validated_patients')
    data_validated_at = models.DateTimeField(null=True, blank=True)
    is_data_validated = models.BooleanField(default=False, help_text="Indica si los datos médicos han sido validados por un médico")
    
    # Campo para seguimiento del análisis del chatbot
    last_chatbot_analysis = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = _('paciente')
        verbose_name_plural = _('pacientes')
        
    def __str__(self):
        return f"{self.user.email} ({self.user.get_tipo_display()})"
    
    def save(self, *args, **kwargs):
        # Asegurar que el tipo de usuario es paciente
        if self.user.tipo != 'patient':
            self.user.tipo = 'patient'
            self.user.save(update_fields=['tipo'])

        # Sanitizar los campos proporcionados
        if self.triaje_level:
            self.triaje_level = sanitize_input(self.triaje_level)
        if self.ocupacion:
            self.ocupacion = sanitize_input(self.ocupacion)
        if self.medical_context:
            self.medical_context = sanitize_input(self.medical_context)
        if self.allergies:
            self.allergies = sanitize_input(self.allergies)
        if self.medications:
            self.medications = sanitize_input(self.medications)
        if self.medical_history:
            self.medical_history = sanitize_input(self.medical_history)

        super().save(*args, **kwargs)

    def update_from_chatbot_analysis(self, analysis_data, created_by=None):
        # Campos que pueden ser actualizados desde el chatbot
        chatbot_fields = [
            'triaje_level', 'pain_scale', 'medical_context',
            'allergies', 'medications', 'medical_history', 'ocupacion'
        ]
        
        # Verificar si hay cambios reales en los datos
        has_changes = False
        for field in chatbot_fields:
            if field in analysis_data and getattr(self, field) != analysis_data[field]:
                has_changes = True
                break
        
        if has_changes:
            # Crear una entrada en el historial antes de actualizar los datos
            history_data = {
                'patient': self,
                'source': 'chatbot',
                'created_by': created_by,
                'notes': 'Actualización automática desde análisis del chatbot'
            }
            
            # Copiar los valores actuales al historial
            for field in chatbot_fields:
                history_data[field] = getattr(self, field)
            
            # Crear la entrada de historial
            PatientHistoryEntry.objects.create(**history_data)
            
            # Actualizar los campos que vienen en el análisis
            fields_updated = []
            for field in chatbot_fields:
                if field in analysis_data and analysis_data[field] is not None:
                    setattr(self, field, analysis_data[field])
                    fields_updated.append(field)
            
            # Registrar la fecha del análisis
            self.last_chatbot_analysis = timezone.now()
            fields_updated.append('last_chatbot_analysis')
            
            # Resetear validación médica cuando se actualizan datos por chatbot
            self.is_data_validated = False
            self.data_validated_by = None
            self.data_validated_at = None
            fields_updated.extend(['is_data_validated', 'data_validated_by', 'data_validated_at'])
            
            # Guardar cambios si hay algún campo actualizado
            if fields_updated:
                self.save(update_fields=fields_updated)
                # Verificar si con estos cambios el perfil ahora está completo
                self.user.check_profile_completion()
                return True
        
        return False

    def clinical_snapshot(self):
        return {
            'triaje_level': self.triaje_level,
            'pain_scale': self.pain_scale,
            'medical_context': self.medical_context,
            'allergies': self.allergies,
            'medications': self.medications,
            'medical_history': self.medical_history,
            'ocupacion': self.ocupacion,
            'is_data_validated': self.is_data_validated,
            'data_validated_by': str(self.data_validated_by_id) if self.data_validated_by_id else None,
            'data_validated_at': self.data_validated_at.isoformat() if self.data_validated_at else None,
            'last_chatbot_analysis': self.last_chatbot_analysis.isoformat() if self.last_chatbot_analysis else None,
        }

class DoctorPatientRelation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey('Doctor', on_delete=models.CASCADE, related_name='patient_relations')
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='doctor_relations')
    is_primary_doctor = models.BooleanField(default=False, help_text="Indica si este doctor es el médico primario del paciente")
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('doctor', 'patient', 'active')
        verbose_name = _('relación médico-paciente')
        verbose_name_plural = _('relaciones médico-paciente')
        
    def __str__(self):
        return f"Dr. {self.doctor.user.last_name} - Paciente: {self.patient.user.last_name} ({self.start_date})"
    
    def save(self, *args, **kwargs):
        if self.notes:
            self.notes = sanitize_input(self.notes)
        super().save(*args, **kwargs)

class PatientHistoryEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='history_entries')
    
    # Campos médicos - copia de los campos en Patient
    triaje_level = models.CharField(max_length=20, blank=True, null=True)
    pain_scale = models.IntegerField(blank=True, null=True)
    medical_context = EncryptedTextField(blank=True, null=True)
    allergies = EncryptedTextField(blank=True, null=True)
    medications = EncryptedTextField(blank=True, null=True)
    medical_history = EncryptedTextField(blank=True, null=True)
    ocupacion = models.CharField(max_length=100, blank=True, null=True)
    
    # Metadatos del registro
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_history_entries')
    source = models.CharField(max_length=20, choices=(
        ('chatbot', 'Chatbot'),
        ('doctor', 'Doctor'),
        ('patient', 'Paciente'),
        ('admin', 'Administrador'),
    ), default='chatbot')
    notes = models.TextField(blank=True, null=True, help_text="Notas o razón del cambio")

    class Meta:
        verbose_name = _('entrada de historial del paciente')
        verbose_name_plural = _('entradas de historial del paciente')
        ordering = ['-created_at']  # Ordenar por fecha más reciente primero
    
    def __str__(self):
        return f"Historial de {self.patient.user.last_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        if self.notes:
            self.notes = sanitize_input(self.notes)
        if self.medical_context:
            self.medical_context = sanitize_input(self.medical_context)
        if self.allergies:
            self.allergies = sanitize_input(self.allergies)
        if self.medications:
            self.medications = sanitize_input(self.medications)
        if self.medical_history:
            self.medical_history = sanitize_input(self.medical_history)
        if self.ocupacion:
            self.ocupacion = sanitize_input(self.ocupacion)
        super().save(*args, **kwargs)

    def clinical_snapshot(self):
        return {
            'id': str(self.id),
            'patient_id': str(self.patient_id),
            'triaje_level': self.triaje_level,
            'pain_scale': self.pain_scale,
            'medical_context': self.medical_context,
            'allergies': self.allergies,
            'medications': self.medications,
            'medical_history': self.medical_history,
            'ocupacion': self.ocupacion,
            'source': self.source,
            'created_by': str(self.created_by_id) if self.created_by_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'notes': self.notes,
        }


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    actor_service = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    actor_ip = models.GenericIPAddressField(blank=True, null=True)
    action = models.CharField(max_length=100, db_index=True)
    resource_type = models.CharField(max_length=100, db_index=True)
    resource_id = models.CharField(max_length=100, db_index=True)
    data_before = models.JSONField(blank=True, null=True)
    data_after = models.JSONField(blank=True, null=True)
    content_hash = models.CharField(max_length=64)
    signature = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('registro de auditoría')
        verbose_name_plural = _('registros de auditoría')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['resource_type', 'resource_id', 'timestamp']),
            models.Index(fields=['actor_user', 'timestamp']),
        ]
