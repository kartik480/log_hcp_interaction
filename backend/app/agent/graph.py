"""LangGraph workflow: extract → compliance → catalog hints → follow-ups → reply."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import httpx
from langgraph.graph import END, StateGraph

from app.agent.state import AgentGraphState
from app.agent.tools import (
    append_trace,
    compliance_guard,
    fetch_hcp_context,
    plan_follow_ups,
    validate_materials_and_samples,
)
from app.config import settings

logger = logging.getLogger(__name__)


SYSTEM_EXTRACT = """You are a life-sciences CRM assistant for field reps logging HCP interactions.
Extract ONLY what is explicitly supported by the user's text. Return strict JSON with keys:
hcp_name (string|null), interaction_type (meeting|call|email|conference|other|null),
occurred_at (ISO8601 string|null if unknown), attendees (string[]),
topics_discussed (string), sentiment (positive|neutral|negative|null),
outcomes (string), follow_up_actions (string), materials_mentioned (string[]), samples_mentioned (string[]),
confidence (object mapping field name to 0..1 float).

Do not invent catalog IDs or SKUs; only capture free-text mentions."""


def _openrouter_model(primary: bool = True) -> str:
    return settings.openrouter_model_primary if primary else settings.openrouter_model_fallback


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    if start == -1:
        raise ValueError("no json in model output")
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(text[start:])
    if not isinstance(obj, dict):
        raise ValueError("model output json is not an object")
    return obj


def _call_openrouter(user_text: str, form_draft: dict, primary: bool) -> str:
    payload = {
        "model": _openrouter_model(primary=primary),
        "messages": [
            {"role": "system", "content": SYSTEM_EXTRACT},
            {
                "role": "user",
                "content": json.dumps(
                    {"user_text": user_text, "existing_form_draft": form_draft},
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("openrouter returned no choices")
        return choices[0]["message"]["content"]


def _invoke_extraction(user_text: str, form_draft: dict) -> dict[str, Any]:
    if not settings.openrouter_api_key:
        return {
            "hcp_name": None,
            "interaction_type": None,
            "occurred_at": None,
            "attendees": [],
            "topics_discussed": user_text,
            "sentiment": None,
            "outcomes": "",
            "follow_up_actions": "",
            "materials_mentioned": [],
            "samples_mentioned": [],
            "confidence": {},
            "_error": "OPENROUTER_API_KEY not set; returning heuristic stub.",
        }
    try:
        text = _call_openrouter(user_text=user_text, form_draft=form_draft, primary=True)
        return _extract_json(text)
    except Exception as first_err:
        logger.warning("Primary OpenRouter extraction failed: %s", first_err)
        try:
            text = _call_openrouter(user_text=user_text, form_draft=form_draft, primary=False)
            return _extract_json(text)
        except Exception as second_err:
            logger.warning("Fallback OpenRouter extraction failed: %s", second_err)
            return {
                "hcp_name": None,
                "interaction_type": None,
                "occurred_at": None,
                "attendees": [],
                "topics_discussed": user_text,
                "sentiment": None,
                "outcomes": "",
                "follow_up_actions": "",
                "materials_mentioned": [],
                "samples_mentioned": [],
                "confidence": {},
                "_error": f"OpenRouter unavailable ({type(second_err).__name__}); applied graceful fallback.",
            }


def node_extract(state: AgentGraphState) -> AgentGraphState:
    trace = list(state.get("tool_trace", []))
    data = _invoke_extraction(state.get("user_text", ""), state.get("form_draft", {}))
    if err := data.pop("_error", None):
        append_trace(trace, "extract_stub", {"note": err})
    patch: dict[str, Any] = {}
    confidence: list[dict] = []
    conf_obj = data.get("confidence") or {}
    if isinstance(conf_obj, dict):
        for k, v in conf_obj.items():
            try:
                confidence.append({"field": k, "score": float(v), "rationale": None})
            except (TypeError, ValueError):
                continue

    if data.get("hcp_name"):
        patch["hcp_name"] = data["hcp_name"]
    if data.get("interaction_type"):
        patch["interaction_type"] = data["interaction_type"]
    if data.get("occurred_at"):
        patch["occurred_at"] = data["occurred_at"]
    if data.get("attendees"):
        patch["attendees"] = data["attendees"]
    if data.get("topics_discussed"):
        patch["topics_discussed"] = data["topics_discussed"]
    if data.get("sentiment"):
        patch["sentiment"] = data["sentiment"]
    if data.get("outcomes") is not None:
        patch["outcomes"] = data["outcomes"]
    if data.get("follow_up_actions") is not None:
        patch["follow_up_actions"] = data["follow_up_actions"]

    mats = data.get("materials_mentioned") or []
    samps = data.get("samples_mentioned") or []
    if mats or samps:
        raw = validate_materials_and_samples.invoke(
            {
                "material_names": ", ".join(mats) if isinstance(mats, list) else str(mats),
                "sample_skus": ", ".join(samps) if isinstance(samps, list) else str(samps),
            }
        )
        append_trace(trace, "validate_materials_and_samples", {"input": {"materials": mats, "samples": samps}})
        resolved = json.loads(raw)
        if resolved.get("materials"):
            patch["materials"] = [
                {
                    "catalog_id": m.get("catalog_id", "UNRESOLVED"),
                    "name": m.get("name", ""),
                    "quantity": 1,
                }
                for m in resolved["materials"]
            ]
        if resolved.get("samples"):
            patch["samples"] = [
                {
                    "sku": s.get("sku", "UNRESOLVED"),
                    "name": s.get("name", ""),
                    "quantity": 1,
                }
                for s in resolved["samples"]
            ]

    return {
        **state,
        "extracted_patch": patch,
        "confidence": confidence,
        "tool_trace": trace,
    }


def node_compliance(state: AgentGraphState) -> AgentGraphState:
    trace = list(state.get("tool_trace", []))
    blob = json.dumps(
        {
            "user_text": state.get("user_text", ""),
            "patch": state.get("extracted_patch", {}),
        },
        ensure_ascii=False,
    )
    raw = compliance_guard.invoke({"interaction_text": blob})
    append_trace(trace, "compliance_guard", {"text_len": len(blob)})
    flags = json.loads(raw).get("flags", [])
    return {**state, "compliance_flags": flags, "tool_trace": trace}


def node_hcp_context(state: AgentGraphState) -> AgentGraphState:
    trace = list(state.get("tool_trace", []))
    draft = state.get("form_draft", {}) or {}
    hcp_id = draft.get("hcp_id") or "demo-hcp"
    raw = fetch_hcp_context.invoke({"hcp_id": str(hcp_id)})
    append_trace(trace, "fetch_hcp_context", {"hcp_id": hcp_id})
    # Context is traced for audit; merge is optional in a fuller implementation
    _ = json.loads(raw)
    return {**state, "tool_trace": trace}


def node_followups(state: AgentGraphState) -> AgentGraphState:
    trace = list(state.get("tool_trace", []))
    summary_bits = [
        state.get("user_text", ""),
        json.dumps(state.get("extracted_patch", {}), ensure_ascii=False),
    ]
    summary = "\n".join(summary_bits)[:4000]
    raw = plan_follow_ups.invoke({"summary": summary})
    append_trace(trace, "plan_follow_ups", {"summary_chars": len(summary)})
    suggestions = json.loads(raw).get("suggestions", [])
    return {**state, "follow_up_suggestions": suggestions, "tool_trace": trace}


def node_assistant_reply(state: AgentGraphState) -> AgentGraphState:
    flags = state.get("compliance_flags") or []
    patch = state.get("extracted_patch") or {}
    if not settings.openrouter_api_key:
        msg = (
            "Applied a local extraction stub (set OPENROUTER_API_KEY for full LLM). "
            f"Proposed {len(patch)} field updates."
        )
    else:
        msg = (
            "Extracted structured updates from your message. "
            f"Fields touched: {', '.join(patch.keys()) or 'none'}. "
        )
        if flags:
            msg += f"Compliance review flagged: {', '.join(flags)}."
    return {**state, "assistant_reply": msg}


def build_graph():
    g = StateGraph(AgentGraphState)
    g.add_node("hcp_context", node_hcp_context)
    g.add_node("extract", node_extract)
    g.add_node("compliance", node_compliance)
    g.add_node("followups", node_followups)
    g.add_node("reply", node_assistant_reply)
    g.set_entry_point("hcp_context")
    g.add_edge("hcp_context", "extract")
    g.add_edge("extract", "compliance")
    g.add_edge("compliance", "followups")
    g.add_edge("followups", "reply")
    g.add_edge("reply", END)
    return g.compile()


graph = build_graph()


def run_parse_graph(user_text: str, form_draft: dict) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    out = graph.invoke(
        {
            "user_text": user_text,
            "form_draft": form_draft,
            "tool_trace": [],
            "run_id": run_id,
        }
    )
    out["run_id"] = run_id
    return out
