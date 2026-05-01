"""Additional LangGraph workflows for logging and editing interactions."""

from __future__ import annotations

import json
import uuid
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agent.tools import compliance_guard, edit_interaction, log_interaction, sync_calendar_tasks


class LogGraphState(TypedDict, total=False):
    rep_id: str
    draft: dict[str, Any]
    chat_transcript: list[dict[str, Any]]
    summary: str
    compliance_flags: list[str]
    interaction_id: str
    synced_tasks: int
    tool_trace: list[dict[str, Any]]
    run_id: str


class EditGraphState(TypedDict, total=False):
    interaction_id: str
    draft: dict[str, Any]
    patch: dict[str, Any]
    reason: str
    compliance_flags: list[str]
    revision: int
    tool_trace: list[dict[str, Any]]
    run_id: str


def _append_trace(trace: list[dict[str, Any]], tool: str, payload: dict[str, Any]) -> None:
    trace.append({"tool": tool, "payload": payload})


def node_log_summarize(state: LogGraphState) -> LogGraphState:
    draft = state.get("draft") or {}
    summary = (
        draft.get("summary")
        or draft.get("topics_discussed")
        or "Interaction logged via form/chat."
    )
    summary = str(summary)[:500]
    return {**state, "summary": summary}


def node_log_compliance(state: LogGraphState) -> LogGraphState:
    trace = list(state.get("tool_trace") or [])
    raw = compliance_guard.invoke(
        {"interaction_text": json.dumps({"draft": state.get("draft"), "summary": state.get("summary")})}
    )
    parsed = json.loads(raw)
    flags = parsed.get("flags") or []
    _append_trace(trace, "compliance_guard", {"flags": flags, "blocked": bool(parsed.get("blocked"))})
    return {**state, "compliance_flags": flags, "tool_trace": trace}


def node_log_persist(state: LogGraphState) -> LogGraphState:
    trace = list(state.get("tool_trace") or [])
    payload = log_interaction.invoke(
        {
            "rep_id": state.get("rep_id") or "demo-rep",
            "draft_json": json.dumps(state.get("draft") or {}),
            "chat_transcript_json": json.dumps(state.get("chat_transcript") or []),
        }
    )
    result = json.loads(payload)
    _append_trace(trace, "log_interaction", result)
    return {**state, "interaction_id": result["interaction_id"], "tool_trace": trace}


def node_log_sync_tasks(state: LogGraphState) -> LogGraphState:
    trace = list(state.get("tool_trace") or [])
    followups = (state.get("draft") or {}).get("ai_suggested_follow_ups") or []
    payload = sync_calendar_tasks.invoke(
        {
            "interaction_id": state.get("interaction_id") or "",
            "tasks_json": json.dumps(followups),
        }
    )
    result = json.loads(payload)
    _append_trace(trace, "sync_calendar_tasks", result)
    return {**state, "synced_tasks": int(result.get("synced", 0)), "tool_trace": trace}


def build_log_graph():
    g = StateGraph(LogGraphState)
    g.add_node("summarize", node_log_summarize)
    g.add_node("compliance", node_log_compliance)
    g.add_node("persist", node_log_persist)
    g.add_node("sync_tasks", node_log_sync_tasks)
    g.set_entry_point("summarize")
    g.add_edge("summarize", "compliance")
    g.add_edge("compliance", "persist")
    g.add_edge("persist", "sync_tasks")
    g.add_edge("sync_tasks", END)
    return g.compile()


def node_edit_compliance(state: EditGraphState) -> EditGraphState:
    trace = list(state.get("tool_trace") or [])
    raw = compliance_guard.invoke({"interaction_text": json.dumps({"patch": state.get("patch") or {}})})
    parsed = json.loads(raw)
    flags = parsed.get("flags") or []
    _append_trace(trace, "compliance_guard", {"flags": flags, "blocked": bool(parsed.get("blocked"))})
    return {**state, "compliance_flags": flags, "tool_trace": trace}


def node_edit_persist(state: EditGraphState) -> EditGraphState:
    trace = list(state.get("tool_trace") or [])
    payload = edit_interaction.invoke(
        {
            "interaction_id": state.get("interaction_id") or "",
            "draft_json": json.dumps(state.get("draft") or {}),
            "reason": state.get("reason") or "edit",
            "patch_json": json.dumps(state.get("patch") or {}),
        }
    )
    result = json.loads(payload)
    _append_trace(trace, "edit_interaction", result)
    return {**state, "revision": int(result["revision"]), "tool_trace": trace}


def build_edit_graph():
    g = StateGraph(EditGraphState)
    g.add_node("compliance", node_edit_compliance)
    g.add_node("persist", node_edit_persist)
    g.set_entry_point("compliance")
    g.add_edge("compliance", "persist")
    g.add_edge("persist", END)
    return g.compile()


log_graph = build_log_graph()
edit_graph = build_edit_graph()


def run_log_graph(rep_id: str, draft: dict[str, Any], chat_transcript: list[dict[str, Any]]) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    out = log_graph.invoke(
        {
            "rep_id": rep_id,
            "draft": draft,
            "chat_transcript": chat_transcript,
            "tool_trace": [],
            "run_id": run_id,
        }
    )
    out["run_id"] = run_id
    return out


def run_edit_graph(
    interaction_id: str, draft: dict[str, Any], patch: dict[str, Any], reason: str
) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    out = edit_graph.invoke(
        {
            "interaction_id": interaction_id,
            "draft": draft,
            "patch": patch,
            "reason": reason,
            "tool_trace": [],
            "run_id": run_id,
        }
    )
    out["run_id"] = run_id
    return out
