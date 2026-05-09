# Evidence schema

All orchestrator runs append to `evidence/orchestrator-<runId>.jsonl`. One JSON
object per line. Designed so judges can `grep`/`jq` directly, or call
`evaluator_get_evidence_summary` and see the same shape.

## Common fields

Every line has:

| Field | Type | Notes |
|---|---|---|
| `ts` | `string` | UTC ISO 8601 second resolution |
| `runId` | `string` | Per-process run id (`run-<8-hex>`) |
| `kind` | `string` | The discriminator — see below |

Tokens (any string matching `sbc_team_*`, `Bearer ...`, `X-Team-Token: ...`)
are redacted to `[REDACTED]` before write. See `orchestrator/evidence.py`.

## Kinds

### `mcp_call`
```json
{"kind":"mcp_call","tool":"square_create_order","args":{"items":[...]},
 "ok":true,"resultSummary":{"orderId":"ord_..."}}
```

### `event`
A scenario-emitted event consumed from `world_next_event`.
```json
{"kind":"event","source":"whatsapp","type":"inbound_message",
 "payload":{"from":"+128...","message":"..."}}
```

### `decision`
Captured when an agent or handler picks an action with a rationale.
```json
{"kind":"decision","agent":"sales","action":"create_order",
 "rationale":"customer confirmed Medovik medium for Saturday pickup"}
```

### `owner_msg`
```json
{"kind":"owner_msg","subkind":"approval_request",
 "summary":"Allergy promise requested","approvalId":"a1b2c3d4",
 "context":{"channel":"whatsapp","sender":"+128..."}}
```

Variants of `subkind`:
- `notify` — informational message
- `approval_request` — awaiting verdict
- `approval_resolution` — `verdict: "approve" | "reject"`, `auto: bool`

### `claude_run`
Outcome of a `claude -p` subprocess invocation.
```json
{"kind":"claude_run","label":"whatsapp_inbound","ok":true,
 "project":"agents/sales","promptPreview":"...","responsePreview":"..."}
```

### `dispatch_drop`, `dispatch_error`
Routing failures.

### `scenario_summary`
Final tick of a run.
```json
{"kind":"scenario_summary","summary":{"deliveredEvents":42,...},"processed":42}
```

### `dry_run`
Sentinel emitted in `--dry-run` mode so we have a non-empty file even on a
no-op.

## How judges read this

`evaluator_get_evidence_summary` (server-side) reflects the team's MCP audit
log; this file is the **client-side** parallel. Together they let the
seven scoring agents reconstruct exactly what happened.

If you add a new evidence kind, document it here and add a short test in
`orchestrator/tests/test_evidence.py`.
