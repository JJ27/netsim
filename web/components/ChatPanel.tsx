"use client";

import { useState } from "react";
import { sendChat, ChatResponse } from "@/lib/api";

type Props = { carrier: string; year: number; quarter: number };

type Turn = { role: "user" | "assistant"; text: string; agents?: ChatResponse };

export default function ChatPanel({ carrier, year, quarter }: Props) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    const msg = input.trim();
    if (!msg || busy) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", text: msg }]);
    setBusy(true);
    try {
      const resp = await sendChat({ message: msg, carrier, year, quarter });
      const combined = Object.entries(resp)
        .map(([agent, text]) => `**${agent}**\n${text}`)
        .join("\n\n");
      setTurns((t) => [...t, { role: "assistant", text: combined, agents: resp }]);
    } catch (e) {
      setTurns((t) => [...t, { role: "assistant", text: `Error: ${String(e)}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="flex h-full flex-col border-l border-gray-800 bg-panel">
      <header className="border-b border-gray-800 px-4 py-3">
        <div className="text-sm font-semibold">Ask about {carrier}</div>
        <div className="text-xs text-gray-500">
          Snapshot: {year}Q{quarter}
        </div>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3 text-sm">
        {turns.length === 0 && (
          <div className="text-gray-500">
            Try: <em>&quot;What happened to {carrier}&apos;s network in 2024?&quot;</em>
          </div>
        )}
        {turns.map((t, i) => (
          <div
            key={i}
            className={t.role === "user" ? "text-gray-200" : "whitespace-pre-wrap text-gray-300"}
          >
            {t.role === "user" ? <span className="font-semibold">You: </span> : null}
            {t.text}
          </div>
        ))}
        {busy && <div className="text-gray-500">Thinking…</div>}
      </div>

      <form
        className="border-t border-gray-800 p-3"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <input
          className="w-full rounded border border-gray-700 bg-ink px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
          placeholder="Ask about this carrier…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
        />
      </form>
    </aside>
  );
}
