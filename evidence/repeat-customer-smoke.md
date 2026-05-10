# Repeat-customer bonus smoke evidence

Bonus bucket A — "repeat customers" + "abandoned orders" lift. Deterministic
evidence shapes covered by `orchestrator/tests/test_customers.py` and
emitted live by the orchestrator dispatcher when the listed events arrive.

## Auto-saved profile + greeting → proposed reorder

Triggered by the second WhatsApp inbound from a repeat customer where
`square_recent_orders` shows the same SKU ≥ 2 times.

```jsonl
{"kind":"customer_profile_upserted","channel":"whatsapp","identifier":"+12815550100","hasFavorite":true,"hasSavedPayment":false,"hasSavedAddress":false,"lastOrders":2,"evidenceSources":["channel_inbound","square_recent_orders"],"smoke":"orchestrator/tests/test_customers.py::test_whatsapp_greeting_triggers_proposed_reorder"}
{"kind":"repeat_customer_detected","channel":"whatsapp","sender":"+12815550100","favoriteSku":"medovik-medium","priorOrders":2,"evidenceSources":["customer_profile","square_recent_orders"],"smoke":"orchestrator/tests/test_customers.py::test_whatsapp_greeting_triggers_proposed_reorder"}
{"kind":"proposed_reorder","channel":"whatsapp","recipient":"+12815550100","sku":"medovik-medium","priorOrders":2,"savedPayment":false,"savedAddress":false,"bodyPreview":"Hi Sam! Welcome back to Happy Cake. Want your usual medovik medium? Just say 'yes' and we'll send a payment link.","evidenceSources":["customer_profile","whatsapp_send"]}
{"kind":"channel_outbound","label":"proposed_reorder","channel":"whatsapp","tool":"whatsapp_send","recipient":"+12815550100","bodyPreview":"Hi Sam! Welcome back to Happy Cake. Want your usual medovik medium? Just say 'yes' and we'll send a payment link."}
```

## Same flow on Instagram DM

```jsonl
{"kind":"customer_profile_upserted","channel":"instagram","identifier":"sam_h","hasFavorite":true,"hasSavedPayment":false,"hasSavedAddress":false,"lastOrders":0,"evidenceSources":["channel_inbound","square_recent_orders"],"smoke":"orchestrator/tests/test_customers.py::test_instagram_greeting_triggers_proposed_reorder"}
{"kind":"repeat_customer_detected","channel":"instagram","sender":"sam_h","threadId":"t1","favoriteSku":"milk-maiden","priorOrders":3,"evidenceSources":["customer_profile","square_recent_orders"]}
{"kind":"proposed_reorder","channel":"instagram","recipient":"t1","sku":"milk-maiden","priorOrders":3,"savedPayment":false,"savedAddress":false,"bodyPreview":"Hi Sam! Welcome back to Happy Cake. Want your usual milk maiden? Just say 'yes' and we'll send a payment link.","evidenceSources":["customer_profile","instagram_send_dm"]}
```

## Abandoned-order scheduler tick

Emitted at orchestrator startup and on every `schedule:abandoned_tick`
event. The handler scans `square_recent_orders`, filters to
`pending_pickup` state with pickup ≤ 120 min away, and re-emits a
synthetic `whatsapp:follow_up_due` event for each candidate. The
existing follow-up handler then sends through `whatsapp_send`.

```jsonl
{"kind":"abandoned_scan","leadMinutes":120,"candidateCount":1,"evidenceSources":["square_recent_orders"]}
{"kind":"abandoned_follow_up_emitted","orderId":"sq_order_456","pickupAt":"2026-05-10T15:00:00Z","recipient":"+12815550100","evidenceSources":["square_recent_orders"]}
```

## Storefront proof

- `/account/[id]` — read-only customer profile page with saved payment
  display, delivery address, last orders, and a "Reorder in one tap"
  CTA when `favorite_product.count >= 2`.
- `/api/customers/[id]` — agent-readable JSON view of the same profile
  with masked payment token (`Visa ending 4242`) and a
  `_quickReorderEndpoint` pointing at `/order?...&channel=quick-reorder`.

Real payment integration is sandbox-only here; `paymentToken` values are
opaque strings like `sandbox_card_visa_4242`. See
`docs/PRODUCTION-PATH.md` for the post-hackathon path.
