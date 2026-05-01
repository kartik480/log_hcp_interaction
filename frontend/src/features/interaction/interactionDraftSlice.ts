import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export type Sentiment = "positive" | "neutral" | "negative";
export type InteractionType = "meeting" | "call" | "email" | "conference" | "other";

export interface MaterialRef {
  catalog_id: string;
  name: string;
  quantity: number;
}

export interface SampleRef {
  sku: string;
  name: string;
  quantity: number;
}

export interface InteractionDraftState {
  hcp_id: string | null;
  hcp_name: string;
  interaction_type: InteractionType;
  occurred_at: string;
  attendees: string;
  topics_discussed: string;
  materials: MaterialRef[];
  samples: SampleRef[];
  sentiment: Sentiment;
  outcomes: string;
  follow_up_actions: string;
  ai_suggested_follow_ups: string[];
  summary: string;
}

const initialState: InteractionDraftState = {
  hcp_id: null,
  hcp_name: "",
  interaction_type: "meeting",
  occurred_at: "",
  attendees: "",
  topics_discussed: "",
  materials: [],
  samples: [],
  sentiment: "neutral",
  outcomes: "",
  follow_up_actions: "",
  ai_suggested_follow_ups: [],
  summary: "",
};

function toLocalDatetimeValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const slice = createSlice({
  name: "interactionDraft",
  initialState: { ...initialState, occurred_at: toLocalDatetimeValue(new Date()) },
  reducers: {
    resetDraft: () => ({
      ...initialState,
      occurred_at: toLocalDatetimeValue(new Date()),
    }),
    setField<K extends keyof InteractionDraftState>(state, action: PayloadAction<{ key: K; value: InteractionDraftState[K] }>) {
      const { key, value } = action.payload;
      state[key] = value;
    },
    applyServerDraft(state, action: PayloadAction<Record<string, unknown>>) {
      const p = action.payload;
      if (typeof p.hcp_name === "string") state.hcp_name = p.hcp_name;
      if (typeof p.interaction_type === "string") state.interaction_type = p.interaction_type as InteractionType;
      if (typeof p.occurred_at === "string") {
        const raw = p.occurred_at;
        state.occurred_at = raw.includes("T") ? raw.slice(0, 16) : raw;
      }
      if (Array.isArray(p.attendees)) state.attendees = (p.attendees as string[]).join(", ");
      if (typeof p.topics_discussed === "string") state.topics_discussed = p.topics_discussed;
      if (typeof p.outcomes === "string") state.outcomes = p.outcomes;
      if (typeof p.follow_up_actions === "string") state.follow_up_actions = p.follow_up_actions;
      if (typeof p.sentiment === "string") state.sentiment = p.sentiment as Sentiment;
      if (Array.isArray(p.materials)) state.materials = p.materials as MaterialRef[];
      if (Array.isArray(p.samples)) state.samples = p.samples as SampleRef[];
      if (Array.isArray(p.ai_suggested_follow_ups)) {
        state.ai_suggested_follow_ups = p.ai_suggested_follow_ups as string[];
      }
      if (typeof p.summary === "string") state.summary = p.summary;
    },
    adoptFollowUpSuggestion(state, action: PayloadAction<string>) {
      const line = action.payload;
      state.follow_up_actions = state.follow_up_actions
        ? `${state.follow_up_actions}\n• ${line}`
        : `• ${line}`;
    },
  },
});

export const { resetDraft, setField, applyServerDraft, adoptFollowUpSuggestion } = slice.actions;
export const interactionDraftReducer = slice.reducer;
