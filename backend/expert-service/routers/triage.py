from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.expert_orchestrator import ExpertOrchestrator
from services.loader import load_knowledge_base


router = APIRouter(prefix="/expert", tags=["expert"])
expert_orchestrator = ExpertOrchestrator()


class ExpertRequest(BaseModel):
    message: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    case_id: str | None = None


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "scaffold",
        "service": "expert-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/evaluate")
async def evaluate(payload: ExpertRequest) -> dict[str, Any]:
    decision = expert_orchestrator.evaluate(
        user_message=payload.message,
        prior_expert_state=payload.context.get("expert_state"),
    )
    return {
        "action": decision.action,
        "response": decision.response,
        "case_id": decision.case_id,
        "confidence": decision.confidence,
        "rule_ids_applied": decision.rule_ids_applied,
        "fallback_reason": decision.fallback_reason,
        "emergency_triggered": decision.emergency_triggered,
        "triage_level": decision.triage_level,
        "pain_scale": decision.pain_scale,
        "symptoms": decision.symptoms,
        "state": {
            "active_case_id": decision.state.active_case_id,
            "active_node_id": decision.state.active_node_id,
            "required_fields_status": decision.state.required_fields_status,
            "confidence": decision.state.confidence,
            "last_rule_ids": decision.state.last_rule_ids,
            "fallback_reason": decision.state.fallback_reason,
            "emergency_triggered": decision.state.emergency_triggered,
            "collected_fields": decision.state.collected_fields,
            "triage_level": decision.state.triage_level,
        },
    }


@router.post("/emergency-check")
async def emergency_check(payload: ExpertRequest) -> dict[str, Any]:
    decision = expert_orchestrator.evaluate(
        user_message=payload.message,
        prior_expert_state=payload.context.get("expert_state"),
    )
    return {
        "is_emergency": bool(decision.emergency_triggered),
        "matched_rules": decision.rule_ids_applied if decision.emergency_triggered else [],
        "message": payload.message,
    }


@router.get("/cases")
async def list_cases() -> dict[str, Any]:
    kb = load_knowledge_base()
    return {
        "cases": sorted(kb.get("cases", {}).keys()),
    }
