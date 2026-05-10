# Production readiness — bonus map (+5)

> Hackathon brief §9 awards up to **+5 bonus points** for production
> readiness: clean deploy, mobile performance, admin/operator view, audit
> trail, failure handling, safe owner handoff. This file points the
> evaluator at the concrete artifact behind each criterion. Nothing here
> is a claim — every line links to code, tests, or evidence.

| Criterion | Where it lives |
|---|---|
| Clean deploy | [`docs/PRODUCTION-PATH.md`](PRODUCTION-PATH.md) — tool-by-tool sandbox→prod swap, credential lifecycle, lead times |
| Mobile performance | [`docs/MOBILE-PERFORMANCE.md`](MOBILE-PERFORMANCE.md) — Lighthouse 91/95/100/92 mobile, evidence under `evidence/lighthouse-mobile-home.report.{html,json}` |
| Admin/operator view | `bots/ops_bot.py` — Telegram-only owner UI: `/status`, `/audit`, `/pending`, `/capacity`, `/tickets`, `/reviews` |
| Audit trail | `orchestrator/evidence.py` — append-only JSONL with token redaction; one file per run; helpers `latest_evidence_file`, `unresolved_approval_requests` |
| Failure handling | `orchestrator/dispatcher.py` (handler isolation) + `orchestrator/mcp_client.py` (transient 5xx retry) |
| Safe owner handoff | `orchestrator/telegram_bot.py` — inline approve/reject keyboards, dev-mode no-op when token missing, evidence row on every approval lifecycle event |

## 1. Clean deploy

`docs/PRODUCTION-PATH.md` walks the future engineer from "open the
sandbox" to "go live on real Square + WhatsApp + Meta Ads + GBP."
Highlights:

- the agent layer never changes between sandbox and prod — only the MCP
  endpoint URL and adapter behind it;
- per-tool mapping table with auth model and lead time (the WA Business
  verification 3–5 day window is called out so it is the first thing
  ordered);
- credentials live in `~/.config/arai/env.local` (or repo `.env.local`),
  loaded via `scripts/load_env.sh`. `.env.example` ships placeholders
  only;
- pre-commit hook in `scripts/git-hooks/pre-commit` blocks accidental
  secret commits.

## 2. Mobile performance

The website is the customer-facing surface, so we measured it. Lighthouse
mobile against a production Next.js build:

| Performance | A11y | Best-practices | SEO |
|---:|---:|---:|---:|
| 91 | 95 | 100 | 92 |

Numbers, command, and HTML/JSON artifacts are reproducible from
`docs/MOBILE-PERFORMANCE.md`.

## 3. Admin/operator view

Owner UI is **Telegram-only** by hard rule. The ops bot now exposes a
single-screen health view and audit replay so the owner never has to
SSH or read JSONL by hand:

- `/status` — `health_snapshot()` aggregates the latest evidence run
  into one block: rows processed, MCP call count + errors, handler
  errors, last error, last decision, count of unresolved approvals.
- `/audit <approvalId>` — full chain of evidence rows for a single
  approval, so the owner can replay why a decision happened.
- `/pending`, `/capacity`, `/tickets`, `/reviews`, `/pending_posts` —
  unchanged, still the day-to-day operator surface.

Aggregator: `orchestrator/health.py`. Tests:
`orchestrator/tests/test_health.py`.

## 4. Audit trail

Every orchestrator run writes a single append-only JSONL file at
`evidence/orchestrator-run-<id>.jsonl`. Schema in
`docs/EVIDENCE-SCHEMA.md`. Properties that matter for an audit trail:

- one row per side-effect: `mcp_call`, `event`, `decision`,
  `owner_msg`, `dispatch_drop`, `handler_error`;
- token redaction at write time (`_TOKEN_PATTERN` in
  `orchestrator/evidence.py`) — anything that looks like
  `sbc_team_…`, `Bearer …`, or `X-Team-Token: …` is replaced with
  `[REDACTED]` before the bytes hit disk;
- `runId` stamped on every row, so cross-run drift is impossible;
- read helpers (`latest_evidence_file`, `read_jsonl_tail`,
  `unresolved_approval_requests`, `audit_trail`) keep the operator UI
  reading the same source the evaluator reads.

## 5. Failure handling

Two layers, both backed by tests.

### Handler isolation in the dispatcher

A single buggy handler can no longer kill the scenario loop. The
dispatcher now wraps every `handler(event, ctx)` call:

- exceptions are caught at the boundary;
- a `handler_error` row is written to evidence with the exception type,
  message, traceback (capped at 8 frames), event, and routing key;
- if a Telegram notifier is wired, the owner gets a one-line
  `⚠️ Handler error: …` ping so it never goes unnoticed;
- the scenario loop continues with the next event.

Code: `orchestrator/dispatcher.py`. Tests:
`test_handler_exception_is_logged_and_swallowed`,
`test_handler_error_notifies_telegram_when_present`.

### Transient retry on the MCP client

`MCPClient._rpc` retries on transport errors and HTTP 5xx with
exponential backoff (0.4s, 0.8s + jitter, max 2 retries by default).
4xx and JSON-RPC error responses are NOT retried — they are surfaced
immediately.

Code: `orchestrator/mcp_client.py`. Tests:
`test_transient_5xx_retries_then_succeeds`,
`test_transient_5xx_gives_up_after_retries`.

## 6. Safe owner handoff

`orchestrator/telegram_bot.py` is the only place outside-world
side-effects can be approved. Properties:

- approval requests carry an `approvalId` that threads through evidence
  (`approval_request` → `approval_resolution`);
- inline approve/reject keyboard — no free-form text required from the
  owner;
- when `TELEGRAM_BOT_TOKEN_OWNER` / `TELEGRAM_OWNER_CHAT_ID` are unset
  the notifier silently no-ops in dev/CI but still writes evidence rows,
  so a fresh-clone evaluator run never crashes for missing creds;
- `/audit <id>` in the ops bot replays the full approval chain for
  forensic review.

## How to verify

From a fresh clone:

```bash
source scripts/load_env.sh && arai_load_env "$PWD"
cd orchestrator && uv run python -m pytest tests/ -q
```

Spot-check the new surface:

```bash
# Health snapshot from latest evidence run (no Telegram needed)
python -c "from orchestrator.health import health_snapshot, format_health; \
  import json; s = health_snapshot(); print(format_health(s))"
```
