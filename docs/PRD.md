# Project Requirements Document (PRD)

**Project name:** PantryPilot — Agentic Meal-Planning & Grocery Checkout (AP2-aligned)
**Audience:** PM, Design, Frontend, Backend, Risk/Fraud, Legal/Compliance
**Primary markets:** Singapore (RedMart, FairPrice Online as reference merchants)
**Protocol reference:** Google AP2 (Agent Payments Protocol) — mandates as cryptographically signed, verifiable proof of a user’s instruction to pay; open, payment-agnostic rails. ([Google Cloud][1])

---

## 1) Problem & Goals

Families want AI agents to plan meals, compile carts across merchants, and **check out autonomously**—but merchants need to **verify the agent** and see **proof of user consent, spend limits, and authority**. AP2 introduces **Mandates** (signed instructions) to prove the user authorised a specific purchase under defined constraints. This project validates the UX and integration patterns for **capturing mandates**, **signalling “agent transaction” to merchants**, and **exposing limits/authority** to both sides. ([Google Cloud][1])

**Goals**

1. Ship a working reference app that:

   * Captures **user consent/mandates** per AP2 and stores them securely.
   * Surfaces **agent identity** + **agent transaction badge** to merchants.
   * Enforces & displays **spend limits** and **authority scope** to user and merchant.
2. Provide reusable **UI patterns** and **API contracts** aligned to AP2 for future integrations.
3. Demonstrate multi-rail readiness (card/bank today; crypto via AP2 extensions later). ([Google Cloud][1])

**Out of scope (v1)**

* Real money movement; we simulate merchant checkouts.
* Production KYC; we stub identity with plausible flows.

---

## 2) Personas

* **Ava (Parent/Admin):** sets weekly budget, approves agent purchases, defines which merchants are allowed.
* **Ben (Teen/Dependent):** can add items/requests; cannot approve payments beyond a pocket-money limit.
* **PantryPilot Agent:** plans meals, builds cart, negotiates substitutions, executes purchase under mandate.
* **Merchant Ops (FairPrice/RedMart role):** wants assurance this is a **trusted agent** with **valid mandate** and limits.

---

## 3) Key Use Cases & User Stories

### A. Create & manage mandates (User ↔ Agent)

* *As Ava*, I can **create a shopping mandate** authorizing PantryPilot to purchase groceries **up to S$180/week**, only from **FairPrice/RedMart**, **Friday–Sunday**, and with **no alcohol**.
* *As Ava*, I can **review & revoke** a mandate at any time.
* *As Ava*, I can **approve one-off overage** (e.g., S$30 extra) with a second factor.

**AP2 Mapping:** “Mandate” = a tamper-proof, **cryptographically signed instruction** that encodes scope, spend caps, validity window, and payment rails; used as the **foundational evidence for each transaction**. ([Google Cloud][1])

### B. Agent-assisted checkout (Agent ↔ Merchant)

* *As Merchant*, I see a **prominent “Agent Transaction” badge**, the **Agent ID**, and a **Mandate summary** (issuer, scope, expiry, spend cap used/remaining) before authorising fulfilment.
* *As Merchant*, I can **inspect** (but not exfiltrate) a **verifiable mandate envelope** and **validate** it against the AP2 spec. ([ap2-protocol.org][2])

### C. Spend-limit & authority UX

* *As Ava*, I see **current spend vs. mandate cap** by week, **remaining allowance**, and **pending agent carts** awaiting implicit/explicit approval.
* *As Merchant*, I see **authorised amount ≤ remaining cap**, and any **policy constraints** (e.g., “no alcohol”).

---

## 4) User Experience Requirements

### 4.1 Mandate creation flow (mobile-first)

1. **Choose Template:** “Weekly Groceries” pre-set.
2. **Scope & Limits:**

   * Merchants: RedMart, FairPrice (multi-select).
   * Budget: e.g., S$180/week; item caps (e.g., S$30/line).
   * Categories allowed/blocked (alcohol, tobacco blocked by default).
   * Validity window: Fri 00:00 → Sun 23:59; duration 8 weeks.
3. **Payment rails:** select Card-on-file (default). (Future: support bank/PayNow; AP2 is rail-agnostic.) ([Google Cloud][1])
4. **2FA confirmation:** Singpass/OTP; show **Mandate Preview** with human-readable summary + hash.
5. **Credential signing:** App generates an **AP2 Mandate** (verifiable credential) and stores a **user-held copy**; server keeps reference & status only. ([Google Cloud][1])
6. **Success state:** shareable **Mandate ID** and QR for debugging.

**UX Artifacts to deliver:** High-fidelity mockups, content strings, empty/error states, accessibility notes.

### 4.2 Agent checkout UX (User)

* **Cart sheet**: items, merchants, substitutions.
* **“Pay with Agent under Mandate”** CTA shows: mandate name, remaining cap, expiry, rails.
* **Override drawer** (if over cap): explain shortfall; offer one-off increase + step-up auth.

### 4.3 Merchant console UI (simulated)

* **Agent Transaction Banner** (top): “This order is initiated by **PantryPilot (Agent-123)** under **Mandate M-8F23** (Ava Tan).”
* **Mandate chip set:** `Scope: Groceries`, `Cap: S$180/wk (Remaining S$42)`, `Valid: Fri–Sun`, `No alcohol`.
* **Verify panel:** expandable card revealing verified fields: signer, signature alg, created/expiry, nonce, mandate hash. (Follows AP2 verification language.) ([ap2-protocol.org][2])

---

## 5) Functional Requirements

### 5.1 Mandates (AP2)

* **CreateMandate(user, payload)** → returns `mandate_vc` (W3C VC/JWT or JSON-LD), `mandate_id`, `status=active`.
* **RevokeMandate(mandate_id)** → `status=revoked`, with revocation list update.
* **GetMandateStatus(mandate_id)** → {active|revoked|expired, remaining_cap, window}.
* **ListMandates(user_id)** → list with summaries.

**Minimum mandate claims** (AP2-aligned):

* `subject`: user DID / identifier
* `agent_id`: PantryPilot DID
* `merchants_allowed`: list of domain patterns
* `categories_allowed/blocked`
* `spend_cap.amount`, `spend_cap.period` (e.g., S$180/week)
* `valid_from`, `valid_until`, `days_of_week`
* `payment_rails_allowed`: ["card", "bank"] (future: ["x402"])
* `policy`: age-restricted items disallowed
* `signature`: algorithm + key id
  (Claims model follows AP2 “mandate as verifiable, tamper-proof instruction”.) ([Google Cloud][1])

### 5.2 Checkout & Payment Intent (Agent → Merchant)

* **PreparePaymentIntent(cart, merchant_domain, mandate_id)**

  * Agent attaches **Mandate VC** + **intent hash** + **agent identity**; sends to merchant checkout endpoint.
  * Merchant validates: **signature, expiry, nonce, scope, cap coverage**; then returns `payment_intent_id` + order preview.
* **ConfirmPayment(payment_intent_id)** finalises order if within mandate; otherwise requires user step-up.

*(AP2 describes mandates as the foundational evidence for each transaction; we follow that pattern and keep the payment method itself rail-agnostic.)* ([Google Cloud][1])

### 5.3 Spend-cap enforcement

* **Cap tracker**: rolling weekly window; decremented on `ConfirmPayment`.
* **Race handling**: optimistic lock with `cap_version`; merchant receives remaining-cap snapshot & server timestamp.

### 5.4 Eventing & Audit

* **Events:** `MANDATE.CREATED/REVOKED`, `PAYMENT.INTENT.CREATED`, `PAYMENT.CONFIRMED/DECLINED`, `CAP.UPDATED`.
* **Audit log**: immutable append-only store linking `mandate_id`, `agent_id`, `merchant_domain`, and hashes.

---

## 6) Non-Functional Requirements

* **Security:** Keys stored with OS/TEE-backing where possible; signed requests; replay protection with nonces; mandate revocation lists; step-up auth for overages. (Aligns to AP2 security guidance around signed mandates / ECDSA-style signatures.) ([Google Cloud][1])
* **Privacy:** Store minimal PII; VC stored client-side, server stores references + status.
* **Compliance:** PDPA-aware logging; configurable data residency; age-restricted item policy.
* **Performance:** Merchant verification path ≤ 200 ms p95 under simulated load.

---

## 7) Architecture (Reference Implementation)

**Components**

* **Web App (User Portal):** React/Next.js; mandate creation & wallet.
* **Agent Service:** Node/Python service that plans meals, builds carts, calls merchants, and signs AP2 requests.
* **Mandate Service:** Issues/validates **AP2 Mandates** (VC format), cap ledger, revocation.
* **Merchant Simulator:** Express/FastAPI with “agent-aware” checkout to verify mandate envelopes and render merchant UI.
* **Integration layer:** abstract `PaymentRailProvider` (card/bank now; optional **x402** crypto rail later). ([Coinbase][3])

**Data stores**

* Mandate registry (Postgres) with hash pointers to client-held VC.
* Cap ledger (Postgres + row-level locking).
* Audit log (WORM bucket).

---

## 8) API Contracts (v1, simplified)

### 8.1 Mandates

`POST /mandates`

```json
{
  "template": "weekly_groceries",
  "merchants_allowed": ["*.fairprice.com.sg","*.redmart.com"],
  "spend_cap": {"amount": 180, "currency": "SGD", "period": "WEEK"},
  "validity": {"days_of_week": ["FRI","SAT","SUN"], "duration_weeks": 8},
  "categories_blocked": ["alcohol"],
  "rails_allowed": ["card"]
}
```

**201** →

```json
{
  "mandate_id": "M-8F23",
  "mandate_vc": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9....",
  "status": "active"
}
```

`POST /mandates/{id}/revoke` → **200** `{ "status":"revoked" }`

### 8.2 Checkout (Agent → Merchant)

`POST /merchant/{domain}/payment_intents`

```json
{
  "agent_id": "did:agent:pantrypilot:123",
  "mandate": {"vc": "JWT..."},
  "cart": {"items":[{"sku":"milk","qty":2,"price":3.2}]},
  "nonce": "c2a3...",
  "created_at": "2025-10-21T12:00:00Z"
}
```

**200** →

```json
{
  "payment_intent_id": "pi_abc",
  "verified": true,
  "mandate_summary": {"cap_remaining": 42, "valid_until":"2025-12-14"},
  "display_flags": {"agent_transaction": true}
}
```

`POST /payment_intents/{id}/confirm` → **200** `{ "status":"confirmed" }` or **402** with `requires_action: "user_step_up"`.

---

## 9) UX Specifications (key screens)

1. **Mandate Builder** (user)

* Sections: Scope ▸ Spend ▸ Time ▸ Rails ▸ Review & Sign
* Copy guidelines: human-first (“You’re authorising PantryPilot to buy groceries up to S$180/week from RedMart/FairPrice, Fridays to Sundays until Dec 14.”)

2. **Agent Checkout Sheet** (user)

* Shows **remaining cap**, **items**, **merchant(s)**, **policy banners** (no alcohol). Over-cap state offers one-off increase with OTP.

3. **Merchant Console** (merchant)

* **Agent badge** + **Mandate chips**
* **Verify drawer**: `signer`, `created`, `expires`, `nonce`, `mandate hash`, `scopes`, `cap remaining`. All wording mirrors AP2’s “mandate as foundational evidence” concept. ([Google Cloud][1])

---

## 10) Risk, Edge Cases & Mitigations

* **Replay / stolen mandate VC:** All requests require **fresh nonce + short expiry**; merchants verify and bind the mandate to the **merchant domain** before acceptance. ([ap2-protocol.org][2])
* **Concurrent spend (cart races):** optimistic locking on cap ledger; merchant receives `cap_version`.
* **Substitutions causing cap overage:** agent requests step-up; or merchant suggests cheaper alternatives.
* **Revocation timing:** mandate status checked at **intent** and **confirm**; cache TTL ≤ 60s.
* **Crypto rails (future):** add optional **x402** provider; same mandate envelope; distinct settlement path. ([Coinbase][3])

---

## 11) Success Metrics (v1 pilot)

* **Completion rate** of agent-led checkouts without user step-up ≥ 80% (within cap).
* **Time-to-checkout** ↓ 30% vs. manual checkout.
* **Mandate comprehension** (usability study): ≥ 90% of users correctly explain scope/limits after creation.
* **Merchant verification latency** p95 ≤ 200 ms.

---

## 12) Delivery Plan

**M0–M1 (4 weeks) — Foundations**

* Mandate service (VC/JWT issuance, revocation, cap ledger).
* Agent ↔ Merchant simulator with AP2-style envelopes.
* UX prototypes for mandate builder & merchant badge.

**M2 (4 weeks) — End-to-End**

* Full checkout flow with step-up overage.
* Merchant verification drawer + audit log.
* Usability tests with 8–10 families.

**M3 (2–3 weeks) — Hardening**

* Security review (key storage, nonce, expiry).
* Optional bank rail (PayNow mock).
* Experiment flag for **x402** provider stub (off by default). ([Coinbase][3])

---

## 13) Open Questions

* **Merchant attestation UX:** Should merchants attest they’ve checked the mandate drawer before fulfilment?
* **Dependent controls:** Per-child sub-mandates (e.g., S$20/week pocket-limit)?
* **Regional policy:** Auto-block age-restricted SKUs based on mandate policy vs. merchant’s own catalogue tagging.

---

## 14) References

* **AP2 overview & mandates** (signed, tamper-proof user instructions; payment-agnostic): Google blog + spec. ([Google Cloud][1])
* **x402 extension (future crypto rail):** Coinbase/partners overview. ([Coinbase][3])
* **Ecosystem/partners & positioning:** Axios / Business press summaries. ([Axios][4])
* **Security considerations for AP2:** Cloud Security Alliance. ([Cloud Security Alliance][5])
* **AP2 repo & issues (active work, mandate SDK requests):** GitHub. ([GitHub][6])

[1]: https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol?utm_source=chatgpt.com "Announcing Agent Payments Protocol (AP2)"
[2]: https://ap2-protocol.org/specification/?utm_source=chatgpt.com "AP2 specification - Agent Payments Protocol (AP2)"
[3]: https://www.coinbase.com/developer-platform/discover/launches/google_x402?utm_source=chatgpt.com "Google Agentic Payments Protocol + x402"
[4]: https://www.axios.com/2025/09/16/google-ai-agents-ecommerce-online-shopping?utm_source=chatgpt.com "Google's new plan to build trust in AI agents as personal shoppers"
[5]: https://cloudsecurityalliance.org/blog/2025/10/06/secure-use-of-the-agent-payments-protocol-ap2-a-framework-for-trustworthy-ai-driven-transactions?utm_source=chatgpt.com "Secure Use of the Agent Payments Protocol (AP2) | CSA"
[6]: https://github.com/google-agentic-commerce/AP2?utm_source=chatgpt.com "google-agentic-commerce/AP2: Building a Secure and ..."
