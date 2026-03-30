from django.core.management.base import BaseCommand

from users.models import Patient, PatientClinicalSummary
from users.utils.ai_service_sync import push_clinical_summary_to_ai


class Command(BaseCommand):
    help = "Recalcula PatientClinicalSummary y opcionalmente sincroniza user_summary_embeddings en ai-service."

    def add_arguments(self, parser):
        parser.add_argument("--user-id", dest="user_id")
        parser.add_argument("--push-ai", action="store_true", dest="push_ai")

    def handle(self, *args, **options):
        queryset = Patient.objects.select_related("user").all()
        if options.get("user_id"):
            queryset = queryset.filter(user_id=options["user_id"])

        processed = 0
        pushed = 0
        for patient in queryset.iterator():
            summary, _created = PatientClinicalSummary.objects.get_or_create(patient=patient)
            triage_history = list(
                patient.history_entries.exclude(triaje_level__isnull=True).exclude(triaje_level="").values_list("triaje_level", flat=True)[:5]
            )
            summary.sync_from_patient(triage_history=triage_history, episode_snapshot=summary.active_episode_snapshot, clinical_flags=summary.clinical_flags)
            processed += 1
            if options.get("push_ai") and push_clinical_summary_to_ai(summary):
                pushed += 1

        self.stdout.write(self.style.SUCCESS(f"PatientClinicalSummary procesados: {processed}"))
        if options.get("push_ai"):
            self.stdout.write(self.style.SUCCESS(f"PatientClinicalSummary sincronizados con ai-service: {pushed}"))
