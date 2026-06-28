from typing import Any, Dict, Optional

from services.emergency_guard import build_emergency_message, detect_emergency
from services.loader import load_knowledge_base
from services.models import ExpertDecision, ExpertState
from services.rule_engine import classify_triage_level, detect_best_case, extract_case_fields, infer_pain_level
from services.scoring_engine import detect_case_conflict, evaluate_confidence
from services.tree_engine import build_advice, compute_required_fields_status, select_next_node


class ExpertOrchestrator:
    def __init__(self) -> None:
        kb = load_knowledge_base()
        self.cases = kb.get("cases", {})
        self.emergency_rules = kb.get("emergency", {})
        self.triage_policy = kb.get("triage_policy", {})

    def evaluate(
        self,
        *,
        user_message: str,
        prior_expert_state: Optional[Dict[str, Any]] = None,
    ) -> ExpertDecision:
        prior_state = prior_expert_state or {}
        previous_case_id = prior_state.get("active_case_id")
        previous_fields = prior_state.get("collected_fields", {})
        previous_pain = prior_state.get("pain_scale", 0)
        previous_node_id = prior_state.get("active_node_id")

        case_id, intent_score, second_score = detect_best_case(
            user_message=user_message,
            cases=self.cases,
            active_case_id=previous_case_id,
        )
        case_conflict = detect_case_conflict(
            best_score=float(intent_score),
            second_score=float(second_score),
            conflict_delta=float(self.triage_policy.get("case_conflict_delta", 0.1)),
        )

        emergency_triggered, emergency_rules, is_psych = detect_emergency(
            user_message_lower=(user_message or "").lower(),
            emergency_rules=self.emergency_rules,
            case_id=case_id,
        )
        if emergency_triggered:
            state = ExpertState(
                active_case_id=case_id,
                confidence=1.0,
                last_rule_ids=emergency_rules,
                emergency_triggered=True,
                collected_fields=previous_fields,
                triage_level="Severo",
            )
            return ExpertDecision(
                action="escalate",
                response=build_emergency_message(self.emergency_rules, psychological=is_psych),
                case_id=case_id,
                confidence=1.0,
                rule_ids_applied=emergency_rules,
                emergency_triggered=True,
                triage_level="Severo",
                pain_scale=infer_pain_level(user_message, previous_value=previous_pain),
                state=state,
            )

        if not case_id or case_id not in self.cases or case_conflict:
            fallback_reason = "case_conflict" if case_conflict else "no_case_match"
            state = ExpertState(
                active_case_id=case_id,
                confidence=0.0,
                last_rule_ids=["fallback_rule_no_case_match"],
                fallback_reason=fallback_reason,
                collected_fields=previous_fields,
                triage_level=self.triage_policy.get("default_triage", "Leve"),
            )
            return ExpertDecision(
                action="fallback_ai",
                response="",
                case_id=case_id,
                confidence=0.0,
                rule_ids_applied=["fallback_rule_no_case_match"],
                fallback_reason=fallback_reason,
                triage_level=state.triage_level,
                pain_scale=infer_pain_level(user_message, previous_value=previous_pain),
                state=state,
            )

        case_def = self.cases[case_id]
        expected_field = None
        if previous_node_id:
            for node in case_def.get("tree", []):
                if node.get("id") == previous_node_id:
                    expected_field = node.get("field")
                    break
        collected_fields = extract_case_fields(
            case_def=case_def,
            user_message=user_message,
            previous_fields=previous_fields,
            expected_field=expected_field,
        )
        pain_scale = infer_pain_level(user_message, previous_value=previous_pain)
        triage_level = classify_triage_level(case_id, pain_scale, user_message, self.triage_policy)
        required_fields_status = compute_required_fields_status(case_def, collected_fields)
        confidence, confidence_ok = evaluate_confidence(
            intent_score=float(intent_score),
            required_fields_status=required_fields_status,
            threshold=float(self.triage_policy.get("confidence_threshold", 0.65)),
        )

        min_intent_for_tree = float(self.triage_policy.get("min_intent_for_tree", 0.25))
        continuing_same_case = bool(previous_case_id and previous_case_id == case_id)
        should_fallback = (not confidence_ok) and (float(intent_score) < min_intent_for_tree) and (not continuing_same_case)
        if should_fallback:
            state = ExpertState(
                active_case_id=case_id,
                required_fields_status=required_fields_status,
                confidence=confidence,
                last_rule_ids=["fallback_rule_low_confidence"],
                fallback_reason="low_confidence",
                collected_fields=collected_fields,
                triage_level=triage_level,
            )
            return ExpertDecision(
                action="fallback_ai",
                response="",
                case_id=case_id,
                confidence=confidence,
                rule_ids_applied=["fallback_rule_low_confidence"],
                fallback_reason="low_confidence",
                triage_level=triage_level,
                pain_scale=pain_scale,
                symptoms=case_def.get("intent_keywords", []),
                state=state,
            )

        next_node = select_next_node(case_def, required_fields_status)
        if next_node:
            response = next_node.get("question", "Para continuar, dame un poco más de información.")
            active_node_id = next_node.get("id")
            action = "ask"
            rule_ids = [str(next_node.get("rule_id", "tree_question_rule"))]
        else:
            response = build_advice(case_def, triage_level)
            active_node_id = None
            action = "advise"
            rule_ids = [f"advice_{triage_level.lower()}"]

        state = ExpertState(
            active_case_id=case_id,
            active_node_id=active_node_id,
            required_fields_status=required_fields_status,
            confidence=confidence,
            last_rule_ids=rule_ids,
            collected_fields=collected_fields,
            triage_level=triage_level,
        )
        return ExpertDecision(
            action=action,
            response=response,
            case_id=case_id,
            confidence=confidence,
            rule_ids_applied=rule_ids,
            triage_level=triage_level,
            pain_scale=pain_scale,
            symptoms=case_def.get("intent_keywords", []),
            state=state,
        )
