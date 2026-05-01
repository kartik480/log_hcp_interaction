import { apiJson } from "./client";
import type { ChatMessage } from "../features/interaction/chatSessionSlice";
import type { InteractionDraftState } from "../features/interaction/interactionDraftSlice";

export interface ParseChatResponse {
  draft_patch: Record<string, unknown>;
  assistant_message: string;
  follow_up_suggestions: string[];
  confidence: { field: string; score: number; rationale?: string | null }[];
  compliance_flags: string[];
  tool_trace: Record<string, unknown>[];
  run_id: string;
}

export interface LogInteractionResponse {
  interaction_id: string;
  status: "logged";
  summary: string;
  tool_trace: Record<string, unknown>[];
}

function draftToPayload(d: InteractionDraftState) {
  return {
    hcp_id: d.hcp_id,
    hcp_name: d.hcp_name || null,
    interaction_type: d.interaction_type,
    occurred_at: d.occurred_at ? new Date(d.occurred_at).toISOString() : null,
    attendees: d.attendees
      ? d.attendees.split(",").map((s) => s.trim()).filter(Boolean)
      : [],
    topics_discussed: d.topics_discussed,
    materials: d.materials,
    samples: d.samples,
    sentiment: d.sentiment,
    outcomes: d.outcomes,
    follow_up_actions: d.follow_up_actions,
    ai_suggested_follow_ups: d.ai_suggested_follow_ups,
    summary: d.summary || null,
  };
}

export function parseChat(messages: ChatMessage[], draft: InteractionDraftState) {
  return apiJson<ParseChatResponse>("/interactions/parse-chat", {
    method: "POST",
    body: JSON.stringify({
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      draft: draftToPayload(draft),
    }),
  });
}

export function logInteraction(draft: InteractionDraftState, chatTranscript: ChatMessage[]) {
  return apiJson<LogInteractionResponse>("/interactions/log", {
    method: "POST",
    body: JSON.stringify({
      draft: draftToPayload(draft),
      chat_transcript: chatTranscript,
      rep_id: "demo-rep",
    }),
  });
}
