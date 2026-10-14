import { A2uiSurface } from "@a2ui/react/v0_9";
import type { ReactCatalogComponent } from "@a2ui/react/v0_9";
import { basicCatalog } from "@a2ui/web_core/v0_9/basic_catalog";
import { MessageProcessor, type SurfaceModel } from "@a2ui/web_core/v0_9";
import { type FormEvent, useCallback, useRef, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

interface SurfaceEntry {
  model: SurfaceModel;
  disabled: boolean;
}

interface ChatEntry {
  id: number;
  role: "user" | "agent";
  text: string;
  surface?: SurfaceEntry;
}

interface ChatResponse {
  text: string;
  a2ui: Record<string, unknown>[];
}

export function App() {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const nextEntryId = useRef(0);

  const disableSurface = useCallback((entryId: number) => {
    setEntries((prev) =>
      prev.map((e) => (e.id === entryId && e.surface ? { ...e, surface: { ...e.surface, disabled: true } } : e)),
    );
  }, []);

  // Each turn that carries A2UI content gets its own MessageProcessor/surface
  // instance (surfaceId "item_creation"/"item_table" repeats turn to turn,
  // and the protocol forbids a createSurface for a surfaceId that already
  // exists -- a single shared processor across turns would collide). Older
  // turns' surfaces are kept, not deleted, and frozen in place instead.
  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      setEntries((prev) => [...prev, { id: nextEntryId.current++, role: "user", text: trimmed }]);
      setSending(true);
      try {
        const response = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: trimmed }),
        });
        if (!response.ok) {
          throw new Error(`${response.status} ${response.statusText}`);
        }
        const data = (await response.json()) as ChatResponse;

        const agentEntryId = nextEntryId.current++;
        let surface: SurfaceEntry | undefined;
        if (data.a2ui.length > 0) {
          const entryProcessor = new MessageProcessor([basicCatalog], (action) => {
            const ctx = action.context as Record<string, unknown>;
            let followUp: string | undefined;
            if (action.name === "create_item") {
              followUp =
                `Create an item named "${ctx.name}" with description ` +
                `"${ctx.description ?? ""}", price ${ctx.price}, and quantity ${ctx.quantity}.`;
            } else if (action.name === "create_customer") {
              followUp =
                `Create a customer named "${ctx.name}" with email "${ctx.email}", ` +
                `phone "${ctx.phone}", city "${ctx.city}", and country "${ctx.country}".`;
            } else {
              return;
            }
            disableSurface(agentEntryId);
            void sendMessage(followUp);
          });
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          entryProcessor.processMessages(data.a2ui as any);
          const model = Array.from(entryProcessor.model.surfacesMap.values())[0];
          if (model) {
            surface = { model, disabled: false };
          }
        }

        setEntries((prev) => [
          // Only the newest surface stays interactive; every earlier one is frozen.
          ...prev.map((e) => (e.surface ? { ...e, surface: { ...e.surface, disabled: true } } : e)),
          { id: agentEntryId, role: "agent", text: data.text, surface },
        ]);
      } catch (error) {
        setEntries((prev) => [
          ...prev,
          { id: nextEntryId.current++, role: "agent", text: `Error reaching the agent: ${String(error)}` },
        ]);
      } finally {
        setSending(false);
      }
    },
    [disableSurface],
  );

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    const text = input;
    setInput("");
    void sendMessage(text);
  };

  return (
    <div className="app">
      <h1>Agent Chat</h1>

      <div className="chat-log">
        {entries.length === 0 && <p className="chat-empty">Ask the agent a question to get started.</p>}
        {entries.map((entry) => (
          <div key={entry.id} className={`bubble bubble-${entry.role}`}>
            <span className="bubble-role">{entry.role === "user" ? "You" : "Agent"}</span>
            <p>{entry.text}</p>
            {entry.surface && (
              <div className={`surface${entry.surface.disabled ? " surface-disabled" : ""}`}>
                {/* basicCatalog's components are web components (ComponentApi), not React
                    components (ReactCatalogComponent, which adds `.render`); A2uiSurface
                    renders them as elements at runtime (see @a2ui/react's web-component
                    bridge) but its public type only declares the React-component case. */}
                <A2uiSurface surface={entry.surface.model as unknown as SurfaceModel<ReactCatalogComponent>} />
              </div>
            )}
          </div>
        ))}
        {sending && <div className="bubble bubble-agent bubble-pending">Thinking…</div>}
      </div>

      <form className="composer" onSubmit={onSubmit}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask the agent something…"
          disabled={sending}
        />
        <button type="submit" disabled={sending || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
