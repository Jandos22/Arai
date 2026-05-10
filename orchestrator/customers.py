"""Customer profile store — JSON-backed, sandbox-only.

Drives the "extra mile" repeat-customer flow:

1. Every WhatsApp/Instagram inbound auto-upserts a profile keyed by phone or
   IG handle. We never ask the customer to "register" — we just remember.
2. On hydration, we reach into ``square_recent_orders`` to detect the
   customer's favorite SKU and last-N order summary.
3. When the customer next sends a greeting, the agent layer can call
   ``propose_reorder()`` to draft a one-tap reorder.

No real payment data lives here. We keep a sandbox ``payment_token`` field
(opaque string) so the storefront can demo "saved card" UX, but nothing
in this repo issues, validates, or charges a card. Real Square/Stripe
tokenization is wired up post-hackathon — see
``docs/PRODUCTION-PATH.md``.

Storage shape: one JSON file at ``evidence/customers.json``::

    {
      "+12815550123": {
        "id": "+12815550123",
        "channel_keys": {"whatsapp": "+12815550123", "instagram": "sam_h"},
        "name": "Sam",
        "delivery_address": "123 Main St, Sugar Land, TX",
        "payment_token": "sandbox_card_visa_4242",
        "favorite_product": {"sku": "medovik-medium", "count": 4},
        "last_orders": [
          {"id": "sq_order_1", "sku": "medovik-medium", "ts": "..."},
          ...
        ],
        "first_seen": "2026-04-30T...",
        "last_seen": "2026-05-10T..."
      },
      ...
    }
"""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

GREETING_PATTERN = re.compile(
    r"^\s*(hi|hey|hello|salem|salam|salaam|assalam|hola|good\s*(morning|afternoon|evening))[\s!.,?]*$",
    re.IGNORECASE,
)

REPEAT_THRESHOLD = 2  # need ≥ 2 same-SKU orders for a "favorite"
LAST_ORDERS_KEEP = 5


@dataclass
class CustomerStore:
    """File-backed JSON store. One lock per process — fine for our scale."""

    path: Path = field(default_factory=lambda: Path("evidence/customers.json"))
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    # --- low-level I/O --------------------------------------------------
    def _load(self) -> dict[str, dict[str, Any]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except (ValueError, OSError):
            return {}

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)

    # --- public API -----------------------------------------------------
    def get(self, identifier: str) -> dict[str, Any] | None:
        if not identifier:
            return None
        with self._lock:
            return self._load().get(identifier)

    def upsert_from_inbound(
        self,
        *,
        channel: str,
        identifier: str,
        name: str | None = None,
        recent_orders: Any = None,
    ) -> dict[str, Any]:
        """Create or update a profile from a channel inbound.

        ``recent_orders`` is the raw ``square_recent_orders`` result (list,
        dict, or None). We extract this customer's orders by phone match
        and refresh ``last_orders`` + ``favorite_product`` accordingly.
        """
        if not identifier:
            raise ValueError("identifier required")

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            data = self._load()
            profile = data.get(identifier) or {
                "id": identifier,
                "channel_keys": {},
                "first_seen": now,
            }
            profile["last_seen"] = now
            profile.setdefault("channel_keys", {})[channel] = identifier
            if name and not profile.get("name"):
                profile["name"] = name

            customer_orders = list(_orders_for_phone(recent_orders, identifier))
            if customer_orders:
                profile["last_orders"] = customer_orders[:LAST_ORDERS_KEEP]
                fav = _favorite_sku(customer_orders)
                if fav is not None:
                    profile["favorite_product"] = fav

            data[identifier] = profile
            self._save(data)
            return profile

    def attach_payment_token(self, identifier: str, token: str) -> None:
        """Sandbox-only. Never store real PAN/CVV here."""
        with self._lock:
            data = self._load()
            profile = data.setdefault(identifier, {"id": identifier})
            profile["payment_token"] = token
            self._save(data)

    def attach_delivery_address(self, identifier: str, address: str) -> None:
        with self._lock:
            data = self._load()
            profile = data.setdefault(identifier, {"id": identifier})
            profile["delivery_address"] = address
            self._save(data)

    def all_profiles(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return self._load()


# --- pure helpers (importable + testable without filesystem) ------------

def is_greeting(message: str) -> bool:
    """Match short greetings (hi / hello / salem) — first 30 chars only."""
    if not message:
        return False
    head = message.strip()[:60]
    return bool(GREETING_PATTERN.match(head))


def propose_reorder(profile: dict[str, Any]) -> dict[str, Any] | None:
    """Build a one-tap reorder proposal from a profile.

    Returns ``None`` if the profile doesn't have enough repeat-purchase
    signal (≥ ``REPEAT_THRESHOLD`` of the same SKU). Returning ``None`` is
    the signal to the handler layer "fall through to the normal greeting".
    """
    fav = profile.get("favorite_product") or {}
    count = int(fav.get("count") or 0)
    sku = fav.get("sku")
    if not sku or count < REPEAT_THRESHOLD:
        return None
    name = profile.get("name")
    salutation = f"Hi {name}!" if name else "Hi!"
    has_saved_payment = bool(profile.get("payment_token"))
    has_saved_address = bool(profile.get("delivery_address"))
    quick = "tap reply '1' to confirm" if has_saved_payment else "say 'yes' and we'll send a payment link"
    delivery_note = " We'll deliver to your saved address." if has_saved_address else ""
    return {
        "sku": sku,
        "count": count,
        "message": (
            f"{salutation} Welcome back to Happy Cake. Want your usual "
            f"{_friendly_sku(sku)}?{delivery_note} Just {quick}."
        ),
        "saved_payment": has_saved_payment,
        "saved_address": has_saved_address,
    }


def _friendly_sku(sku: str) -> str:
    return sku.replace("-", " ").replace("_", " ").strip().lower()


def _orders_for_phone(recent_orders: Any, phone: str) -> Iterable[dict[str, Any]]:
    """Yield dict orders attributable to ``phone`` from MCP recent_orders."""
    last4 = re.sub(r"\D", "", phone)[-4:] if phone else ""
    for order in _iter_orders(recent_orders):
        candidate = " ".join(
            str(order.get(k) or "")
            for k in ("phone", "customerPhone", "customer", "from")
        )
        order_last4 = re.sub(r"\D", "", candidate)[-4:]
        if last4 and order_last4 == last4:
            yield {
                "id": str(order.get("id") or order.get("orderId") or ""),
                "sku": _extract_sku(order),
                "ts": str(order.get("ts") or order.get("createdAt") or ""),
            }


def _favorite_sku(orders: list[dict[str, Any]]) -> dict[str, Any] | None:
    counts: dict[str, int] = {}
    for o in orders:
        sku = o.get("sku")
        if sku:
            counts[sku] = counts.get(sku, 0) + 1
    if not counts:
        return None
    sku, count = max(counts.items(), key=lambda kv: kv[1])
    return {"sku": sku, "count": count}


def _extract_sku(order: dict[str, Any]) -> str:
    """Best-effort extract a SKU from a Square-shaped order dict."""
    for key in ("sku", "variationId", "productId"):
        v = order.get(key)
        if isinstance(v, str) and v:
            return v
    items = order.get("items") or order.get("lineItems") or []
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict):
            for key in ("sku", "variationId", "productId", "name"):
                v = first.get(key)
                if isinstance(v, str) and v:
                    return v
    return ""


def _iter_orders(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
        return
    if isinstance(value, dict):
        for key in ("orders", "recentOrders", "items", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        yield item
                return
        yield value
