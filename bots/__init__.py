"""bots package — dedicated per-agent Telegram bot UIs.

The orchestrator already owns the *approval queue* (inline keyboards via
``orchestrator.telegram_bot.TelegramNotifier``). These bots are the
*command-driven* surfaces the brief mentions ("one bot per agent"):

- ``marketing_bot`` — /budget /campaigns /report /run
- ``ops_bot`` — /capacity /tickets /reviews /pending_posts
- ``sales_bot`` — /menu /threads /orders /pos (read-only)

All three are optional. The system works without any of them; they add
owner-side ergonomics.
"""
