"""Regression tests for the mock AgentService cart building logic."""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.agent import AgentService
from services.mandate import MandateService, default_validity_window


def test_default_mandate_produces_cart_items() -> None:
    agent_service = AgentService()
    mandate_service = MandateService()
    valid_from, valid_until = default_validity_window()

    mandate = mandate_service.issue_mandate(
        subject="did:user:ava-tan",
        agent_id=agent_service.agent_id,
        merchants_allowed=["*.redmart.com", "*.fairprice.com.sg"],
        categories_allowed=["Groceries", "Fresh Produce"],
        categories_blocked=["Alcohol"],
        spend_amount=180.0,
        currency="SGD",
        period="WEEK",
        valid_from=valid_from,
        valid_until=valid_until,
        days_of_week=["FRI", "SAT", "SUN"],
        payment_rails_allowed=["card"],
        policy_notes="No alcohol. Agent purchases only within family meal plan scope.",
    )

    cart = agent_service.build_cart(mandate)

    assert cart, "Expected at least one cart item for the default mandate"
