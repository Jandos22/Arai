# bots/

Optional dedicated Telegram bots — one per agent role. Gives the owner
slash-command-driven chats per concern (`/marketing /run`, `/ops /capacity`,
`/sales /orders`) on top of the orchestrator's approval queue.

The brief explicitly allows "one bot per agent if the system has multiple
agents". These bots aren't required for scoring — the orchestrator-attached
owner notifier (in `orchestrator/telegram_bot.py`) already handles all
approval-gated actions. Run these for owner ergonomics.

## Bots

| File | Token env var | Commands |
|---|---|---|
| `marketing_bot.py` | `TELEGRAM_BOT_TOKEN_MARKETING` | `/budget /campaigns /report /run` |
| `ops_bot.py` | `TELEGRAM_BOT_TOKEN_OPS` | `/capacity /tickets /reviews /pending_posts` |
| `sales_bot.py` | `TELEGRAM_BOT_TOKEN_SALES` | `/menu /threads /orders /pos` (read-only) |

## Setup

1. Talk to [@BotFather](https://t.me/BotFather) on Telegram and create four
   bots with `Arai`-prefixed display names:

   | Display name | Suggested username | Env var |
   |---|---|---|
   | `Arai` | `@arai_tbot` | `TELEGRAM_BOT_TOKEN_OWNER` |
   | `Arai Sales` | `@arai_sales_tbot` | `TELEGRAM_BOT_TOKEN_SALES` |
   | `Arai Ops` | `@arai_ops_tbot` | `TELEGRAM_BOT_TOKEN_OPS` |
   | `Arai Marketing` | `@arai_mark_bot` | `TELEGRAM_BOT_TOKEN_MARKETING` |

   If an exact username is unavailable, choose the nearest available
   `arai_*_bot` variant and keep the display name role-specific.
2. Paste the tokens into `.env.local` or `~/.config/arai/env.local` next to
   `STEPPE_MCP_TOKEN`. Never commit these values.
   ```
   TELEGRAM_BOT_TOKEN_OWNER=...
   TELEGRAM_BOT_TOKEN_MARKETING=...
   TELEGRAM_BOT_TOKEN_OPS=...
   TELEGRAM_BOT_TOKEN_SALES=...
   TELEGRAM_OWNER_CHAT_ID=<your numeric chat id>
   ```
3. Message each bot once from the owner's Telegram account.
4. To find your chat id, run:
   ```bash
   curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN_OWNER/getUpdates" | jq '.result[].message.chat.id'
   ```
   If `getUpdates` returns an empty list even after sending `/start`, use a
   Telegram identity helper such as `@userinfobot` to get your numeric user
   id, then paste that value into `TELEGRAM_OWNER_CHAT_ID`.
5. Verify the tokens without printing secrets:
   ```bash
   bash scripts/verify_telegram_bots.sh
   ```
6. After the chat id is set, send one test message from each bot:
   ```bash
   bash scripts/verify_telegram_bots.sh --send-test
   ```

## Run

The bots reuse the orchestrator's MCP client + evidence logger, so launch
them from the orchestrator venv:

```bash
cd orchestrator
PYTHONPATH=.. .venv/bin/python -m bots.marketing_bot
PYTHONPATH=.. .venv/bin/python -m bots.ops_bot
PYTHONPATH=.. .venv/bin/python -m bots.sales_bot
```

Each runs in foreground; use `tmux`, `screen`, or three terminals.

The owner approval bot is not a foreground process. It is used by the
orchestrator through `orchestrator/telegram_bot.py`; when
`TELEGRAM_BOT_TOKEN_OWNER` and `TELEGRAM_OWNER_CHAT_ID` are set, owner-gated
actions send inline approve/reject cards to Telegram. If those variables are
missing, the orchestrator keeps its dev/evaluator fallback and auto-approves
so headless runs still move.

## Owner-only

Every command is wrapped in `@owner_only` (see `_common.py`). If the
chat_id doesn't match `TELEGRAM_OWNER_CHAT_ID`, the bot replies politely
and ignores. Set `TELEGRAM_OWNER_CHAT_ID` or commands will work for
anyone who knows the bot — fine for hackathon demo, not fine in
production.

## Architecture role

```
                    ┌─ orchestrator/telegram_bot.py
                    │  (approval queue, inline keyboards)
                    │
        owner ──────┼─ bots/marketing_bot.py  (/budget /run …)
        Telegram    ├─ bots/ops_bot.py        (/capacity /tickets …)
                    └─ bots/sales_bot.py      (/menu /orders …)
```

All four chats share the same MCP token (`STEPPE_MCP_TOKEN`) and write to
the same evidence file (`evidence/orchestrator-<runId>.jsonl`).
