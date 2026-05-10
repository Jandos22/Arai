"use client";

import { FormEvent, useState } from "react";

type Turn = { role: "user" | "assistant"; text: string; payload?: unknown };

const EXAMPLES = [
  "Which cake works for 10 people today?",
  "I need a custom birthday cake tomorrow afternoon",
  "My pickup timing was confusing and I want help",
  "Is my order ready for pickup?",
];

export default function AssistantClient() {
  const [message, setMessage] = useState(EXAMPLES[0]);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);

  async function ask(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (!message.trim()) return;
    const userText = message.trim();
    setTurns((t) => [...t, { role: "user", text: userText }]);
    setLoading(true);
    const response = await fetch("/api/assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userText }),
    });
    const json = await response.json();
    setTurns((t) => [...t, { role: "assistant", text: json.answer ?? "I could not answer that.", payload: json }]);
    setLoading(false);
  }

  return (
    <div className="grid lg:grid-cols-[0.9fr_1.1fr] gap-8">
      <section className="rounded-3xl bg-cream-100 p-6 space-y-4">
        <h2 className="font-display text-2xl text-happy-blue-900">Ask the on-site assistant</h2>
        <p className="text-sm text-ink/70">Covers product guidance, custom orders, complaints, order-status questions, policies, and owner escalation.</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <button key={example} type="button" onClick={() => setMessage(example)} className="rounded-full border border-happy-blue-200 px-3 py-1.5 text-xs hover:bg-happy-blue-100">{example}</button>
          ))}
        </div>
        <form onSubmit={ask} className="space-y-3">
          <textarea className="w-full rounded-2xl border border-cream-300 bg-white px-4 py-3" rows={5} value={message} onChange={(e) => setMessage(e.target.value)} />
          <button className="rounded-full bg-happy-blue-700 text-cream-50 px-6 py-3 hover:bg-happy-blue-900 font-medium disabled:opacity-60" disabled={loading}>{loading ? "Thinking..." : "Ask assistant"}</button>
        </form>
      </section>

      <section className="space-y-4">
        {turns.length === 0 ? (
          <div className="rounded-3xl border border-happy-blue-200 p-6 text-ink/70">Try a product question, custom cake request, complaint, or order-status question. Responses include structured escalation and handoff metadata for evaluators.</div>
        ) : (
          turns.map((turn, idx) => (
            <article key={idx} className={turn.role === "user" ? "rounded-3xl bg-happy-blue-900 text-cream-50 p-5" : "rounded-3xl bg-white border border-cream-200 p-5"}>
              <p className="text-xs uppercase tracking-widest opacity-70">{turn.role}</p>
              <p className="mt-2 whitespace-pre-wrap">{turn.text}</p>
              {turn.payload ? <pre className="mt-4 max-h-72 overflow-auto rounded-2xl bg-cream-100 text-ink p-3 text-xs whitespace-pre-wrap">{JSON.stringify(turn.payload, null, 2)}</pre> : null}
            </article>
          ))
        )}
      </section>
    </div>
  );
}
