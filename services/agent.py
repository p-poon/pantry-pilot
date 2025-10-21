"""Simulated PantryPilot agent behaviours for the Streamlit demo."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Dict, List

from .mandate import Mandate


@dataclass
class MealPlan:
    week_of: datetime
    meals: List[str]


@dataclass
class CartItem:
    name: str
    merchant: str
    quantity: int
    price: float

    @property
    def total(self) -> float:
        return round(self.quantity * self.price, 2)


class AgentService:
    agent_id = "did:agent:pantrypilot:123"

    def create_meal_plan(self) -> MealPlan:
        week_start = datetime.now()
        meals = [
            "Mon: Teriyaki Salmon Bowl",
            "Tue: Veggie Stir-fry",
            "Wed: Chicken Pho",
            "Thu: Beyond Burger Night",
            "Fri: Family Hotpot",
            "Sat: Bento Picnic",
            "Sun: Laksa Sunday",
        ]
        return MealPlan(week_of=week_start, meals=meals)

    def build_cart(self, mandate: Mandate) -> List[CartItem]:
        base_cart = [
            CartItem("Salmon Fillets", "RedMart", 2, 12.50),
            CartItem("Veggie Stir-fry Kit", "FairPrice", 1, 8.90),
            CartItem("Chicken Broth", "RedMart", 3, 4.25),
            CartItem("Plant-based Patties", "FairPrice", 1, 9.80),
            CartItem("Hotpot Set", "RedMart", 1, 28.40),
            CartItem("Laksa Paste", "FairPrice", 2, 3.10),
        ]
        allowed_tokens: set[str] = set()
        for merchant in mandate.merchants_allowed:
            token = self._merchant_token(merchant)
            if token:
                allowed_tokens.add(token)
        filtered_cart = [
            item
            for item in base_cart
            if self._merchant_token(item.merchant) in allowed_tokens
        ]
        return filtered_cart

    def cart_total(self, cart: List[CartItem]) -> float:
        return round(sum(item.total for item in cart), 2)

    def generate_checkout_payload(self, cart: List[CartItem], mandate: Mandate) -> Dict[str, object]:
        items_payload = [
            {
                "name": item.name,
                "merchant": item.merchant,
                "quantity": item.quantity,
                "total": item.total,
            }
            for item in cart
        ]
        payload = {
            "agent_id": self.agent_id,
            "mandate_id": mandate.mandate_id,
            "mandate_signature": mandate.signature,
            "cart_total": self.cart_total(cart),
            "items": items_payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        payload["agent_signature"] = self._sign_payload(payload)
        return payload

    def _sign_payload(self, payload: Dict[str, object]) -> str:
        payload_json = json.dumps({k: v for k, v in payload.items() if k != "agent_signature"}, sort_keys=True)
        return hashlib.sha256(payload_json.encode()).hexdigest()

    @staticmethod
    def _merchant_token(merchant: str) -> str:
        """Normalize a merchant identifier to its core brand token."""
        cleaned = merchant.strip().lower()
        if cleaned.startswith("*."):
            cleaned = cleaned[2:]
        cleaned = cleaned.lstrip(".")
        return cleaned.split(".", 1)[0] if cleaned else ""


class MerchantVerifier:
    """Simple verifier to emulate merchant-side mandate validation logic."""

    @staticmethod
    def verify_payload(payload: Dict[str, object], mandate: Mandate) -> Dict[str, str]:
        cart_total = payload.get("cart_total", 0.0)
        remaining = mandate.spend_cap.remaining
        status = "Approved" if cart_total <= remaining else "Needs user step-up"
        expected_signature = hashlib.sha256(
            json.dumps(
                {k: v for k, v in payload.items() if k != "agent_signature"},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        signature_valid = expected_signature == payload.get("agent_signature")
        return {
            "Agent": payload.get("agent_id", "unknown"),
            "Mandate": mandate.mandate_id,
            "Signature": payload.get("mandate_signature", ""),
            "Agent Signature": payload.get("agent_signature", ""),
            "Signature Valid": "Yes" if signature_valid else "No",
            "Cart Total": f"{mandate.spend_cap.currency} {cart_total:.2f}",
            "Remaining Cap": f"{mandate.spend_cap.currency} {remaining:.2f}",
            "Decision": status,
        }
