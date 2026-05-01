import { configureStore } from "@reduxjs/toolkit";
import { chatSessionReducer } from "../features/interaction/chatSessionSlice";
import { interactionDraftReducer } from "../features/interaction/interactionDraftSlice";

export const store = configureStore({
  reducer: {
    interactionDraft: interactionDraftReducer,
    chatSession: chatSessionReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
