# Ops GMB Local-Presence Smoke Notes

Issue #19 expands Google Business simulator coverage beyond review
replies.

Run from repo root with `.env.local`, `ARAI_ENV_FILE`, or
`~/.config/arai/env.local` populated:

```sh
bash agents/ops/scripts/smoke_gmb_local.sh
```

Expected coverage:

- Metrics stage calls `gb_get_metrics` for recent local-search metrics
  and `gb_list_simulated_actions` for prior simulator actions.
- Post stage calls `gb_simulate_post` to record a proposed local Google
  Business post, then returns owner-gate JSON with
  `trigger="gmb_post_publish"` and `channel="gmb"`.
- The smoke appends a structured row to `evidence/ops-sample.jsonl`
  with `test="ops_gmb_local_presence_smoke"` plus the observed tools.

Known simulator gap:

- The live `gb_*` catalog has no Google Business Q&A read/write tool.
  Q&A events should report this gap and avoid fabricated tool calls.
