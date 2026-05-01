from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Sentiment = Literal["positive", "neutral", "negative"]
InteractionType = Literal["meeting", "call", "email", "conference", "other"]


class MaterialRef(BaseModel):
    catalog_id: str
    name: str
    quantity: int = 1


class SampleRef(BaseModel):
    sku: str
    name: str
    quantity: int = 1


class InteractionDraft(BaseModel):
    hcp_id: str | None = None
    hcp_name: str | None = None
    interaction_type: InteractionType = "meeting"
    occurred_at: datetime | None = None
    attendees: list[str] = Field(default_factory=list)
    topics_discussed: str = ""
    materials: list[MaterialRef] = Field(default_factory=list)
    samples: list[SampleRef] = Field(default_factory=list)
    sentiment: Sentiment = "neutral"
    outcomes: str = ""
    follow_up_actions: str = ""
    ai_suggested_follow_ups: list[str] = Field(default_factory=list)
    summary: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ParseChatRequest(BaseModel):
    messages: list[ChatMessage]
    draft: InteractionDraft | None = None


class FieldConfidence(BaseModel):
    field: str
    score: float = Field(ge=0.0, le=1.0)
    rationale: str | None = None


class ParseChatResponse(BaseModel):
    draft_patch: dict
    assistant_message: str
    follow_up_suggestions: list[str] = Field(default_factory=list)
    confidence: list[FieldConfidence] = Field(default_factory=list)
    compliance_flags: list[str] = Field(default_factory=list)
    tool_trace: list[dict] = Field(default_factory=list)
    run_id: str


class LogInteractionRequest(BaseModel):
    draft: InteractionDraft
    chat_transcript: list[ChatMessage] | None = None
    rep_id: str = "demo-rep"


class LogInteractionResponse(BaseModel):
    interaction_id: str
    status: Literal["logged"] = "logged"
    summary: str
    tool_trace: list[dict] = Field(default_factory=list)


class EditInteractionRequest(BaseModel):
    natural_language_edit: str | None = None
    draft_patch: dict | None = None
    reason: str = ""


class EditInteractionResponse(BaseModel):
    interaction_id: str
    revision: int
    draft: InteractionDraft
    tool_trace: list[dict] = Field(default_factory=list)
