from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import connection

from common.security.encrypted_fields import ENCRYPTED_VALUE_PREFIX
from users.models import Patient, PatientHistoryEntry


ENCRYPTED_FIELDS = (
    "medical_context",
    "allergies",
    "medications",
    "medical_history",
)


class Command(BaseCommand):
    help = "Cifra en reposo los campos clinicos legacy que aun siguen en texto plano."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Muestra cuantos registros se actualizarian sin guardar cambios.")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        patient_updates = self._backfill_queryset(Patient.objects.all(), dry_run=dry_run)
        history_updates = self._backfill_queryset(PatientHistoryEntry.objects.all(), dry_run=dry_run)
        mode = "dry-run" if dry_run else "apply"
        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill {mode} completado. Patients actualizados: {patient_updates}. "
                f"PatientHistoryEntry actualizados: {history_updates}."
            )
        )

    def _backfill_queryset(self, queryset, *, dry_run: bool) -> int:
        updates = 0
        pk_name = queryset.model._meta.pk.attname
        table_name = queryset.model._meta.db_table
        select_fields = ", ".join([pk_name, *ENCRYPTED_FIELDS])
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT {select_fields} FROM {table_name}")
            raw_rows = cursor.fetchall()

        for row in raw_rows:
            pk_value = row[0]
            raw_map = dict(zip(ENCRYPTED_FIELDS, row[1:]))
            update_fields = [
                field_name
                for field_name, raw_value in raw_map.items()
                if isinstance(raw_value, str) and raw_value and not raw_value.startswith(ENCRYPTED_VALUE_PREFIX)
            ]
            if not update_fields:
                continue
            updates += 1
            if dry_run:
                continue
            instance = queryset.model.objects.get(pk=pk_value)
            for field_name in update_fields:
                setattr(instance, field_name, getattr(instance, field_name))
            instance.save(update_fields=update_fields)
        return updates
