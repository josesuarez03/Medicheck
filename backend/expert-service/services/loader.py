import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def _rules_root() -> Path:
    return Path(__file__).resolve().parents[1] / "rules"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None or not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=1)
def load_knowledge_base() -> Dict[str, Any]:
    rules_root = _rules_root()
    cases_root = rules_root / "cases"
    shared_root = rules_root / "shared"

    cases: Dict[str, Any] = {}
    if cases_root.exists():
        for full_path in sorted(cases_root.iterdir()):
            if full_path.suffix not in {".json", ".yaml", ".yml"}:
                continue
            case_def = _load_json(full_path) if full_path.suffix == ".json" else _load_yaml(full_path)
            case_id = case_def.get("case_id")
            if case_id:
                cases[str(case_id)] = case_def

    emergency = _load_json(shared_root / "emergency.json")
    triage_policy = _load_json(shared_root / "triage_policy.json")
    if not emergency:
        emergency = _load_yaml(shared_root / "emergency.yaml")
    if not triage_policy:
        triage_policy = _load_yaml(shared_root / "triage_policy.yaml")
    return {
        "cases": cases,
        "emergency": emergency,
        "triage_policy": triage_policy,
    }
