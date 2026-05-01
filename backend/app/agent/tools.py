"""LangGraph tool implementations for sales / HCP CRM workflows."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from app.schemas.interaction import InteractionDraft
from app.services.interaction_db import create_interaction, update_interaction


def _trace(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"tool": name, "payload": payload}


@tool
def log_interaction(
    rep_id: str,
    draft_json: str,
    chat_transcript_json: str = "[]",
) -> str:
    """Persist a finalized HCP interaction. draft_json is InteractionDraft as JSON string."""
    draft = InteractionDraft.model_validate_json(draft_json)
    transcript = json.loads(chat_transcript_json) if chat_transcript_json else []
    result = create_interaction(rep_id=rep_id, draft=draft, chat_transcript=transcript)
    return json.dumps(result)


@tool
def edit_interaction(
    interaction_id: str,
    draft_json: str,
    reason: str,
    patch_json: str = "{}",
) -> str:
    """Apply an audited edit to a logged interaction; stores revision metadata."""
    draft = InteractionDraft.model_validate_json(draft_json)
    patch = json.loads(patch_json) if patch_json else {}
    result = update_interaction(interaction_id, draft, reason=reason, patch=patch)
    return json.dumps(result)


@tool
def fetch_hcp_context(hcp_id: str) -> str:
    """Return territory-aware HCP profile context for grounding extraction."""
    demo = {
        "hcp_id": hcp_id,
        "tier": "high",
        "specialty": "Medical Oncology",
        "institution": "Metro Cancer Center",
        "last_topics": ["OncoBoost Phase III", "adverse events profile"],
    }
    return json.dumps(demo)


@tool
def validate_materials_and_samples(material_names: str, sample_skus: str) -> str:
    """Resolve free-text material/sample mentions against an approved catalog (stub)."""
    catalog_materials = {"OncoBoost Phase III PDF": "MAT-ONC-003", "OncoBoost brochure": "MAT-ONC-001"}
    catalog_samples = {"OncoBoost sample kit": "SKU-ONC-900"}
    mats = [m.strip() for m in material_names.split(",") if m.strip()]
    skus = [s.strip() for s in sample_skus.split(",") if s.strip()]
    resolved_m = [{ "name": m, "catalog_id": catalog_materials.get(m, "UNRESOLVED")} for m in mats]
    resolved_s = [{ "name": s, "sku": catalog_samples.get(s, "UNRESOLVED")} for s in skus]
    return json.dumps({"materials": resolved_m, "samples": resolved_s})


@tool
def compliance_guard(interaction_text: str) -> str:
    """Flag potential compliance issues (off-label, missing consent markers, etc.)."""
    text = interaction_text.lower()
    flags: list[str] = []
    if "off-label" in text or "off label" in text:
        flags.append("possible_off_label_language")
    if "guaranteed cure" in text or "100% effective" in text:
        flags.append("unsubstantiated_efficacy_claim")
    if "voice" in text and "consent" not in text:
        flags.append("voice_note_consent_not_recorded")
    return json.dumps({"blocked": len(flags) >= 2, "flags": flags})


@tool
def plan_follow_ups(summary: str) -> str:
    """Generate structured follow-up tasks from an interaction summary."""
    suggestions = [
        "Schedule follow-up meeting in 2 weeks",
        "Send approved efficacy one-pager (latest version)",
        "Confirm sample delivery and capture acknowledgement",
    ]
    if "advisory" in summary.lower():
        suggestions.append("Add HCP to advisory board invite list (pending approval)")
    return json.dumps({"suggestions": suggestions})


@tool
def sync_calendar_tasks(interaction_id: str, tasks_json: str) -> str:
    """Push approved tasks to calendar/task backend (stub integration)."""
    tasks = json.loads(tasks_json) if tasks_json else []
    return json.dumps({"interaction_id": interaction_id, "synced": len(tasks), "provider": "stub"})


TOOLS = [
    log_interaction,
    edit_interaction,
    fetch_hcp_context,
    validate_materials_and_samples,
    compliance_guard,
    plan_follow_ups,
    sync_calendar_tasks,
]


def append_trace(state_trace: list[dict], name: str, payload: dict[str, Any]) -> None:
    state_trace.append(_trace(name, payload))
