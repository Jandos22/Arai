"""Deterministic growth bonus scoring tests."""
from __future__ import annotations

from orchestrator.growth import build_pickup_follow_up_message, score_whatsapp_lead


def test_scores_hot_custom_whatsapp_lead_with_square_repeat_evidence():
    score = score_whatsapp_lead(
        {
            "from": "+12815550123",
            "message": "I want a custom birthday cake for pickup tomorrow afternoon",
        },
        {"orders": [{"id": "sq_order_1", "customerPhone": "+1 281 555 0123"}]},
    )

    assert score.score == 90
    assert score.segment == "hot"
    assert score.route == "owner_review"
    assert score.follow_up_after_minutes == 15
    assert "repeat-customer Square evidence" in score.reasons


def test_scores_low_inquiry_without_follow_up():
    score = score_whatsapp_lead({"message": "What time do you close?"}, {"orders": []})

    assert score.score == 10
    assert score.segment == "low"
    assert score.route == "standard_reply"
    assert score.follow_up_after_minutes is None


def test_pickup_follow_up_message_uses_square_order_hint():
    message = build_pickup_follow_up_message(
        {"pickupAt": "today at 4 PM"},
        {"orders": [{"id": "sq_order_123"}]},
    )

    assert "sq_order_123" in message
    assert "today at 4 PM" in message
