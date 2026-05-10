"""Unit tests for the referrals helper."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.referrals import (
    ReferralStore,
    code_for,
    detect_codes,
    referral_pitch,
)


def test_code_for_is_stable_across_calls():
    a = code_for("+12815550123")
    b = code_for("+12815550123")
    assert a == b
    assert a.startswith("HAPPY-")
    assert len(a) == len("HAPPY-XXXX")


def test_code_for_differs_per_identifier():
    assert code_for("+12815550123") != code_for("+12815550199")


def test_code_for_requires_identifier():
    with pytest.raises(ValueError):
        code_for("")


def test_detect_codes_normalizes_case_and_finds_inline():
    code = code_for("alice@example.com")
    assert detect_codes(f"hi please apply {code.lower()} thanks") == [code]


def test_detect_codes_returns_empty_when_absent():
    assert detect_codes("just a normal message") == []
    assert detect_codes("") == []


def test_referral_pitch_includes_code():
    code = "HAPPY-AB12"
    assert code in referral_pitch(code)


def test_issue_is_idempotent_per_identifier(tmp_path: Path):
    store = ReferralStore(path=tmp_path / "referrals.json")
    first = store.issue("+12815550123")
    second = store.issue("+12815550123")
    assert first == second
    on_disk = json.loads((tmp_path / "referrals.json").read_text())
    assert list(on_disk["issued"].keys()) == ["+12815550123"]


def test_redeem_matches_issued_code(tmp_path: Path):
    store = ReferralStore(path=tmp_path / "referrals.json")
    issued = store.issue("+12815550123")
    issuer = store.redeem(code=issued["code"], redeemer="+12815550199", channel="whatsapp")
    assert issuer is not None
    assert issuer["identifier"] == "+12815550123"
    on_disk = json.loads((tmp_path / "referrals.json").read_text())
    assert len(on_disk["redemptions"]) == 1
    assert on_disk["redemptions"][0]["matched"] is True


def test_redeem_unknown_code_records_unmatched(tmp_path: Path):
    store = ReferralStore(path=tmp_path / "referrals.json")
    issuer = store.redeem(code="HAPPY-FFFF", redeemer="+12815550199", channel="whatsapp")
    assert issuer is None
    on_disk = json.loads((tmp_path / "referrals.json").read_text())
    assert on_disk["redemptions"][0]["matched"] is False
