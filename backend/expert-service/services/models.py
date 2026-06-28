from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExpertState:
    active_case_id: Optional[str] = None
    active_node_id: Optional[str] = None
    required_fields_status: Dict[str, bool] = field(default_factory=dict)
    confidence: float = 0.0
    last_rule_ids: List[str] = field(default_factory=list)
    fallback_reason: Optional[str] = None
    emergency_triggered: bool = False
    collected_fields: Dict[str, Any] = field(default_factory=dict)
    triage_level: str = "Leve"


@dataclass
class ExpertDecision:
    action: str
    response: str
    case_id: Optional[str]
    confidence: float
    rule_ids_applied: List[str] = field(default_factory=list)
    fallback_reason: Optional[str] = None
    emergency_triggered: bool = False
    method_trace: List[str] = field(default_factory=lambda: ["rules", "tree", "scoring"])
    triage_level: str = "Leve"
    pain_scale: int = 0
    symptoms: List[str] = field(default_factory=list)
    state: ExpertState = field(default_factory=ExpertState)
