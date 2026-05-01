import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

interface ChatSessionState {
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  lastRunId: string | null;
}

const initialState: ChatSessionState = {
  messages: [
    {
      role: "assistant",
      content:
        "Log interaction details here (for example: “Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure”) or ask for help.",
    },
  ],
  loading: false,
  error: null,
  lastRunId: null,
};

const slice = createSlice({
  name: "chatSession",
  initialState,
  reducers: {
    addMessage(state, action: PayloadAction<ChatMessage>) {
      state.messages.push(action.payload);
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.loading = action.payload;
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },
    setLastRunId(state, action: PayloadAction<string | null>) {
      state.lastRunId = action.payload;
    },
    clearChat(state) {
      state.messages = initialState.messages;
      state.lastRunId = null;
      state.error = null;
    },
  },
});

export const { addMessage, setLoading, setError, setLastRunId, clearChat } = slice.actions;
export const chatSessionReducer = slice.reducer;
