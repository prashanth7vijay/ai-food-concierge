import { useEffect, useRef, useState } from "react";
import { Send, Loader2 } from "lucide-react";
import { useAppState } from "../context/AppStateContext";
import MessageBubble from "./MessageBubble";
import SuggestedPrompts from "./SuggestedPrompts";

export default function ChatPanel() {
  const { messages, sendMessage, isSending, chatError } = useAppState();
  const [draft, setDraft] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  const submit = (e) => {
    e?.preventDefault();
    if (!draft.trim() || isSending) return;
    sendMessage(draft);
    setDraft("");
  };

  return (
    <section className="flex h-full min-w-0 flex-1 flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <SuggestedPrompts onPick={(p) => sendMessage(p)} />
          </div>
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            {isSending && (
              <div className="flex items-center gap-2 text-xs text-ink-soft">
                <Loader2 size={14} className="animate-spin" />
                Thinking through your request…
              </div>
            )}
            {chatError && (
              <div className="rounded-md border border-chili/40 bg-chili-soft/60 px-3 py-2 text-sm text-ink">
                {chatError}
              </div>
            )}
          </div>
        )}
      </div>

      <form
        onSubmit={submit}
        className="border-t border-line bg-paper-raised px-4 py-3 sm:px-8"
      >
        <div className="mx-auto flex max-w-3xl items-center gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Tell me what you're craving…"
            className="flex-1 rounded-full border border-line bg-paper px-4 py-2.5 text-sm text-ink placeholder:text-ink-soft/60 focus:border-chili"
            aria-label="Message the food concierge"
          />
          <button
            type="submit"
            disabled={isSending || !draft.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-chili text-paper transition-opacity disabled:opacity-40"
            aria-label="Send message"
          >
            <Send size={16} />
          </button>
        </div>
      </form>
    </section>
  );
}
