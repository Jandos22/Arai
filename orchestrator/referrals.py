"""Referral codes — issue, store, detect redemption.

Lightweight JSON-backed store (mirrors ``customers.py``). One code per
customer identifier, deterministic and idempotent: re-issuing for the
same identifier returns the existing code.

Code shape: ``HAPPY-XXXX`` where ``XXXX`` is 4 uppercase hex chars
seeded from a SHA-1 of the identifier. Stable, easy to type, easy to
log-grep.

Redemption is detected by scanning inbound message bodies for the
``HAPPY-`` prefix and matching against issued codes. We only log
``referral_redeemed`` evidence; sandbox does not have a discount engine,
so the owner-side workflow is "honour the credit at pickup".
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CODE_PATTERN = re.compile(r"\bHAPPY-([A-F0-9]{4})\b", re.IGNORECASE)


def code_for(identifier: str) -> str:
    """Stable 4-hex-char referral code for a given customer identifier."""
    if not identifier:
        raise ValueError("identifier required")
    digest = hashlib.sha1(identifier.encode("utf-8")).hexdigest().upper()
    return f"HAPPY-{digest[:4]}"


def detect_codes(body: str) -> list[str]:
    """Return any normalized referral codes found in a message body."""
    if not body:
        return []
    return [f"HAPPY-{m.group(1).upper()}" for m in CODE_PATTERN.finditer(body)]


@dataclass
class ReferralStore:
    """File-backed JSON store for issued codes + redemption attempts."""

    path: Path = field(default_factory=lambda: Path("evidence/referrals.json"))
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"issued": {}, "redemptions": []}), encoding="utf-8")

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except (ValueError, OSError):
            data = {}
        data.setdefault("issued", {})
        data.setdefault("redemptions", [])
        return data

    def _save(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)

    def issue(self, identifier: str, *, channel: str = "whatsapp") -> dict[str, Any]:
        """Issue (or re-fetch) the stable code for ``identifier``."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        code = code_for(identifier)
        with self._lock:
            data = self._load()
            row = data["issued"].get(identifier)
            if row:
                return row
            row = {
                "identifier": identifier,
                "code": code,
                "channel": channel,
                "issued_at": now,
            }
            data["issued"][identifier] = row
            self._save(data)
            return row

    def redeem(self, *, code: str, redeemer: str, channel: str) -> dict[str, Any] | None:
        """Record a redemption attempt. Returns the issuer row if matched."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            data = self._load()
            issuer = next(
                (row for row in data["issued"].values() if row.get("code") == code),
                None,
            )
            entry = {
                "code": code,
                "redeemer": redeemer,
                "channel": channel,
                "ts": now,
                "matched": bool(issuer),
                "issuer": issuer.get("identifier") if issuer else None,
            }
            data["redemptions"].append(entry)
            self._save(data)
            return issuer


def referral_pitch(code: str) -> str:
    """One-line referral pitch for use inside follow-up messages."""
    return (
        f"Share code {code} with a friend — they get $5 off their first cake "
        f"and we credit $5 to your next order at pickup."
    )
