from __future__ import annotations

import logging

from services.bedrock_claude import build_turn_prompt, call_claude
from services.comprehend_medical import detect_entities
from services.context_manager import init_context
from services.conversation_context_service import ConversationContextService
from services.embeddings import build_embedding_payload
from services.input_validate import MessageAnalysis, analyze_message, generate_response
from services.medical_facts import FactsSummary, MedicalFact
from services.pain_utils import extract_pain_scale
from services.triaje_classification import TriageClassification


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLINICAL_SIGNAL_THRESHOLD_EMBED = 0.25
CLINICAL_SIGNAL_THRESHOLD_DEEP_EXTRACT = 0.15


class Chatbot:
    def __init__(
        self,
        user_input,
        user_data,
        initial_prompt=None,
        user_id=None,
        conversation_id=None,
        existing_context=None,
        postgres_context=None,
    ):
        self.user_input = user_input
        self.user_data = user_data or {}
        self.initial_prompt = initial_prompt
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.existing_context = existing_context or {}
        self.postgres_context = postgres_context or {}
        self.context = {}
        self.response = None
        self.max_questions_per_turn = 2
        self.context_service = None
        if self.user_id and self.conversation_id:
            try:
                self.context_service = ConversationContextService()
            except Exception as exc:
                logger.warning("Conversation context service unavailable: %s", exc)

    def initialize_conversation(self):
        try:
            analysis = analyze_message(self.user_input)
            if not analysis.is_valid:
                return {"error": analysis.error_message or "Mensaje inválido o irreconocible."}

            if analysis.analysis_type == "greeting":
                return self._build_non_clinical_response(analysis)

            deep_extract = analysis.clinical_signal_score >= CLINICAL_SIGNAL_THRESHOLD_DEEP_EXTRACT
            extraction = detect_entities(self.user_input, context=self.existing_context if deep_extract else None)
            structured_facts = extraction.get("facts", [])
            facts_summary = FactsSummary(**(extraction.get("facts_summary", {}) or {}))

            if analysis.analysis_type == "non_clinical" and not structured_facts:
                return self._build_non_clinical_response(analysis, facts_summary=facts_summary)

            context_result = init_context(self.user_input, user_data=self.user_data, existing_context=self.existing_context)
            self.context = context_result.get("context", {}) if isinstance(context_result, dict) else {}
            self.context["facts_summary"] = facts_summary.model_dump()
            self.context["medical_entities"] = structured_facts
            symptoms = list(dict.fromkeys(facts_summary.chief_complaints + facts_summary.symptoms))
            pain_level = self._extract_pain_level_from_summary(facts_summary)
            self.context["symptoms"] = symptoms
            self.context["pain_level"] = pain_level

            triage = TriageClassification.from_facts(
                facts_summary,
                existing_context=self.existing_context,
                environment=self.context.get("environment", "general"),
            )
            real_facts = [MedicalFact(**fact) if isinstance(fact, dict) else fact for fact in structured_facts]
            embedding_payload = build_embedding_payload(self.user_input, real_facts, analysis, facts_summary)

            questions_selected = []
            prompt_context = self._build_minimal_prompt_context(
                facts_summary=facts_summary,
                triage=triage,
                questions_selected=questions_selected,
            )
            prompt_metadata = build_turn_prompt(prompt_context, initial_prompt=self.initial_prompt)

            try:
                self.response = call_claude(
                    prompt=prompt_context,
                    triage_level=triage.triage_level,
                    initial_prompt=self.initial_prompt,
                )
            except Exception:
                self.response = generate_response(self.user_input)

            if triage.triage_level == "Severo":
                self.response = triage.handle_severe_case(self.user_input)

            if self.context_service and self.user_id and self.conversation_id:
                try:
                    self.context_service.append_turn(
                        self.user_id,
                        self.conversation_id,
                        self.user_input,
                        self.response,
                        metadata={
                            "triage_level": triage.triage_level,
                            "prompt_sections_used": prompt_metadata["prompt_sections_used"],
                        },
                        facts=real_facts,
                        facts_summary=facts_summary,
                        analysis=analysis,
                    )
                except Exception as exc:
                    logger.warning("Could not persist conversational context: %s", exc)

            return {
                "context": self.context,
                "triaje_level": triage.triage_level,
                "entities": structured_facts,
                "structured_facts": extraction,
                "facts_summary": facts_summary.model_dump(),
                "response": self.response,
                "symptoms": symptoms,
                "symptoms_pattern": TriageClassification.analyze_symptom_pattern(symptoms),
                "pain_scale": pain_level,
                "missing_questions": [],
                "analysis_type": analysis.analysis_type,
                "triage_reasons": triage.triage_reasons,
                "triage_confidence": triage.triage_confidence,
                "prompt_sections_used": prompt_metadata["prompt_sections_used"],
                "prompt_token_budget": prompt_metadata["prompt_token_budget"],
                "embedding_payload": embedding_payload.model_dump(),
                "conversation_state": {
                    "missing_fields": [],
                    "collected_fields": [k for k, v in self.context.items() if v not in (None, "", [], {})],
                    "next_intent": "triage_recommendation" if triage.triage_level == "Severo" else "collect_missing_data",
                    "loop_guard_triggered": False,
                    "questions_selected": questions_selected,
                    "max_questions_per_turn": self.max_questions_per_turn,
                },
            }
        except Exception as exc:
            logger.error("Error en la inicialización del chatbot: %s", exc)
            return {"error": "Ocurrió un problema al procesar la solicitud."}

    def _build_non_clinical_response(self, analysis: MessageAnalysis, facts_summary: FactsSummary | None = None):
        return {
            "context": self.user_data or {},
            "triaje_level": "info",
            "entities": [],
            "structured_facts": {
                "facts": [],
                "facts_summary": (facts_summary or FactsSummary()).model_dump(),
                "discarded_segments": [self.user_input] if analysis.analysis_type != "greeting" else [],
            },
            "facts_summary": (facts_summary or FactsSummary()).model_dump(),
            "response": generate_response(self.user_input),
            "symptoms": [],
            "symptoms_pattern": {},
            "pain_scale": 0,
            "missing_questions": [],
            "analysis_type": analysis.analysis_type,
            "triage_reasons": [],
            "triage_confidence": 0.0,
            "prompt_sections_used": [],
            "prompt_token_budget": {
                "target_max_input_tokens": 1200,
                "used_estimate": 0,
            },
            "embedding_payload": {
                "skipped": True,
                "reason": "low_clinical_signal",
                "signal_score": analysis.clinical_signal_score,
                "embedding_target": "clinical_hybrid",
                "embedding_text": "",
                "facts_used": [],
            },
            "conversation_state": {
                "missing_fields": [],
                "collected_fields": list((self.user_data or {}).keys()),
                "next_intent": "collect_initial_symptoms",
                "loop_guard_triggered": False,
                "questions_selected": [],
                "max_questions_per_turn": self.max_questions_per_turn,
            },
        }

    def _extract_pain_level_from_summary(self, facts_summary: FactsSummary) -> int:
        if facts_summary.pain_scale is not None:
            return int(facts_summary.pain_scale)
        explicit = extract_pain_scale(self.user_input)
        if explicit is not None:
            return explicit
        previous_candidates = [
            self.existing_context.get("pain_level_reported"),
            self.existing_context.get("pain_level"),
            self.existing_context.get("pain_scale"),
        ]
        for value in previous_candidates:
            if isinstance(value, int) and 0 <= value <= 10:
                return value
        return 0

    def _build_minimal_prompt_context(self, *, facts_summary: FactsSummary, triage, questions_selected: list[str]):
        prompt_context = {
            **self.context,
            "user_input": self.user_input,
            "postgres_context": self.postgres_context,
            "facts_summary": facts_summary.model_dump(),
            "questions_selected": questions_selected[:2],
            "triage_level": triage.triage_level,
        }
        if self.context_service and self.user_id and self.conversation_id:
            prompt_context.update(
                self.context_service.build_prompt_context(
                    user_id=self.user_id,
                    conversation_id=self.conversation_id,
                    user_input=self.user_input,
                    current_context=self.context,
                    missing_questions=[],
                    questions_selected=questions_selected,
                    postgres_context=self.postgres_context,
                    triage_level=triage.triage_level,
                    facts_summary=facts_summary,
                )
            )
        return prompt_context
