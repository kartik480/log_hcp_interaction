from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.agent.graph import run_parse_graph
from app.agent.workflows import run_edit_graph, run_log_graph
from app.schemas.interaction import (
    ChatMessage,
    EditInteractionRequest,
    EditInteractionResponse,
    InteractionDraft,
    LogInteractionRequest,
    LogInteractionResponse,
    ParseChatRequest,
    ParseChatResponse,
    FieldConfidence,
)
from app.services.interaction_db import get_interaction_draft

router = APIRouter(prefix="/interactions", tags=["interactions"])


def _merge_draft(base: InteractionDraft, patch: dict[str, Any]) -> InteractionDraft:
    data = base.model_dump(mode="json")
    for key, val in patch.items():
        if key in {"materials", "samples", "attendees", "ai_suggested_follow_ups"} and val is not None:
            data[key] = val
        elif val is not None:
            data[key] = val
    return InteractionDraft.model_validate(data)


@router.post("/parse-chat", response_model=ParseChatResponse)
def parse_chat(body: ParseChatRequest) -> ParseChatResponse:
    last_user = next((m.content for m in reversed(body.messages) if m.role == "user"), "")
    draft = body.draft or InteractionDraft()
    out = run_parse_graph(last_user, draft.model_dump(mode="json"))
    patch = out.get("extracted_patch") or {}
    merged = _merge_draft(draft, patch)
    merged_dict = merged.model_dump(mode="json")
    if out.get("follow_up_suggestions"):
        merged_dict["ai_suggested_follow_ups"] = list(
            dict.fromkeys((merged.ai_suggested_follow_ups or []) + out["follow_up_suggestions"])
        )
    trace = list(out.get("tool_trace") or [])
    conf = [FieldConfidence(**c) for c in (out.get("confidence") or []) if c.get("field")]
    return ParseChatResponse(
        draft_patch=merged_dict,
        assistant_message=out.get("assistant_reply") or "",
        follow_up_suggestions=out.get("follow_up_suggestions") or [],
        confidence=conf,
        compliance_flags=out.get("compliance_flags") or [],
        tool_trace=trace,
        run_id=out.get("run_id") or "",
    )


@router.post("/log", response_model=LogInteractionResponse)
def log_interaction_endpoint(body: LogInteractionRequest) -> LogInteractionResponse:
    transcript = [m.model_dump() for m in (body.chat_transcript or [])]
    out = run_log_graph(
        rep_id=body.rep_id,
        draft=body.draft.model_dump(mode="json"),
        chat_transcript=transcript,
    )
    trace = list(out.get("tool_trace") or [])
    return LogInteractionResponse(
        interaction_id=out["interaction_id"],
        summary=out.get("summary") or body.draft.summary or body.draft.topics_discussed[:500],
        tool_trace=trace,
    )


@router.patch("/{interaction_id}", response_model=EditInteractionResponse)
def edit_interaction_endpoint(interaction_id: str, body: EditInteractionRequest) -> EditInteractionResponse:
    draft = get_interaction_draft(interaction_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Interaction not found")
    patch: dict[str, Any] = body.draft_patch or {}
    if body.natural_language_edit and not patch:
        patch = {"topics_discussed": (draft.topics_discussed + "\n" + body.natural_language_edit).strip()}
    new_draft = _merge_draft(draft, patch)
    out = run_edit_graph(
        interaction_id=interaction_id,
        draft=new_draft.model_dump(mode="json"),
        patch=patch,
        reason=body.reason or "edit",
    )
    updated = get_interaction_draft(interaction_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Interaction not found after edit")
    trace = list(out.get("tool_trace") or [])
    return EditInteractionResponse(
        interaction_id=interaction_id,
        revision=int(out["revision"]),
        draft=updated,
        tool_trace=trace,
    )


@router.get("/{interaction_id}", response_model=InteractionDraft)
def get_interaction(interaction_id: str) -> InteractionDraft:
    row = get_interaction_draft(interaction_id)
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return row
