import { NextRequest } from "next/server";
import { loadAvailability } from "@/lib/availability";
import { createOrderIntent } from "@/lib/order-intent";
import { Catalog, CatalogItem, loadCatalog, priceRange } from "@/lib/catalog";
import { McpEvidence, isMcpConfigured, readMcpEvidence } from "@/lib/mcp";
import { suggestUpsell } from "@/lib/upsell";

export const dynamic = "force-dynamic";

type AssistantIntent = "catalog" | "custom_order" | "complaint" | "status" | "policy" | "order_intent";
type EvidenceSource =
  | McpEvidence
  | {
      tool: string;
      source: "local";
      ok: true;
      summary: unknown;
    };

type McpCatalog = {
  items?: CatalogItem[];
};

type McpCapacity = {
  dailyCapacityMinutes?: number;
  capacityMinutes?: number;
  currentLoadMinutes?: number;
  currentLoad?: number;
  defaultLeadTimeMinutes?: number;
};

type McpConstraint = {
  productId?: string;
  name?: string;
  leadTimeMinutes?: number;
  prepMinutes?: number;
  requiresCustomWork?: boolean;
};

type McpOrder = {
  orderId?: string;
  id?: string;
  status?: string;
  customerName?: string;
};

type McpTicket = {
  ticketId?: string;
  id?: string;
  status?: string;
  orderId?: string;
};

const CUSTOM_ORDER_ANSWER =
  "For custom birthday/design requests, HappyCake needs headcount, flavor, theme/reference photo, exact pickup time, name-on-cake, and allergy notes. Custom work is owner-gated before we promise kitchen capacity; if timing is tight in Sugar Land, I can suggest ready-made cake \"Honey\" (medovik) or cake \"Milk Maiden\" instead.";

const COMPLAINT_ANSWER =
  "I’m sorry — HappyCake fixes cake issues fast. Please send the order name, pickup time, a photo, and what went wrong. I will route it to owner review for a replacement/refund decision before any irreversible action, with the Sugar Land pickup context included.";

const STATUS_ANSWER =
  "For HappyCake order status, share the order name and pickup time. I can read availability at /api/availability for the Sugar Land kitchen, but I do not mark cake \"Honey\", cake \"Milk Maiden\", or any order ready unless Square/kitchen status confirms it.";

function classify(message: string): AssistantIntent {
  const m = message.toLowerCase();
  if (/complaint|wrong|late|refund|problem|bad|issue|pickup confusing/.test(m)) return "complaint";
  if (/status|ready|pickup|where.*order|my order/.test(m)) return "status";
  if (/custom|birthday|design|theme|name on cake|allergy|allergies/.test(m)) return "custom_order";
  if (/order|buy|reserve|checkout|want/.test(m)) return "order_intent";
  if (/delivery|hours|policy|refund|allergen|allergy/.test(m)) return "policy";
  return "catalog";
}

function localEvidence(tool: string, summary: unknown): EvidenceSource {
  return { tool, source: "local", ok: true, summary };
}

function summarizeCatalog(catalog: Catalog | McpCatalog | undefined) {
  const items = catalog?.items ?? [];
  return {
    itemCount: items.length,
    sample: items.slice(0, 5).map((item) => item.name),
  };
}

function summarizeCapacity(capacity: McpCapacity | undefined) {
  if (!capacity) return undefined;
  return {
    dailyCapacityMinutes: capacity.dailyCapacityMinutes ?? capacity.capacityMinutes,
    currentLoadMinutes: capacity.currentLoadMinutes ?? capacity.currentLoad,
    defaultLeadTimeMinutes: capacity.defaultLeadTimeMinutes,
  };
}

function summarizeConstraints(constraints: unknown) {
  const rows = Array.isArray(constraints)
    ? constraints
    : Array.isArray((constraints as { items?: unknown[] } | undefined)?.items)
      ? (constraints as { items: unknown[] }).items
      : [];
  return {
    itemCount: rows.length,
    customWorkItems: rows
      .filter((row): row is McpConstraint => Boolean((row as McpConstraint).requiresCustomWork))
      .map((row) => row.name ?? row.productId)
      .filter(Boolean)
      .slice(0, 5),
  };
}

function summarizeOrders(orders: unknown) {
  const rows = Array.isArray(orders)
    ? orders
    : Array.isArray((orders as { orders?: unknown[] } | undefined)?.orders)
      ? (orders as { orders: unknown[] }).orders
      : [];
  return {
    orderCount: rows.length,
    recent: rows.slice(0, 5).map((row) => {
      const order = row as McpOrder;
      return { orderId: order.orderId ?? order.id, status: order.status, customerName: order.customerName };
    }),
  };
}

function summarizeTickets(tickets: unknown) {
  const rows = Array.isArray(tickets)
    ? tickets
    : Array.isArray((tickets as { tickets?: unknown[] } | undefined)?.tickets)
      ? (tickets as { tickets: unknown[] }).tickets
      : [];
  return {
    ticketCount: rows.length,
    recent: rows.slice(0, 5).map((row) => {
      const ticket = row as McpTicket;
      return { ticketId: ticket.ticketId ?? ticket.id, status: ticket.status, orderId: ticket.orderId };
    }),
  };
}

async function getCatalogEvidence(): Promise<{ catalog: Catalog | McpCatalog; evidence: EvidenceSource[] }> {
  if (!isMcpConfigured()) {
    const catalog = loadCatalog();
    return {
      catalog,
      evidence: [localEvidence("square_list_catalog", { source: catalog.source, ...summarizeCatalog(catalog) })],
    };
  }

  const { result, evidence } = await readMcpEvidence<McpCatalog>(
    "square_list_catalog",
    {},
    summarizeCatalog,
  );
  if (result?.items?.length) {
    return { catalog: result, evidence: [evidence] };
  }

  const catalog = loadCatalog();
  return {
    catalog,
    evidence: [
      evidence,
      localEvidence("catalog_snapshot_fallback", { source: catalog.source, ...summarizeCatalog(catalog) }),
    ],
  };
}

async function getKitchenEvidence(): Promise<EvidenceSource[]> {
  if (!isMcpConfigured()) {
    return [
      localEvidence("kitchen_get_capacity", { configured: false }),
      localEvidence("kitchen_get_menu_constraints", {
        source: "catalog leadTimeMinutes/allergens fixture",
      }),
    ];
  }

  const [capacity, constraints] = await Promise.all([
    readMcpEvidence<McpCapacity>("kitchen_get_capacity", {}, summarizeCapacity),
    readMcpEvidence("kitchen_get_menu_constraints", {}, summarizeConstraints),
  ]);
  return [capacity.evidence, constraints.evidence];
}

async function catalogAnswer(catalog: Catalog | McpCatalog = loadCatalog()) {
  const items = (catalog.items ?? []).slice(0, 5);
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
        variationId: typeof body.variationId === "string" ? body.variationId : undefined,
        quantity: typeof body.quantity === "number" ? body.quantity : 1,
        customerName: body.customerName,
        contact: body.contact,
        fulfillmentType: body.fulfillmentType,
        deliveryAddress: body.deliveryAddress,
        pickupDate: body.pickupDate,
        pickupTime: body.pickupTime,
        scheduledFor: body.scheduledFor,
        notes: message,
        source: "assistant",
      });
      const evidence: EvidenceSource[] = [
        localEvidence("create_order_intent", {
          intentId: order.intentId,
          product: order.product.name,
          ownerGate: order.handoff.ownerGate,
        }),
      ];
      const mcpHandoff: Record<string, unknown> = {};

      if (isMcpConfigured() && !order.handoff.ownerGate.required) {
        const square = await readMcpEvidence<McpOrder>(
          "square_create_order",
          {
            source: "website",
            customerName: order.customer.name,
            customerNote: order.customer.notes ?? "Website assistant order intent captured.",
            items: [
              {
                variationId: order.product.variationId,
                quantity: order.product.quantity,
                note: order.customer.pickupTime ? `Pickup ${order.customer.pickupTime}` : undefined,
              },
            ],
          },
          (result) => ({
            orderId: result?.orderId ?? result?.id,
            status: result?.status,
          }),
        );
        evidence.push(square.evidence);
        const orderId = square.result?.orderId ?? square.result?.id;
        if (orderId) {
          mcpHandoff.squareOrderId = orderId;
          const kitchen = await readMcpEvidence<McpTicket>(
            "kitchen_create_ticket",
            {
              orderId,
              customerName: order.customer.name,
              items: [{ productId: order.product.id, quantity: order.product.quantity }],
              requestedPickupAt: [order.customer.pickupDate, order.customer.pickupTime].filter(Boolean).join(" ") || undefined,
              notes: order.customer.notes,
            },
            (result) => ({
              ticketId: result?.ticketId ?? result?.id,
              status: result?.status,
            }),
          );
          evidence.push(kitchen.evidence);
          mcpHandoff.kitchenTicketId = kitchen.result?.ticketId ?? kitchen.result?.id;
        }
      } else if (order.handoff.ownerGate.required) {
        evidence.push(localEvidence("owner_gate", order.handoff.ownerGate));
      }

      const catalogForUpsell = loadCatalog();
      const itemForUpsell = catalogForUpsell.items.find(
        (i) => i.id === order.product.id || i.slug === productSlug,
      );
      // Skip upsell on owner-gated paths — the order isn't accepted yet,
      // pitching add-ons before owner approval is off-brand and confusing.
      const upsell =
        itemForUpsell && !order.handoff.ownerGate.required
          ? suggestUpsell(itemForUpsell, catalogForUpsell.items, order.product.estimatedTotalUsd ?? 0)
          : null;
      if (upsell) {
        evidence.push(
          localEvidence("upsell_offered", {
            productSlug: itemForUpsell?.slug,
            kind: upsell.kind,
            sku: upsell.sku,
            priceUsd: upsell.priceUsd,
            reason: upsell.reason,
          }),
        );
      }
      const answer =
        `I captured this as a website order intent for ${order.product.name}. ` +
        `Estimated total starts at $${order.product.estimatedTotalUsd}. ` +
        `${order.nextStep}` +
        (upsell ? ` ${upsell.message}` : "");
      return Response.json({
        ok: true,
        intent,
        answer,
        escalation: order.handoff.ownerGate,
        orderIntent: order,
        mcpHandoff,
        upsell,
        evidence,
        suggestedActions: ["Confirm pickup time", "Confirm allergy concerns", "Send to WhatsApp", "Owner review if gated"],
      });
    }

    if (intent === "custom_order") {
      const [{ evidence: catalogEvidence }, kitchenEvidence] = await Promise.all([
        getCatalogEvidence(),
        getKitchenEvidence(),
      ]);
      return Response.json({
        ok: true,
        intent,
        answer: CUSTOM_ORDER_ANSWER,
        escalation: { required: true, reason: "custom cake or allergy/design signal" },
        endpoints: { catalog: "/api/catalog", policies: "/api/policies", availability: "/api/availability" },
        availability: { endpoint: "/api/availability" },
        evidence: [...catalogEvidence, ...kitchenEvidence, localEvidence("owner_gate", { reason: "custom cake or allergy/design signal" })],
        suggestedActions: ["Collect missing details", "Offer ready-made alternative", "Escalate to owner Telegram gate"],
      });
    }

    if (intent === "complaint") {
      const evidence: EvidenceSource[] = [];
      if (isMcpConfigured()) {
        const orders = await readMcpEvidence("square_recent_orders", { limit: 10 }, summarizeOrders);
        evidence.push(orders.evidence);
      } else {
        evidence.push(localEvidence("square_recent_orders", { configured: false }));
      }
      evidence.push(localEvidence("owner_gate", { reason: "complaint/remediation path" }));
      return Response.json({
        ok: true,
        intent,
        answer: COMPLAINT_ANSWER,
        escalation: { required: true, reason: "complaint/remediation path" },
        endpoints: { policies: "/api/policies", availability: "/api/availability" },
        availability: { endpoint: "/api/availability" },
        evidence,
        suggestedActions: ["Collect photo", "Collect order name", "Owner-gated refund/replacement", "Follow up on WhatsApp"],
      });
    }

    if (intent === "status") {
      const evidence: EvidenceSource[] = [];
      if (isMcpConfigured()) {
        const [orders, tickets, production] = await Promise.all([
          readMcpEvidence("square_recent_orders", { limit: 10 }, summarizeOrders),
          readMcpEvidence("kitchen_list_tickets", {}, summarizeTickets),
          readMcpEvidence("kitchen_get_production_summary", {}, (result) => result),
        ]);
        evidence.push(orders.evidence, tickets.evidence, production.evidence);
      } else {
        evidence.push(
          localEvidence("square_recent_orders", { configured: false }),
          localEvidence("kitchen_list_tickets", { configured: false }),
        );
      }
      return Response.json({
        ok: true,
        intent,
        answer: STATUS_ANSWER,
        escalation: { required: false },
        endpoints: { policies: "/api/policies", availability: "/api/availability" },
        evidence,
        suggestedActions: ["Ask for order name", "Ask for pickup time", "Check kitchen ticket", "Message customer with ETA"],
      });
    }

    if (intent === "policy") {
      const kitchenEvidence = await getKitchenEvidence();
      return Response.json({
        ok: true,
        intent,
        answer:
          "Pickup is the default HappyCake path from Sugar Land. Local delivery is limited/case-by-case. Same-day pickup is never guaranteed without live inventory and kitchen capacity confirmation. Traditional cakes like cake \"Honey\" (medovik) can contain wheat, egg, dairy, and sometimes nuts/soy — tell us allergies before ordering, especially for Nauryz or family celebrations. Same-day issues should be sent with a photo so the owner can approve replacement/refund.",
        escalation: { required: false },
        endpoints: { policies: "/api/policies", catalog: "/api/catalog", availability: "/api/availability" },
        evidence: [
          localEvidence("policy_static", { endpoint: "/api/policies", source: "repo policy contract" }),
          ...kitchenEvidence,
        ],
      });
    }

    const { catalog, evidence } = await getCatalogEvidence();
    const kitchenEvidence = await getKitchenEvidence();
    return Response.json({
      ok: true,
      intent,
      answer: await catalogAnswer(catalog),
      escalation: { required: false },
      endpoints: { catalog: "/api/catalog", availability: "/api/availability", orderIntent: "/api/order-intent" },
      evidence: [...evidence, ...kitchenEvidence],
    });
  } catch (error) {
    return Response.json(
      { ok: false, error: error instanceof Error ? error.message : "Assistant request failed" },
      { status: 400 },
    );
  }
}
