import { NextRequest } from "next/server";
import { loadAvailability } from "@/lib/availability";
import { createOrderIntent } from "@/lib/order-intent";
import { loadCatalog, priceRange } from "@/lib/catalog";

export const dynamic = "force-dynamic";

type AssistantIntent = "catalog" | "custom_order" | "complaint" | "status" | "policy" | "order_intent";

function classify(message: string): AssistantIntent {
  const m = message.toLowerCase();
  if (/complaint|wrong|late|refund|problem|bad|issue|pickup confusing/.test(m)) return "complaint";
  if (/status|ready|pickup|where.*order|my order/.test(m)) return "status";
  if (/custom|birthday|design|theme|name on cake|allergy|allergies/.test(m)) return "custom_order";
  if (/order|buy|reserve|checkout|want/.test(m)) return "order_intent";
  if (/delivery|hours|policy|refund|allergen|allergy/.test(m)) return "policy";
  return "catalog";
}

async function catalogAnswer() {
  const items = loadCatalog().items.slice(0, 5);
  const availability = await loadAvailability();
  return `I can help you pick a cake. Popular options: ${items
    .map((item) => {
      const { min, max } = priceRange(item);
      return `${item.name} ($${min}–$${max}, ${item.leadTimeMinutes ?? 90} min lead)`;
    })
    .join("; ")}. ${availability.customerPromise} Tell me occasion, pickup time, allergy concerns, and headcount.`;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const message = String(body.message ?? "").trim().slice(0, 1000);
    const productSlug = typeof body.productSlug === "string" ? body.productSlug : undefined;
    const intent = classify(message);

    if (intent === "order_intent") {
      const order = createOrderIntent({
        productSlug,
        quantity: 1,
        customerName: body.customerName,
        contact: body.contact,
        notes: message,
        source: "assistant",
      });
      return Response.json({
        ok: true,
        intent,
        answer:
          `I captured this as a website order intent for ${order.product.name}. ` +
          `Estimated total starts at $${order.product.estimatedTotalUsd}. ` +
          `${order.nextStep}`,
        escalation: order.handoff.ownerGate,
        orderIntent: order,
        suggestedActions: ["Confirm pickup time", "Confirm allergy concerns", "Send to WhatsApp", "Owner review if gated"],
      });
    }

    if (intent === "custom_order") {
      return Response.json({
        ok: true,
        intent,
        answer:
          "For custom birthday/design requests I need headcount, flavor, theme/reference photo, exact pickup time, name-on-cake, and allergy notes. Custom work is owner-gated before we promise kitchen capacity; I can still suggest ready-made Honey Cake or Milk Maiden if timing is tight.",
        escalation: { required: true, reason: "custom cake or allergy/design signal" },
        endpoints: { catalog: "/api/catalog", policies: "/api/policies" },
        availability: { endpoint: "/api/availability" },
        suggestedActions: ["Collect missing details", "Offer ready-made alternative", "Escalate to owner Telegram gate"],
      });
    }

    if (intent === "complaint") {
      return Response.json({
        ok: true,
        intent,
        answer:
          "I’m sorry — we fix cake issues fast. Please send the order name, pickup time, a photo, and what went wrong. I will route it to owner review for replacement/refund decision before any irreversible action.",
        escalation: { required: true, reason: "complaint/remediation path" },
        endpoints: { policies: "/api/policies" },
        availability: { endpoint: "/api/availability" },
        suggestedActions: ["Collect photo", "Collect order name", "Owner-gated refund/replacement", "Follow up on WhatsApp"],
      });
    }

    if (intent === "status") {
      return Response.json({
        ok: true,
        intent,
        answer:
          "For order status, share the order name and pickup time. I can read availability at /api/availability, but I do not mark anything ready unless Square/kitchen status confirms it.",
        escalation: { required: false },
        endpoints: { policies: "/api/policies", availability: "/api/availability" },
        suggestedActions: ["Ask for order name", "Ask for pickup time", "Check kitchen ticket", "Message customer with ETA"],
      });
    }

    if (intent === "policy") {
      return Response.json({
        ok: true,
        intent,
        answer:
          "Pickup is the default path from Sugar Land. Local delivery is limited/case-by-case. Same-day pickup is never guaranteed without live inventory and kitchen capacity confirmation. Cakes can contain wheat, egg, dairy, and sometimes nuts/soy — tell us allergies before ordering. Same-day issues should be sent with a photo so the owner can approve replacement/refund.",
        escalation: { required: false },
        endpoints: { policies: "/api/policies", catalog: "/api/catalog", availability: "/api/availability" },
      });
    }

    return Response.json({
      ok: true,
      intent,
      answer: await catalogAnswer(),
      escalation: { required: false },
      endpoints: { catalog: "/api/catalog", availability: "/api/availability", orderIntent: "/api/order-intent" },
    });
  } catch (error) {
    return Response.json(
      { ok: false, error: error instanceof Error ? error.message : "Assistant request failed" },
      { status: 400 },
    );
  }
}
