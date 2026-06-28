from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from services.bedrock_claude import build_turn_prompt, call_claude
from services.closure_intent import classify_closure_message
from services.comprehend_medical import detect_entities
from services.context_manager import init_context
from services.conversation_context_service import ConversationContextService
from services.embeddings import build_embedding_payload
from services.input_validate import MessageAnalysis, analyze_message, generate_response
from services.medical_facts import FactsSummary, MedicalFact
from services.pain_utils import extract_pain_scale
from services.retrieval_router import RetrievalRouter
from services.triaje_classification import TriageClassification

try:
    from models.conversation import ConversationalDatasetManager
except Exception:  # pragma: no cover
    ConversationalDatasetManager = None


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
        self.dataset_manager = None
        if self.user_id and self.conversation_id:
            try:
                self.context_service = ConversationContextService()
            except Exception as exc:
                logger.warning("Conversation context service unavailable: %s", exc)
        if ConversationalDatasetManager is not None:
            try:
                self.dataset_manager = ConversationalDatasetManager()
            except Exception as exc:
                logger.warning("Conversation dataset manager unavailable: %s", exc)
        self.existing_context = self._load_existing_context(existing_context or {})

    def initialize_conversation(self):
        try:
            awaiting_closure = self._is_awaiting_closure_confirmation()
            if awaiting_closure:
                closure_result = classify_closure_message(self.user_input, existing_context=self.existing_context)
                if closure_result.intent == "closure":
                    if self._should_skip_duplicate_etl(closure_result.facts_summary):
                        response = "Ya registré este mismo contexto clínico. No vuelvo a lanzar la ETL salvo que añadas información nueva o abras otro episodio."
                        conversation_state = self._build_conversation_state(
                            next_intent="etl_skipped_same_context",
                            awaiting_closure_confirmation=False,
                            should_trigger_etl=False,
                            etl_reason="same_context_already_processed",
                            closure_classifier=closure_result.model_dump(),
                        )
                        logger.info(
                            "etl_skipped_same_context conversation_id=%s user_id=%s",
                            self.conversation_id,
                            self.user_id,
                        )
                        result = self._build_non_clinical_response(
                            analyze_message(self.user_input),
                            response_override=response,
                            conversation_state_override=conversation_state,
                        )
                        self._persist_conversation_turn(
                            response_text=response,
                            conversation_state=conversation_state,
                            facts_summary=closure_result.facts_summary,
                            analysis=analyze_message(self.user_input),
                            symptoms=[],
                            symptoms_pattern={},
                            pain_scale=0,
                            triaje_level=self.existing_context.get("last_triaje_level") or "info",
                        )
                        return result
                    response = "Perfecto. Cierro esta consulta y preparo el resumen clínico para lanzar la ETL."
                    final_chat_summary = self._build_final_chat_summary(closure_result.facts_summary)
                    conversation_state = self._build_conversation_state(
                        next_intent="trigger_etl",
                        awaiting_closure_confirmation=False,
                        should_trigger_etl=True,
                        etl_reason="closure_confirmed",
                        closure_classifier=closure_result.model_dump(),
                    )
                    result = self._build_non_clinical_response(
                        analyze_message(self.user_input),
                        response_override=response,
                        conversation_state_override=conversation_state,
                    )
                    result["final_chat_summary"] = final_chat_summary
                    result["final_chat_summary_title"] = "Resumen de esta consulta"
                    self._persist_conversation_turn(
                        response_text=response,
                        conversation_state=conversation_state,
                        facts_summary=closure_result.facts_summary,
                        analysis=analyze_message(self.user_input),
                        symptoms=[],
                        symptoms_pattern={},
                        pain_scale=0,
                        triaje_level=self.existing_context.get("last_triaje_level") or "info",
                        final_chat_summary=final_chat_summary,
                    )
                    return result
                if closure_result.intent == "uncertain":
                    response = (
                        "Si quieres terminar esta consulta y generar el resumen clínico, responde 'ok gracias'. "
                        "Si tienes otro síntoma o dato nuevo, escríbelo ahora."
                    )
                    conversation_state = self._build_conversation_state(
                        next_intent="await_closure_confirmation",
                        awaiting_closure_confirmation=True,
                        should_trigger_etl=False,
                        closure_classifier=closure_result.model_dump(),
                    )
                    result = self._build_non_clinical_response(
                        analyze_message(self.user_input),
                        response_override=response,
                        conversation_state_override=conversation_state,
                    )
                    self._persist_conversation_turn(
                        response_text=response,
                        conversation_state=conversation_state,
                        facts_summary=closure_result.facts_summary,
                        analysis=analyze_message(self.user_input),
                        symptoms=[],
                        symptoms_pattern={},
                        pain_scale=0,
                        triaje_level=self.existing_context.get("last_triaje_level") or "info",
                    )
                    return result

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
            retrieval_decision = RetrievalRouter.decide(
                clinical_signal_score=analysis.clinical_signal_score,
                facts_summary=facts_summary,
                triage_level=triage.triage_level,
                analysis_type=analysis.analysis_type,
                existing_context=self.existing_context,
            )
            real_facts = [MedicalFact(**fact) if isinstance(fact, dict) else fact for fact in structured_facts]
            embedding_payload = build_embedding_payload(self.user_input, real_facts, analysis, facts_summary)

            questions_selected = []
            prompt_context = self._build_minimal_prompt_context(
                facts_summary=facts_summary,
                triage=triage,
                questions_selected=questions_selected,
                retrieval_decision=retrieval_decision,
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

            offer_closure_prompt = self._should_offer_closure_confirmation(analysis, facts_summary, triage)
            if offer_closure_prompt:
                self.response = (
                    f"{self.response}\n\n"
                    "Si no tienes más síntomas o datos que añadir, responde 'ok gracias' y cierro la consulta para lanzar la ETL."
                )

            conversation_state = self._build_conversation_state(
                next_intent="await_closure_confirmation" if offer_closure_prompt else (
                    "triage_recommendation" if triage.triage_level == "Severo" else "collect_missing_data"
                ),
                awaiting_closure_confirmation=offer_closure_prompt,
                should_trigger_etl=False,
            )

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
                            "patient_id": self.postgres_context.get("patient_id"),
                            "clinical_topic": self._infer_clinical_topic(facts_summary),
                        },
                        facts=real_facts,
                        facts_summary=facts_summary,
                        analysis=analysis,
                    )
                except Exception as exc:
                    logger.warning("Could not persist conversational context: %s", exc)

            self._persist_conversation_turn(
                response_text=self.response,
                conversation_state=conversation_state,
                facts_summary=facts_summary,
                analysis=analysis,
                symptoms=symptoms,
                symptoms_pattern=TriageClassification.analyze_symptom_pattern(symptoms),
                pain_scale=pain_level,
                triaje_level=triage.triage_level,
            )

            return {
                "context": self.context,
                "conversation_id": self.conversation_id,
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
                "retrieval": retrieval_decision.model_dump(),
                "embedding_payload": embedding_payload.model_dump(),
                "conversation_state": conversation_state,
            }
        except Exception as exc:
            logger.error("Error en la inicialización del chatbot: %s", exc)
            return {"error": "Ocurrió un problema al procesar la solicitud."}

    def _build_non_clinical_response(
        self,
        analysis: MessageAnalysis,
        facts_summary: FactsSummary | None = None,
        response_override: str | None = None,
        conversation_state_override: dict[str, Any] | None = None,
    ):
        return {
            "context": self.user_data or {},
            "conversation_id": self.conversation_id,
            "triaje_level": "info",
            "entities": [],
            "structured_facts": {
                "facts": [],
                "facts_summary": (facts_summary or FactsSummary()).model_dump(),
                "discarded_segments": [self.user_input] if analysis.analysis_type != "greeting" else [],
            },
            "facts_summary": (facts_summary or FactsSummary()).model_dump(),
            "response": response_override or generate_response(self.user_input),
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
            "conversation_state": conversation_state_override
            or self._build_conversation_state(
                next_intent="collect_initial_symptoms",
                awaiting_closure_confirmation=False,
                should_trigger_etl=False,
            ),
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

    def _infer_clinical_topic(self, facts_summary: FactsSummary) -> str | None:
        red_flags = {item.lower() for item in facts_summary.red_flags}
        symptoms = {item.lower() for item in (facts_summary.chief_complaints + facts_summary.symptoms)}
        if any("pecho" in item or "disnea" in item for item in red_flags | symptoms):
            return "cardiology"
        if any("cabeza" in item or "mareo" in item for item in symptoms):
            return "neurology"
        if facts_summary.history:
            return "chronic_history"
        return None

    def _build_minimal_prompt_context(self, *, facts_summary: FactsSummary, triage, questions_selected: list[str], retrieval_decision):
        prompt_context = {
            **self.context,
            "user_input": self.user_input,
            "postgres_context": self.postgres_context,
            "facts_summary": facts_summary.model_dump(),
            "questions_selected": questions_selected[:2],
            "triage_level": triage.triage_level,
            "retrieval_level": retrieval_decision.level,
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
                    retrieval_level=retrieval_decision.level,
                    episodic_top_k=retrieval_decision.episodic_top_k,
                    global_top_k=retrieval_decision.global_top_k,
                )
            )
        return prompt_context

    def _load_existing_context(self, client_context: dict[str, Any]) -> dict[str, Any]:
        merged = dict(client_context or {})
        if not self.dataset_manager or not self.user_id or not self.conversation_id:
            return merged
        try:
            conversation = self.dataset_manager.get_conversation(self.user_id, self.conversation_id)
        except Exception as exc:
            logger.warning("Could not load conversation state for %s: %s", self.conversation_id, exc)
            return merged
        if not isinstance(conversation, dict):
            return merged
        stored_context = conversation.get("medical_context", {})
        if isinstance(stored_context, dict):
            merged = {**stored_context, **merged}
        return merged

    def _is_awaiting_closure_confirmation(self) -> bool:
        state = self.existing_context.get("conversation_state", {})
        if isinstance(state, dict) and state.get("awaiting_closure_confirmation") is True:
            return True
        return bool(self.existing_context.get("awaiting_closure_confirmation"))

    def _current_case_signature(self, facts_summary: FactsSummary | None = None) -> str:
        summary = facts_summary.model_dump() if facts_summary is not None else self.existing_context.get("facts_summary", {})
        if not isinstance(summary, dict):
            summary = {}
        normalized = {
            "chief_complaints": summary.get("chief_complaints") or [],
            "symptoms": summary.get("symptoms") or [],
            "red_flags": summary.get("red_flags") or [],
            "body_sites": summary.get("body_sites") or [],
            "history": summary.get("history") or [],
            "medications": summary.get("medications") or [],
            "allergies": summary.get("allergies") or [],
            "duration": summary.get("duration") or "",
            "pain_scale": summary.get("pain_scale"),
            "functional_impact": summary.get("functional_impact") or "",
            "severity_terms": summary.get("severity_terms") or [],
        }
        payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _should_skip_duplicate_etl(self, facts_summary: FactsSummary) -> bool:
        hybrid_state = self.existing_context.get("hybrid_state", {})
        if not isinstance(hybrid_state, dict):
            return False
        etl_state = hybrid_state.get("etl", {})
        if not isinstance(etl_state, dict):
            return False
        if str(etl_state.get("last_status") or "").lower() not in {"queued", "running", "success"}:
            return False
        current_state = self.existing_context.get("conversation_state", {})
        previous_signature = str(current_state.get("current_case_signature") or "") if isinstance(current_state, dict) else ""
        current_signature = self._current_case_signature(facts_summary)
        return bool(previous_signature) and previous_signature == current_signature

    def _should_offer_closure_confirmation(self, analysis: MessageAnalysis, facts_summary: FactsSummary, triage) -> bool:
        if triage.triage_level == "Severo":
            return False
        if analysis.analysis_type != "clinical":
            return False
        has_case = bool(
            facts_summary.chief_complaints
            or facts_summary.symptoms
            or self.existing_context.get("chief_complaint")
        )
        has_supporting_context = bool(
            facts_summary.duration
            or facts_summary.red_flags
            or facts_summary.body_sites
            or facts_summary.functional_impact
            or facts_summary.pain_scale is not None
            or self.existing_context.get("symptom_duration")
            or self.existing_context.get("pain_level_reported") is not None
        )
        return has_case and has_supporting_context

    def _build_conversation_state(
        self,
        *,
        next_intent: str,
        awaiting_closure_confirmation: bool,
        should_trigger_etl: bool,
        etl_reason: str | None = None,
        closure_classifier: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = {
            "missing_fields": [],
            "collected_fields": [k for k, v in self.context.items() if v not in (None, "", [], {})],
            "next_intent": next_intent,
            "loop_guard_triggered": False,
            "questions_selected": [],
            "max_questions_per_turn": self.max_questions_per_turn,
            "awaiting_closure_confirmation": awaiting_closure_confirmation,
            "should_trigger_etl": should_trigger_etl,
            "current_case_signature": self._current_case_signature(),
        }
        if etl_reason:
            state["etl_reason"] = etl_reason
        if closure_classifier:
            state["closure_classifier"] = closure_classifier
        return state

    def _persist_conversation_turn(
        self,
        *,
        response_text: str,
        conversation_state: dict[str, Any],
        facts_summary: FactsSummary,
        analysis: MessageAnalysis,
        symptoms: list[str],
        symptoms_pattern,
        pain_scale: int,
        triaje_level: str,
        final_chat_summary: str | None = None,
    ) -> None:
        if not self.dataset_manager or not self.user_id:
            return
        messages = [{"role": "user", "content": self.user_input}, {"role": "assistant", "content": response_text}]
        if final_chat_summary:
            messages.append({"role": "assistant", "content": f"Resumen de esta consulta\n\n{final_chat_summary}"})
        medical_context = {
            **(self.existing_context or {}),
            **(self.context or {}),
            "facts_summary": facts_summary.model_dump(),
            "conversation_state": conversation_state,
            "awaiting_closure_confirmation": conversation_state.get("awaiting_closure_confirmation", False),
            "last_analysis_type": analysis.analysis_type,
            "last_triaje_level": triaje_level,
        }
        if final_chat_summary:
            medical_context["final_chat_summary"] = final_chat_summary
        try:
            if self.conversation_id:
                current = self.dataset_manager.get_conversation(self.user_id, self.conversation_id) or {}
                if not current:
                    self.conversation_id = self.dataset_manager.add_conversation(
                        self.user_id,
                        medical_context,
                        messages,
                        symptoms,
                        symptoms_pattern,
                        pain_scale,
                        triaje_level,
                        conversation_id=self.conversation_id,
                    )
                    return
                current_messages = current.get("messages", []) if isinstance(current, dict) else []
                if not isinstance(current_messages, list):
                    current_messages = []
                merged_messages = current_messages + messages
                self.dataset_manager.update_conversation(
                    self.user_id,
                    self.conversation_id,
                    messages=merged_messages,
                    symptoms=symptoms,
                    symptoms_pattern=symptoms_pattern,
                    pain_scale=pain_scale,
                    triaje_level=triaje_level,
                    medical_context={**(current.get("medical_context", {}) if isinstance(current, dict) else {}), **medical_context},
                )
            else:
                self.conversation_id = self.dataset_manager.add_conversation(
                    self.user_id,
                    medical_context,
                    messages,
                    symptoms,
                    symptoms_pattern,
                    pain_scale,
                    triaje_level,
                    conversation_id=self.conversation_id,
                )
        except Exception as exc:
            logger.warning("Could not persist conversation %s: %s", self.conversation_id, exc)

    def _build_final_chat_summary(self, latest_facts_summary: FactsSummary | None = None) -> str:
        base_summary = latest_facts_summary or FactsSummary(**((self.existing_context or {}).get("facts_summary", {}) or {}))
        if not any(
            [
                base_summary.chief_complaints,
                base_summary.symptoms,
                base_summary.duration,
                base_summary.red_flags,
                base_summary.pain_scale is not None,
                base_summary.medications,
                base_summary.allergies,
                base_summary.history,
            ]
        ):
            return "No se detectaron suficientes datos clínicos estructurados para resumir esta consulta."

        fragments: list[str] = []
        if base_summary.chief_complaints:
            fragments.append("Motivo principal: " + ", ".join(base_summary.chief_complaints[:2]) + ".")
        if base_summary.symptoms:
            fragments.append("Síntomas relevantes: " + ", ".join(base_summary.symptoms[:4]) + ".")
        if base_summary.duration:
            fragments.append("Duración referida: " + base_summary.duration + ".")
        if base_summary.pain_scale is not None:
            fragments.append(f"Dolor referido: {base_summary.pain_scale}/10.")
        if base_summary.red_flags:
            fragments.append("Señales de alerta: " + ", ".join(base_summary.red_flags[:3]) + ".")
        if base_summary.medications:
            fragments.append("Medicación mencionada: " + ", ".join(base_summary.medications[:3]) + ".")
        if base_summary.allergies:
            fragments.append("Alergias mencionadas: " + ", ".join(base_summary.allergies[:3]) + ".")
        if base_summary.history:
            fragments.append("Antecedentes relevantes: " + ", ".join(base_summary.history[:3]) + ".")
        return "\n".join(f"- {fragment}" for fragment in fragments)
