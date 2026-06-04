import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { auth } from "./lib/firebase";

export default function ChatPanel({ messages, setMessages, onCitationClick }) {
  const [question, setQuestion] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef(null);
  const activeRequestId = useRef(0);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  async function handleAsk(e) {
    e.preventDefault();
    if (!question.trim() || streaming) return;

    const q = question.trim();
    setQuestion("");
    activeRequestId.current += 1;
    const myRequestId = activeRequestId.current;

    setMessages((m) => [
      ...m,
      { role: "user", text: q },
      { role: "assistant", text: "", citations: [] },
    ]);
    setStreaming(true);

    try {
      const token = await auth.currentUser.getIdToken();
      const resp = await fetch(`${import.meta.env.VITE_API_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ question: q }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        if (activeRequestId.current !== myRequestId) { await reader.cancel(); return; }
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop();

        for (const event of events) {
          const line = event.trim();
          if (!line.startsWith("data:")) continue;
          const payload = JSON.parse(line.slice(5).trim());

          if (payload.type === "citations") {
            setMessages((m) => {
              const updated = [...m];
              updated[updated.length - 1] = { ...updated[updated.length - 1], citations: payload.data };
              return updated;
            });
          } else if (payload.type === "text") {
            setMessages((m) => {
              const updated = [...m];
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                text: updated[updated.length - 1].text + payload.data,
              };
              return updated;
            });
          }
        }
      }
    } catch (err) {
      setMessages((m) => {
        const updated = [...m];
        updated[updated.length - 1] = { ...updated[updated.length - 1], text: `Error: ${err.message}` };
        return updated;
      });
    } finally { setStreaming(false); }
  }

  const suggestions = [
    "What have I been worried about lately?",
    "When did I feel really good?",
    "What patterns do you see?",
  ];

  return (
    <div className="flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
        {messages.length === 0 && (
          <div className="space-y-3 pt-8">
            <p className="text-sm text-ink-500 italic font-serif">Some questions to start:</p>
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => setQuestion(s)}
                className="block w-full text-left px-4 py-3 bg-paper-50 border border-paper-400 rounded-lg text-sm font-serif text-ink-700 hover:border-forest hover:bg-sage-100 transition-colors"
              >
                "{s}"
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={msg.role === "user" ? "flex justify-end" : ""}>
            <div
              className={`max-w-[92%] px-4 py-3 rounded-lg text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-forest"
                  : "bg-paper-50 border border-paper-400"
              }`}
            >
              <RenderedMessage
                text={msg.text}
                citations={msg.citations}
                onCitationClick={onCitationClick}
                isUser={msg.role === "user"}
              />
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={handleAsk} className="border-t border-paper-400 p-3 flex gap-2 bg-paper-300">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask anything…"
          disabled={streaming}
          className="flex-1 bg-paper-50 border border-paper-400 rounded-full px-4 py-2 text-sm text-ink-900 placeholder-ink-400 focus:outline-none focus:border-forest transition-colors"
        />
        <button
          disabled={streaming || !question.trim()}
          className="bg-forest text-paper-100 px-4 py-2 rounded-full text-sm hover:bg-forest-dark transition-colors disabled:opacity-40 font-medium"
        >
          {streaming ? "…" : "Ask"}
        </button>
      </form>
    </div>
  );
}

/* ------------------------------------------------------------------
   Renders a chat message with proper markdown AND clickable citations.

   Approach: convert [E1], [E2] markers into placeholder markdown
   that survives the markdown parse, then replace those placeholders
   with citation buttons via a custom component override.

   This way markdown is parsed across the WHOLE message (so ** pairs
   stay balanced), and citations still become clickable buttons.
   ------------------------------------------------------------------ */
function RenderedMessage({ text, citations, onCitationClick, isUser }) {
  // User messages are plain text — no markdown, no citations needed.
  if (isUser) {
    return <span className="whitespace-pre-wrap text-paper-100">{text}</span>;
  }

  const proseClasses = "prose prose-sm max-w-none text-ink-900 prose-p:my-1.5 prose-strong:text-forest prose-strong:font-semibold prose-em:text-ink-900";

  if (!citations || citations.length === 0) {
    return (
      <div className={proseClasses}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div>
    );
  }

  // Map citation IDs to entry metadata for the click handler.
  const byId = Object.fromEntries(citations.map((c) => [c.id, c]));

  // Strategy: leave the citations inline in the markdown source as a custom
  // inline pattern that survives parsing — we'll use a placeholder format like
  // <CITE:E1> that markdown treats as raw HTML-ish, and intercept it via the
  // `code` / inline replacement. Simpler: use markdown links to a fake scheme,
  // then catch them with the `a` component override.
  // Example: [E1] → [E1](cite://E1)
  const linked = text.replace(
    /\[(E\d+(?:,\s*E\d+)*)\]/g,
    (_match, ids) => `[${ids}](cite://${ids.replace(/\s+/g, "")})`
  );

  return (
    <div className={proseClasses}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Intercept our cite:// links and render them as citation buttons.
          a({ href, children }) {
            if (typeof href === "string" && href.startsWith("cite://")) {
              const ids = href.slice(7).split(",");
              return (
                <span>
                  {ids.map((id, j) => {
                    const cite = byId[id];
                    if (!cite) return <span key={j}>[{id}]</span>;
                    return (
                      <button
                        key={j}
                        onClick={() => onCitationClick?.(cite.entry_id)}
                        className="inline-flex items-center px-1.5 py-0.5 mx-0.5 bg-sage-100 hover:bg-forest hover:text-paper-100 text-forest text-xs rounded font-medium transition-colors"
                        title={`Jump to entry from ${cite.created_at.slice(0, 10)}`}
                      >
                        {id}
                      </button>
                    );
                  })}
                </span>
              );
            }
            // Regular link — render as a plain anchor.
            return <a href={href} target="_blank" rel="noreferrer">{children}</a>;
          },
        }}
      >
        {linked}
      </ReactMarkdown>
    </div>
  );
}