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

class PatientClinicalSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='clinical_summary')
    summary_version = models.IntegerField(default=1)
    chief_complaint_current = models.CharField(max_length=255, blank=True, null=True)
    known_allergies = EncryptedTextField(blank=True, null=True)
    current_medications = EncryptedTextField(blank=True, null=True)
    medical_history_known = EncryptedTextField(blank=True, null=True)
    risk_factors = EncryptedTextField(blank=True, null=True)
    occupation_context = models.CharField(max_length=100, blank=True, null=True)
    baseline_pain_context = models.CharField(max_length=50, blank=True, null=True)
    recent_triage_history = models.JSONField(default=list, blank=True)
    active_episode_snapshot = models.JSONField(default=dict, blank=True)
    clinical_flags = models.JSONField(default=dict, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    last_source_update_at = models.DateTimeField(default=timezone.now)
    last_embedding_refresh_at = models.DateTimeField(blank=True, null=True)
    is_validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(
        'Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_clinical_summaries'
    )
    validated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('resumen clínico del paciente')
        verbose_name_plural = _('resúmenes clínicos del paciente')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Resumen clínico IA de {self.patient.user.email}"

    def save(self, *args, **kwargs):
        if self.chief_complaint_current:
            self.chief_complaint_current = sanitize_input(self.chief_complaint_current)
        if self.occupation_context:
            self.occupation_context = sanitize_input(self.occupation_context)
        if self.baseline_pain_context:
            self.baseline_pain_context = sanitize_input(self.baseline_pain_context)
        if self.known_allergies:
            self.known_allergies = sanitize_input(self.known_allergies)
        if self.current_medications:
            self.current_medications = sanitize_input(self.current_medications)
        if self.medical_history_known:
            self.medical_history_known = sanitize_input(self.medical_history_known)
        if self.risk_factors:
            self.risk_factors = sanitize_input(self.risk_factors)
        super().save(*args, **kwargs)

    def clinical_snapshot(self):
        return {
            'id': str(self.id),
            'patient_id': str(self.patient_id),
            'summary_version': self.summary_version,
            'chief_complaint_current': self.chief_complaint_current,
            'known_allergies': self.known_allergies,
            'current_medications': self.current_medications,
            'medical_history_known': self.medical_history_known,
            'risk_factors': self.risk_factors,
            'occupation_context': self.occupation_context,
            'baseline_pain_context': self.baseline_pain_context,
            'recent_triage_history': self.recent_triage_history,
            'active_episode_snapshot': self.active_episode_snapshot,
            'clinical_flags': self.clinical_flags,
            'summary': self.summary,
            'last_source_update_at': self.last_source_update_at.isoformat() if self.last_source_update_at else None,
            'last_embedding_refresh_at': self.last_embedding_refresh_at.isoformat() if self.last_embedding_refresh_at else None,
            'is_validated': self.is_validated,
            'validated_by': str(self.validated_by_id) if self.validated_by_id else None,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def refresh_from_patient_snapshot(self, *, patient_snapshot=None, triage_history=None, episode_snapshot=None):
        patient_snapshot = patient_snapshot or self.patient.clinical_snapshot()
        triage_history = triage_history if triage_history is not None else self.recent_triage_history
        episode_snapshot = episode_snapshot if episode_snapshot is not None else self.active_episode_snapshot

        self.known_allergies = patient_snapshot.get('allergies')
        self.current_medications = patient_snapshot.get('medications')
        self.medical_history_known = patient_snapshot.get('medical_history')
        self.occupation_context = patient_snapshot.get('ocupacion')
        pain_scale = patient_snapshot.get('pain_scale')
        self.baseline_pain_context = str(pain_scale) if pain_scale is not None else None
        self.recent_triage_history = triage_history or []
        self.active_episode_snapshot = episode_snapshot or {}
        facts_summary = self.active_episode_snapshot.get('facts_summary', {}) if isinstance(self.active_episode_snapshot, dict) else {}
        current_chief_complaints = facts_summary.get('chief_complaints', []) if isinstance(facts_summary, dict) else []
        self.chief_complaint_current = ", ".join(current_chief_complaints[:2]) or self.chief_complaint_current
        self.summary = {
            'triaje_level': patient_snapshot.get('triaje_level'),
            'pain_scale': pain_scale,
            'allergies': patient_snapshot.get('allergies'),
            'medications': patient_snapshot.get('medications'),
            'medical_history': patient_snapshot.get('medical_history'),
            'ocupacion': patient_snapshot.get('ocupacion'),
            'active_episode_snapshot': self.active_episode_snapshot,
            'recent_triage_history': self.recent_triage_history,
        }
        self.last_source_update_at = timezone.now()

    def _derived_age(self):
        birth_date = getattr(self.patient.user, 'fecha_nacimiento', None)
        if not birth_date:
            return None
        today = timezone.now().date()
        years = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return years if years >= 0 else None

    def build_summary_payload(self):
        payload = {
            'chief_complaint_current': self.chief_complaint_current,
            'known_allergies': self.known_allergies,
            'current_medications': self.current_medications,
            'medical_history_known': self.medical_history_known,
            'risk_factors': self.risk_factors,
            'occupation_context': self.occupation_context,
            'gender': getattr(self.patient.user, 'genero', None),
            'baseline_pain_context': self.baseline_pain_context,
            'recent_triage_history': self.recent_triage_history or [],
            'active_episode_snapshot': self.active_episode_snapshot or {},
            'clinical_flags': self.clinical_flags or {},
            'age_years': self._derived_age(),
            'is_validated': self.is_validated,
            'summary_version': self.summary_version,
        }
        return {key: value for key, value in payload.items() if value not in (None, '', [], {})}

    def build_summary_text(self):
        payload = self.build_summary_payload()
        fragments = []
        if payload.get('age_years') is not None:
            fragments.append(f"edad: {payload['age_years']}")
        if payload.get('chief_complaint_current'):
            fragments.append(f"motivo_actual: {payload['chief_complaint_current']}")
        if payload.get('known_allergies'):
            fragments.append(f"alergias: {payload['known_allergies']}")
        if payload.get('current_medications'):
            fragments.append(f"medicacion_actual: {payload['current_medications']}")
        if payload.get('medical_history_known'):
            fragments.append(f"antecedentes: {payload['medical_history_known']}")
        if payload.get('risk_factors'):
            fragments.append(f"factores_riesgo: {payload['risk_factors']}")
        if payload.get('occupation_context'):
            fragments.append(f"ocupacion: {payload['occupation_context']}")
        if payload.get('gender'):
            fragments.append(f"sexo: {payload['gender']}")
        if payload.get('baseline_pain_context'):
            fragments.append(f"dolor_reportado: {payload['baseline_pain_context']}")
        triage_history = payload.get('recent_triage_history') or []
        if triage_history:
            fragments.append("triajes_recientes: " + ", ".join(str(item) for item in triage_history[:3]))
        episode_snapshot = payload.get('active_episode_snapshot') or {}
        facts_summary = episode_snapshot.get('facts_summary', {}) if isinstance(episode_snapshot, dict) else {}
        symptoms = facts_summary.get('symptoms', []) if isinstance(facts_summary, dict) else []
        if symptoms:
            fragments.append("sintomas_actuales: " + ", ".join(symptoms[:3]))
        red_flags = facts_summary.get('red_flags', []) if isinstance(facts_summary, dict) else []
        if red_flags:
            fragments.append("red_flags: " + ", ".join(red_flags[:2]))
        return " | ".join(fragments)

    def sync_from_patient(self, *, triage_history=None, episode_snapshot=None, clinical_flags=None, save=True):
        previous_payload = self.summary.copy() if isinstance(self.summary, dict) else {}
        self.refresh_from_patient_snapshot(
            patient_snapshot=self.patient.clinical_snapshot(),
            triage_history=triage_history,
            episode_snapshot=episode_snapshot,
        )
        if clinical_flags is not None:
            self.clinical_flags = clinical_flags
        if previous_payload and previous_payload != self.summary:
            self.summary_version += 1
        if save:
            self.save()
        return self
