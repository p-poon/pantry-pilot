"""Utility classes and helpers for working with mock AP2 mandates."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import hashlib
import json
import random
import string
from typing import Dict, List, Optional


@dataclass
class MandateCap:
    amount: float
    currency: str
    period: str
    remaining: float
    last_reset: date

    def debit(self, value: float) -> None:
        if value > self.remaining:
            raise ValueError("Amount exceeds remaining cap")
        self.remaining = round(self.remaining - value, 2)

    def maybe_reset(self) -> None:
        """Reset the cap weekly based on the period."""
        if self.period.upper() != "WEEK":
            return
        today = date.today()
        # Reset on Mondays to simulate a weekly ledger.
        if today.weekday() == 0 and self.last_reset != today:
            self.remaining = self.amount
            self.last_reset = today


@dataclass
class Mandate:
    mandate_id: str
    subject: str
    agent_id: str
    merchants_allowed: List[str]
    categories_allowed: List[str]
    categories_blocked: List[str]
    spend_cap: MandateCap
    valid_from: datetime
    valid_until: datetime
    days_of_week: List[str]
    payment_rails_allowed: List[str]
    policy_notes: str
    signature: str
    payload: Dict[str, object] = field(default_factory=dict)

    def as_summary(self) -> Dict[str, object]:
        return {
            "Mandate ID": self.mandate_id,
            "Subject": self.subject,
            "Agent": self.agent_id,
            "Scope": ", ".join(self.categories_allowed) or "All",
            "Cap": f"{self.spend_cap.currency} {self.spend_cap.remaining:.2f}/{self.spend_cap.amount:.2f} {self.spend_cap.period.lower()}",
            "Validity": f"{self.valid_from.date()} → {self.valid_until.date()}",
            "Active Days": ", ".join(self.days_of_week),
            "Rails": ", ".join(self.payment_rails_allowed),
            "Policy": self.policy_notes,
            "Signature": self.signature,
        }


class MandateService:
    """Simplified in-memory mandate registry for the Streamlit demo."""

    def __init__(self) -> None:
        self._mandate: Optional[Mandate] = None

    @staticmethod
    def _generate_mandate_id() -> str:
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"M-{suffix}"

    @staticmethod
    def _hash_payload(payload: Dict[str, object]) -> str:
        payload_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_json.encode()).hexdigest()

    def issue_mandate(
        self,
        *,
        subject: str,
        agent_id: str,
        merchants_allowed: List[str],
        categories_allowed: List[str],
        categories_blocked: List[str],
        spend_amount: float,
        currency: str,
        period: str,
        valid_from: datetime,
        valid_until: datetime,
        days_of_week: List[str],
        payment_rails_allowed: List[str],
        policy_notes: str,
    ) -> Mandate:
        mandate_id = self._generate_mandate_id()
        payload = {
            "subject": subject,
            "agent_id": agent_id,
            "merchants_allowed": merchants_allowed,
            "categories_allowed": categories_allowed,
            "categories_blocked": categories_blocked,
            "spend_cap": {
                "amount": spend_amount,
                "currency": currency,
                "period": period,
            },
            "valid_from": valid_from.isoformat(),
            "valid_until": valid_until.isoformat(),
            "days_of_week": days_of_week,
            "payment_rails_allowed": payment_rails_allowed,
            "policy": policy_notes,
        }
        signature = self._hash_payload(payload)
        mandate = Mandate(
            mandate_id=mandate_id,
            subject=subject,
            agent_id=agent_id,
            merchants_allowed=merchants_allowed,
            categories_allowed=categories_allowed,
            categories_blocked=categories_blocked,
            spend_cap=MandateCap(
                amount=spend_amount,
                currency=currency,
                period=period,
                remaining=spend_amount,
                last_reset=date.today(),
            ),
            valid_from=valid_from,
            valid_until=valid_until,
            days_of_week=days_of_week,
            payment_rails_allowed=payment_rails_allowed,
            policy_notes=policy_notes,
            signature=signature,
            payload=payload,
        )
        self._mandate = mandate
        return mandate

    def current_mandate(self) -> Optional[Mandate]:
        if self._mandate:
            self._mandate.spend_cap.maybe_reset()
        return self._mandate

    def record_spend(self, value: float) -> None:
        if not self._mandate:
            raise RuntimeError("No mandate issued")
        self._mandate.spend_cap.debit(value)


def default_validity_window(duration_weeks: int = 8) -> tuple[datetime, datetime]:
    today = datetime.now()
    valid_from = datetime.combine(today.date(), time(hour=0))
    valid_until = valid_from + timedelta(weeks=duration_weeks) - timedelta(seconds=1)
    return valid_from, valid_until
