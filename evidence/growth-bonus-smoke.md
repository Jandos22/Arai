# Growth bonus smoke evidence

These rows are the deterministic evidence shapes covered by
`orchestrator/tests/test_whatsapp_growth.py`.

```jsonl
{"kind":"lead_score","channel":"whatsapp","sender":"+12815550123","score":90,"segment":"hot","route":"owner_review","followUpAfterMinutes":15,"reasons":["whatsapp inbound","order intent","high-value occasion or bulk signal","time-sensitive request","repeat-customer Square evidence"],"evidenceSources":["whatsapp_inbound","square_recent_orders"],"smoke":"orchestrator/tests/test_whatsapp_growth.py::test_whatsapp_inbound_writes_lead_score_from_square_evidence"}
{"kind":"whatsapp_follow_up_sent","recipient":"+12815550123","bodyPreview":"Hi! Quick Happy Cake reminder: your order sq_order_123 is on our pickup list for today at 4 PM. Reply here if anything changes.","evidenceSources":["square_recent_orders","whatsapp_send"],"smoke":"orchestrator/tests/test_whatsapp_growth.py::test_follow_up_due_checks_square_then_sends_whatsapp"}
```
