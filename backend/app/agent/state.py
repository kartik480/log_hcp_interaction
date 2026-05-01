from typing import TypedDict


class AgentGraphState(TypedDict, total=False):
    """LangGraph state for HCP interaction logging."""

    user_text: str
    form_draft: dict
    extracted_patch: dict
    assistant_reply: str
    follow_up_suggestions: list[str]
    compliance_flags: list[str]
    confidence: list[dict]
    tool_trace: list[dict]
    run_id: str
