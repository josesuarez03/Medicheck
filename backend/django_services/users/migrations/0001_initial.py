import uuid

import common.security.encrypted_fields
import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={"unique": "A user with that username already exists."},
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                        verbose_name="username",
                    ),
                ),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254, unique=True, verbose_name="email address")),
                ("oauth_provider", models.CharField(blank=True, max_length=50, null=True)),
                ("oauth_uid", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "tipo",
                    models.CharField(
                        choices=[("admin", "Administrador"), ("patient", "Paciente"), ("doctor", "Doctor")],
                        default="patient",
                        max_length=10,
                    ),
                ),
                ("fecha_nacimiento", models.DateField(blank=True, null=True)),
                ("telefono", models.CharField(blank=True, max_length=20, null=True)),
                ("direccion", models.CharField(blank=True, max_length=255, null=True)),
                ("genero", models.CharField(blank=True, max_length=10, null=True)),
                ("is_profile_completed", models.BooleanField(default=False, verbose_name="Perfil completado")),
                ("date_joined", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "usuario",
                "verbose_name_plural": "usuarios",
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("actor_service", models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ("actor_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("action", models.CharField(db_index=True, max_length=100)),
                ("resource_type", models.CharField(db_index=True, max_length=100)),
                ("resource_id", models.CharField(db_index=True, max_length=100)),
                ("data_before", models.JSONField(blank=True, null=True)),
                ("data_after", models.JSONField(blank=True, null=True)),
                ("content_hash", models.CharField(max_length=64)),
                ("signature", models.CharField(max_length=64)),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "actor_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "registro de auditoría",
                "verbose_name_plural": "registros de auditoría",
                "ordering": ["-timestamp"],
                "indexes": [
                    models.Index(fields=["resource_type", "resource_id", "timestamp"], name="users_auditr_resourc_49dcd5_idx"),
                    models.Index(fields=["actor_user", "timestamp"], name="users_auditr_actor_u_9d0ee6_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Doctor",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("especialidad", models.CharField(blank=True, max_length=100, null=True)),
                ("numero_licencia", models.CharField(blank=True, max_length=50, null=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="doctor",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "doctor",
                "verbose_name_plural": "doctores",
            },
        ),
        migrations.CreateModel(
            name="Patient",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("triaje_level", models.CharField(blank=True, max_length=20, null=True)),
                ("ocupacion", models.CharField(blank=True, max_length=100, null=True)),
                ("pain_scale", models.IntegerField(blank=True, null=True)),
                ("medical_context", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                ("allergies", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                ("medications", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                ("medical_history", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                (
                    "data_validated_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "is_data_validated",
                    models.BooleanField(
                        default=False,
                        help_text="Indica si los datos médicos han sido validados por un médico",
                    ),
                ),
                ("last_chatbot_analysis", models.DateTimeField(blank=True, null=True)),
                (
                    "data_validated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="validated_patients",
                        to="users.doctor",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="patient",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "paciente",
                "verbose_name_plural": "pacientes",
            },
        ),
        migrations.CreateModel(
            name="PatientClinicalSummary",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("summary_version", models.IntegerField(default=1)),
                ("chief_complaint_current", models.CharField(blank=True, max_length=255, null=True)),
                ("known_allergies", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                ("current_medications", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                ("medical_history_known", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                ("risk_factors", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                ("occupation_context", models.CharField(blank=True, max_length=100, null=True)),
                ("baseline_pain_context", models.CharField(blank=True, max_length=50, null=True)),
                ("recent_triage_history", models.JSONField(blank=True, default=list)),
                ("active_episode_snapshot", models.JSONField(blank=True, default=dict)),
                ("clinical_flags", models.JSONField(blank=True, default=dict)),
                ("summary", models.JSONField(blank=True, default=dict)),
                ("last_source_update_at", models.DateTimeField(default=timezone.now)),
                ("last_embedding_refresh_at", models.DateTimeField(blank=True, null=True)),
                ("is_validated", models.BooleanField(default=False)),
                ("validated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "patient",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="clinical_summary",
                        to="users.patient",
                    ),
                ),
                (
                    "validated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="validated_clinical_summaries",
                        to="users.doctor",
                    ),
                ),
            ],
            options={
                "verbose_name": "resumen clínico del paciente",
                "verbose_name_plural": "resúmenes clínicos del paciente",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="PatientHistoryEntry",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("triaje_level", models.CharField(blank=True, max_length=20, null=True)),
                ("pain_scale", models.IntegerField(blank=True, null=True)),
                ("medical_context", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                ("allergies", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                ("medications", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                ("medical_history", common.security.encrypted_fields.EncryptedTextField(blank=True, null=True)),
                ("ocupacion", models.CharField(blank=True, max_length=100, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("chatbot", "Chatbot"),
                            ("doctor", "Doctor"),
                            ("patient", "Paciente"),
                            ("admin", "Administrador"),
                        ],
                        default="chatbot",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True, help_text="Notas o razón del cambio", null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_history_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history_entries",
                        to="users.patient",
                    ),
                ),
            ],
            options={
                "verbose_name": "entrada de historial del paciente",
                "verbose_name_plural": "entradas de historial del paciente",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DoctorPatientRelation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "is_primary_doctor",
                    models.BooleanField(
                        default=False,
                        help_text="Indica si este doctor es el médico primario del paciente",
                    ),
                ),
                ("start_date", models.DateField(auto_now_add=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True, null=True)),
                (
                    "doctor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="patient_relations",
                        to="users.doctor",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="doctor_relations",
                        to="users.patient",
                    ),
                ),
            ],
            options={
                "verbose_name": "relación médico-paciente",
                "verbose_name_plural": "relaciones médico-paciente",
                "unique_together": {("doctor", "patient", "active")},
            },
        ),
    ]
