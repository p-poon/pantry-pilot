"""Streamlit demo for PantryPilot AP2 flows."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.agent import AgentService, MerchantVerifier
from services.mandate import MandateService, default_validity_window

st.set_page_config(page_title="PantryPilot AP2 Demo", layout="wide")

if "mandate_service" not in st.session_state:
    st.session_state.mandate_service = MandateService()
if "agent_service" not in st.session_state:
    st.session_state.agent_service = AgentService()
if "last_signed_payload" not in st.session_state:
    st.session_state.last_signed_payload = None

mandate_service: MandateService = st.session_state.mandate_service
agent_service: AgentService = st.session_state.agent_service

st.title("PantryPilot — Agentic Meal-Planning & AP2 Checkout")
st.caption(
    "Simulated experience for mandate creation, agent cart building, merchant verification, and AP2 signing."
)

st.header("1. Capture User Mandate")
with st.form("mandate_form"):
    subject = st.text_input("User DID", "did:user:ava-tan")
    merchants_allowed = st.multiselect(
        "Allowed merchants",
        ["redmart.com", "fairprice.com.sg", "amazon.sg"],
        default=["redmart.com", "fairprice.com.sg"],
        help="Aligns to PRD §5.1 merchants_allowed claim.",
    )
    spend_amount = st.number_input(
        "Spend cap (SGD)",
        min_value=10.0,
        max_value=500.0,
        value=180.0,
        step=10.0,
    )
    period = st.selectbox("Cap period", ["WEEK"], index=0)
    validity_weeks = st.slider("Validity duration (weeks)", min_value=1, max_value=12, value=8)
    days_of_week = st.multiselect(
        "Active days",
        ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
        default=["FRI", "SAT", "SUN"],
    )
    categories_allowed = st.multiselect(
        "Categories allowed",
        ["Groceries", "Fresh Produce", "Ready Meals", "Household"],
        default=["Groceries", "Fresh Produce"],
    )
    categories_blocked = st.multiselect(
        "Categories blocked",
        ["Alcohol", "Tobacco", "Supplements"],
        default=["Alcohol"],
        help="No-alcohol policy from PRD §4.1 & §5.1.",
    )
    payment_rails = st.multiselect(
        "Payment rails",
        ["card", "bank"],
        default=["card"],
    )
    policy_notes = st.text_area(
        "Policy notes",
        "No alcohol. Agent purchases only within family meal plan scope.",
    )

    submitted = st.form_submit_button("Generate Mandate")
    if submitted:
        valid_from, valid_until = default_validity_window(duration_weeks=validity_weeks)
        mandate = mandate_service.issue_mandate(
            subject=subject,
            agent_id=agent_service.agent_id,
            merchants_allowed=[f"*.{m}" if "." in m else m for m in merchants_allowed],
            categories_allowed=categories_allowed,
            categories_blocked=categories_blocked,
            spend_amount=spend_amount,
            currency="SGD",
            period=period,
            valid_from=valid_from,
            valid_until=valid_until,
            days_of_week=days_of_week,
            payment_rails_allowed=payment_rails,
            policy_notes=policy_notes,
        )
        st.session_state.last_signed_payload = None
        st.success(f"Mandate {mandate.mandate_id} created and signed.")

current_mandate = mandate_service.current_mandate()
if current_mandate:
    st.subheader("Mandate Summary")
    st.table(pd.DataFrame([current_mandate.as_summary()]).T.rename(columns={0: "Details"}))
else:
    st.info("Create a mandate to unlock agent simulation flows.")

st.divider()

if current_mandate:
    st.header("2. Agent Meal Planning & Cart Assembly")
    meal_plan = agent_service.create_meal_plan()
    st.write(
        f"**Week of {meal_plan.week_of.date()}** — PantryPilot proposes the following meal rotation:"
    )
    st.write("\n".join(f"• {meal}" for meal in meal_plan.meals))

    cart = agent_service.build_cart(current_mandate)
    cart_rows = [
        {
            "Item": item.name,
            "Merchant": item.merchant,
            "Quantity": item.quantity,
            "Line total (SGD)": item.total,
        }
        for item in cart
    ]
    st.subheader("Cart Proposal")
    st.dataframe(pd.DataFrame(cart_rows))
    cart_total = agent_service.cart_total(cart)
    st.metric(
        label="Cart total vs mandate cap",
        value=f"SGD {cart_total:.2f}",
        delta=f"Remaining cap: SGD {current_mandate.spend_cap.remaining:.2f}",
    )

    payload = agent_service.generate_checkout_payload(cart, current_mandate)
    st.session_state.last_signed_payload = payload

    st.divider()
    st.header("3. AP2 Signing Envelope")
    st.caption("Agent attaches mandate VC and signs checkout intent per PRD §5.2.")
    st.json(payload)

    st.divider()
    st.header("4. Merchant Verification Snapshot")
    verifier = MerchantVerifier()
    verification = verifier.verify_payload(payload, current_mandate)
    st.json(verification)

    if st.button("Simulate merchant confirm & debit cap"):
        if cart_total <= current_mandate.spend_cap.remaining:
            mandate_service.record_spend(cart_total)
            st.success("Cap ledger updated — mandate remains active.")
        else:
            st.warning("Cart exceeds remaining cap. Trigger user step-up per PRD §5.3.")
else:
    st.stop()
