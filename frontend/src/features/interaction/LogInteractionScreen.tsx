import { useCallback, useState } from "react";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import { logInteraction, parseChat } from "../../api/interactions";
import {
  addMessage,
  clearChat,
  setError as setChatError,
  setLastRunId,
  setLoading as setChatLoading,
} from "./chatSessionSlice";
import {
  adoptFollowUpSuggestion,
  applyServerDraft,
  resetDraft,
  setField,
  type InteractionDraftState,
} from "./interactionDraftSlice";
import "./log-screen.css";

export function LogInteractionScreen() {
  const dispatch = useAppDispatch();
  const draft = useAppSelector((s) => s.interactionDraft);
  const chat = useAppSelector((s) => s.chatSession);
  const [chatInput, setChatInput] = useState("");

  const onChange =
    (key: keyof InteractionDraftState) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      dispatch(setField({ key, value: e.target.value as never }));
    };

  const sendToAi = useCallback(async () => {
    const text = chatInput.trim();
    if (!text) return;
    dispatch(setChatError(null));
    const userMsg = { role: "user" as const, content: text };
    dispatch(addMessage(userMsg));
    setChatInput("");
    dispatch(setChatLoading(true));
    try {
      const res = await parseChat([...chat.messages, userMsg], draft);
      dispatch(applyServerDraft(res.draft_patch));
      dispatch(addMessage({ role: "assistant", content: res.assistant_message }));
      dispatch(setLastRunId(res.run_id));
      if (res.compliance_flags.length) {
        dispatch(
          addMessage({
            role: "assistant",
            content: `Compliance flags: ${res.compliance_flags.join(", ")}`,
          }),
        );
      }
    } catch (e) {
      dispatch(setChatError(e instanceof Error ? e.message : "Request failed"));
    } finally {
      dispatch(setChatLoading(false));
    }
  }, [chat.messages, chatInput, dispatch, draft]);

  const submitInteraction = useCallback(async () => {
    dispatch(setChatError(null));
    dispatch(setChatLoading(true));
    try {
      const res = await logInteraction(draft, chat.messages);
      dispatch(
        addMessage({
          role: "assistant",
          content: `Interaction saved as ${res.interaction_id}.`,
        }),
      );
      dispatch(resetDraft());
      dispatch(clearChat());
    } catch (e) {
      dispatch(setChatError(e instanceof Error ? e.message : "Request failed"));
    } finally {
      dispatch(setChatLoading(false));
    }
  }, [chat.messages, dispatch, draft]);

  return (
    <div className="log-shell">
      <header className="log-header">
        <h1>Log HCP Interaction</h1>
      </header>

      <div className="log-grid">
        <section className="panel">
          <h2>Interaction details</h2>
          <p className="muted">Structured entry stays in sync with the AI assistant.</p>

          <div className="form-row">
            <div className="field">
              <label htmlFor="hcp_name">HCP name</label>
              <input
                id="hcp_name"
                placeholder="Search or select HCP…"
                value={draft.hcp_name}
                onChange={onChange("hcp_name")}
              />
            </div>
            <div className="field">
              <label htmlFor="interaction_type">Interaction type</label>
              <select
                id="interaction_type"
                value={draft.interaction_type}
                onChange={onChange("interaction_type")}
              >
                <option value="meeting">Meeting</option>
                <option value="call">Call</option>
                <option value="email">Email</option>
                <option value="conference">Conference</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="field">
              <label htmlFor="occurred_at">Date & time</label>
              <input
                id="occurred_at"
                type="datetime-local"
                value={draft.occurred_at}
                onChange={onChange("occurred_at")}
              />
            </div>
            <div className="field">
              <label htmlFor="attendees">Attendees</label>
              <input
                id="attendees"
                placeholder="Enter names or search…"
                value={draft.attendees}
                onChange={onChange("attendees")}
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="topics">Topics discussed</label>
            <textarea
              id="topics"
              placeholder="Enter key discussion points…"
              value={draft.topics_discussed}
              onChange={onChange("topics_discussed")}
            />
          </div>

          <div className="form-row">
            <div className="field">
              <label>Materials shared</label>
              <div className="chips">
                {draft.materials.length === 0 ? (
                  <span className="muted">No materials added</span>
                ) : (
                  draft.materials.map((m) => (
                    <span key={m.catalog_id + m.name} className="chip">
                      {m.name}
                    </span>
                  ))
                )}
              </div>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => {
                  const name = window.prompt("Material name");
                  if (!name) return;
                  dispatch(
                    setField({
                      key: "materials",
                      value: [
                        ...draft.materials,
                        { catalog_id: "PENDING", name, quantity: 1 },
                      ],
                    }),
                  );
                }}
              >
                Search / add
              </button>
            </div>
            <div className="field">
              <label>Samples distributed</label>
              <div className="chips">
                {draft.samples.length === 0 ? (
                  <span className="muted">No samples added</span>
                ) : (
                  draft.samples.map((s) => (
                    <span key={s.sku + s.name} className="chip">
                      {s.name}
                    </span>
                  ))
                )}
              </div>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => {
                  const name = window.prompt("Sample name");
                  if (!name) return;
                  dispatch(
                    setField({
                      key: "samples",
                      value: [...draft.samples, { sku: "PENDING", name, quantity: 1 }],
                    }),
                  );
                }}
              >
                Add sample
              </button>
            </div>
          </div>

          <div className="field">
            <label>Observed / inferred HCP sentiment</label>
            <div className="sentiment">
              {(
                [
                  ["positive", "Positive"],
                  ["neutral", "Neutral"],
                  ["negative", "Negative"],
                ] as const
              ).map(([val, label]) => (
                <label key={val}>
                  <input
                    type="radio"
                    name="sentiment"
                    value={val}
                    checked={draft.sentiment === val}
                    onChange={() => dispatch(setField({ key: "sentiment", value: val }))}
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>

          <div className="field">
            <label htmlFor="outcomes">Outcomes</label>
            <textarea
              id="outcomes"
              placeholder="Key outcomes or agreements…"
              value={draft.outcomes}
              onChange={onChange("outcomes")}
            />
          </div>

          <div className="field">
            <label htmlFor="followups">Follow-up actions</label>
            <textarea
              id="followups"
              placeholder="Enter next steps or tasks…"
              value={draft.follow_up_actions}
              onChange={onChange("follow_up_actions")}
            />
          </div>

          <div className="field">
            <label>AI suggested follow-ups</label>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              {draft.ai_suggested_follow_ups.map((s) => (
                <button key={s} type="button" className="btn btn-link" onClick={() => dispatch(adoptFollowUpSuggestion(s))}>
                  + {s}
                </button>
              ))}
              {draft.ai_suggested_follow_ups.length === 0 && (
                <span className="muted">Suggestions appear after you use the assistant.</span>
              )}
            </div>
          </div>

          <div className="toolbar">
            <button type="button" className="btn btn-primary" disabled={chat.loading} onClick={submitInteraction}>
              Submit interaction
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => dispatch(resetDraft())}>
              Reset form
            </button>
          </div>
        </section>

        <aside className="panel">
          <h2>AI assistant</h2>
          <p className="muted">Log interaction via chat; updates merge into the form.</p>

          <div className="chat-box">
            {chat.messages.map((m, i) => (
              <p key={i} className={`chat-line ${m.role === "user" ? "user" : "assistant"}`}>
                <strong>{m.role === "user" ? "You" : "Assistant"}: </strong>
                {m.content}
              </p>
            ))}
          </div>

          <div className="chat-input-row">
            <input
              placeholder="Describe interaction…"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void sendToAi();
                }
              }}
            />
            <button type="button" className="btn btn-primary" disabled={chat.loading} onClick={() => void sendToAi()}>
              Send
            </button>
          </div>
          {chat.error && <p className="error">{chat.error}</p>}
          {chat.lastRunId && (
            <p className="muted" style={{ marginTop: "0.5rem", fontSize: "0.75rem" }}>
              Last run: {chat.lastRunId}
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
