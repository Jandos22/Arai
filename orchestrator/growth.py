"""Growth bonus helpers: lead scoring and WhatsApp follow-up.

The scoring is deliberately deterministic. Agents can still reason in prose,
but the orchestrator writes a repeatable score row that judges can inspect.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ORDER_TERMS = ("order", "buy", "pickup", "delivery", "reserve", "need", "want", "get")
HIGH_VALUE_TERMS = (
    "custom",
    "birthday",
    "office",
    "corporate",
    "wedding",
    "catering",
    "box",
    "dozen",
)
URGENT_TERMS = ("today", "tomorrow", "asap", "tonight", "morning", "afternoon")
RISK_TERMS = ("allergy", "allergic", "refund", "sick", "ill", "complaint", "not fresh")


@dataclass(frozen=True)
class LeadScore:
    score: int
    segment: str
    route: str
    follow_up_after_minutes: int | None
    reasons: list[str]


def score_whatsapp_lead(payload: dict[str, Any], recent_orders: Any = None) -> LeadScore:
    """Score an inbound WhatsApp lead from message content and Square evidence."""
    body = str(payload.get("message") or payload.get("text") or "").lower()
    score = 10
    reasons: list[str] = ["whatsapp inbound"]

    if _contains_any(body, ORDER_TERMS):
        score += 25
        reasons.append("order intent")
    if _contains_any(body, HIGH_VALUE_TERMS):
        score += 25
        reasons.append("high-value occasion or bulk signal")
    if _contains_any(body, URGENT_TERMS):
        score += 15
        reasons.append("time-sensitive request")
    if _contains_any(body, RISK_TERMS):
        score += 10
        reasons.append("owner-risk language")
    if _has_repeat_customer_evidence(payload, recent_orders):
        score += 15
        reasons.append("repeat-customer Square evidence")

    score = min(score, 100)
    if score >= 75:
        return LeadScore(score, "hot", "owner_review", 15, reasons)
    if score >= 50:
        return LeadScore(score, "warm", "whatsapp_follow_up", 60, reasons)
    return LeadScore(score, "low", "standard_reply", None, reasons)


def build_pickup_follow_up_message(payload: dict[str, Any], recent_orders: Any = None) -> str:
    """Return a short customer-safe reminder grounded in the current order view."""
    order_hint = _latest_order_hint(recent_orders)
    pickup = payload.get("pickupAt") or payload.get("pickupWindow") or payload.get("pickup")
    if order_hint and pickup:
        return (
            f"Hi! Quick Happy Cake reminder: your order {order_hint} is on our pickup list "
            f"for {pickup}. Reply here if anything changes."
        )
    if order_hint:
        return (
            f"Hi! Quick Happy Cake reminder: your order {order_hint} is on our pickup list. "
            "Reply here if anything changes."
        )
    if pickup:
        return (
            f"Hi! Quick Happy Cake reminder: we have your pickup noted for {pickup}. "
            "Reply here if anything changes."
        )
    return "Hi! Quick Happy Cake reminder: we have your order on our pickup list. Reply here if anything changes."


def _contains_any(body: str, terms: tuple[str, ...]) -> bool:
    return any(term in body for term in terms)


def _has_repeat_customer_evidence(payload: dict[str, Any], recent_orders: Any) -> bool:
    sender = str(payload.get("from") or payload.get("phone") or "")
    if not sender:
        return False
    for order in _iter_orders(recent_orders):
        customer_phone = str(order.get("phone") or order.get("customerPhone") or order.get("customer", ""))
        if sender[-4:] and sender[-4:] in customer_phone:
            return True
    return False


def _latest_order_hint(recent_orders: Any) -> str | None:
    for order in _iter_orders(recent_orders):
        return str(order.get("id") or order.get("orderId") or order.get("name") or "").strip() or None
    return None


def _iter_orders(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("orders", "recentOrders", "items", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return [value]
    return []
