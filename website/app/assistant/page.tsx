import AssistantClient from "./AssistantClient";

export const metadata = {
  title: "Cake assistant",
  description: "HappyCake on-site assistant for product guidance, order intake, complaints, and owner escalation.",
};

export default function AssistantPage() {
  return (
    <div className="space-y-8">
      <div className="max-w-3xl">
        <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">On-site assistant</p>
        <h1 className="font-display text-4xl text-happy-blue-900 mt-2">Ask Arai about cakes</h1>
        <p className="mt-4 text-ink/75">A lightweight browser assistant for evaluator testing. It reads the same catalog/policy surface as agents and returns explicit owner-gate and order-intent metadata.</p>
      </div>
      <AssistantClient />
    </div>
  );
}
