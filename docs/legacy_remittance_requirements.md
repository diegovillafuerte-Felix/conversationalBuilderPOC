# Felix Remittances - Business Requirements Document

> **Purpose**: This document maps the business logic and process flows for remittances as implemented in the conversations-api service. It serves as a reference for porting functionality to a new service.

---

## Table of Contents
1. [Geographic Scope](#1-geographic-scope)
2. [Delivery Methods](#2-delivery-methods)
3. [The Sending Process](#3-the-sending-process)
4. [Recipients (Beneficiaries)](#4-recipients-beneficiaries)
5. [Pricing & Limits](#5-pricing--limits)
6. [Transfer Status & Lifecycle](#6-transfer-status--lifecycle)
7. [Edge Cases & Special Flows](#7-edge-cases--special-flows)
8. [Key Decision Trees](#8-key-decision-trees)

---

## 1. GEOGRAPHIC SCOPE

### 1.1 Destination Countries
Users can send money to **7 destination countries**:

| Country | ISO Code | Currency | Status |
|---------|----------|----------|--------|
| Mexico | MX | MXN (Mexican Peso) | ✅ Fully supported |
| Guatemala | GT | GTQ (Quetzal) | ✅ Fully supported |
| Honduras | HN | HNL (Lempira) | ✅ Fully supported |
| Colombia | CO | COP (Colombian Peso) | ✅ Fully supported |
| Dominican Republic | DO | DOP (Dominican Peso) | ✅ Fully supported |
| El Salvador | SV | USD (US Dollar) | ✅ Fully supported |
| Nicaragua | NI | NIO (Córdoba) | ✅ Fully supported |

### 1.2 Source Country & Currency
- **Source**: United States only (US-based users)
- **Source Currency**: USD (US Dollars)

### 1.3 Country-Specific Differences

#### Mexico (MX)
- Most delivery methods available (bank, cash, debit card, wallets)
- Mercado Pago wallet integration
- Walmart/Bodega Aurrera cash pickup (special promotional rate: 0.5% discount)
- Deposit fee ($3.50) for certain bank transfers
- Azteca bank special promotions

#### Guatemala (GT)
- Bank deposits and cash pickup
- Special city selection flow for Guatemala City metro area
- State-level location required for cash pickup

#### Honduras (HN)
- Bank deposits and cash pickup
- Location (city/state) required

#### Colombia (CO)
- Bank deposits
- Digital wallets: Nequi, Daviplata, Zigi
- Requires account type selection (savings/checking)
- Bancolombia special handling
- Name validation on accounts

#### Dominican Republic (DO)
- Bank deposits and cash pickup
- Currency switching capability (DOP ↔ USD)
- Routed through chat service

#### El Salvador (SV)
- Native USD (dollarized economy)
- Bank deposits
- Routed through chat service
- Experimental pricing by group

#### Nicaragua (NI)
- Bank deposits and cash pickup
- Specific beneficiary name flow

---

## 2. DELIVERY METHODS

### 2.1 Delivery Method Types

| Type | Description | Countries |
|------|-------------|-----------|
| **BANK** | Direct bank deposit | All countries |
| **CASH** | Cash pickup at physical locations | MX, GT, HN, DO, NI |
| **DEBIT** | Debit card transfer | MX |
| **WALLET** | Digital wallet (Nequi, Daviplata, etc.) | CO, MX (Mercado Pago) |
| **UNITELLER_DIRECT** | Uniteller partner network | MX |
| **TRANSFER_DIRECTO_CASH** | Transfer Directo cash network | MX |
| **INTERMEX_DIRECT** | Intermex partner network | MX |

### 2.2 Recipient Info Required Per Delivery Method

#### Bank Deposit
- Bank name
- Account number
- Account type (savings/checking) - Colombia only
- CLABE (Mexico)
- Branch code (some banks)

#### Cash Pickup
- External location ID
- Store/location selection
- City and state (for finding pickup points)

#### Debit Card
- Card number (16 digits)
- Bank name

#### Wallet
- Wallet type (Nequi, Daviplata, Mercado Pago, etc.)
- Phone number or account number
- Account owner name

### 2.3 Disbursement Partners/Providers

| Provider | Countries | Delivery Types |
|----------|-----------|----------------|
| **Uniteller** | MX | Bank, Cash |
| **Intermex** | MX | Bank, Cash |
| **Transfer Directo** | MX | Bank, Cash |
| **Bitso** | MX | Bank (crypto rails) |
| **Arcus** | MX | Bank |
| **dLocal** | Multi-country | Bank |
| **Cobre** | GT, HN, NI | Bank, Cash |
| **Akisi** | CO, SV, DO | Bank |
| **Felix** | Internal | Various |

---

## 3. THE SENDING PROCESS

### 3.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER JOURNEY                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   START ──▶ HALLWAY ──▶ AMOUNT ──▶ BENEFICIARY ──▶ LOCATION        │
│                │                                       │             │
│                │                                       ▼             │
│            (New vs                               DELIVERY METHOD     │
│             Existing                                   │             │
│             User)                                      ▼             │
│                                                   CONFIRMATION       │
│                                                        │             │
│                                                        ▼             │
│                                                   PAYMENT LINK       │
│                                                        │             │
│                                                        ▼             │
│                                                   ORDER CREATED      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Step-by-Step Breakdown

#### Step 1: Hallway (Entry Point)
**What happens:**
- User greeting (new vs existing user)
- Menu display with options
- Quick transaction shortcuts (for returning users)

**Required Inputs:**
- User phone number (for identification)
- User message/intent

**Decisions/Branches:**
- New user → Special onboarding greeting
- Existing user → Show quick actions, recent recipients
- Partner user (Meli, Nubank, Felix API) → Route to partner flow
- Banned user → Block and notify

**What can go wrong:**
- Invalid phone number → Reject with error
- Banned/blocked user → Show ban message
- System error → Route to agent queue

---

#### Step 2: Amount Collection
**What happens:**
- User specifies how much to send
- System calculates exchange rate and fees
- Multi-entity detection (if user sends amount + beneficiary name together)

**Required Inputs:**
- Amount in USD or destination currency
- Currency preference (if applicable)

**Decisions/Branches:**
- Amount below minimum → Error message
- Amount exceeds KYC limit → Show limit info, offer upgrade
- Amount exceeds wallet/store limit → Suggest alternative delivery method

**What can go wrong:**
- Invalid amount format → Ask again
- KYC limits exceeded → Show limit info, block or prompt upgrade
- Rate expired → Refresh rate automatically

**Business Rules:**
- Minimum transfer: Varies by country (typically $1-5)
- Exchange rate has TTL (time-to-live), auto-refreshes when expired
- Fee calculated based on amount tiers and destination country

---

#### Step 3: Beneficiary Selection
**What happens:**
- Show existing beneficiaries for selected country
- Allow creating new beneficiary
- Name entity extraction from messages

**Required Inputs:**
- Beneficiary name (first name, last name, middle name optional)
- Selection from list OR new beneficiary info

**Decisions/Branches:**
- Existing beneficiary found → Pre-fill info
- Multiple potential matches → Show selection list
- New beneficiary → Collect name info
- Name entity detected → Auto-suggest match

**What can go wrong:**
- No matching beneficiary → Create new
- Ambiguous name match → Show options
- Invalid name format → Ask to clarify

---

#### Step 4: Location (Country-Specific)
**What happens:**
- Collect city/state for cash pickup
- Validate location exists in system

**Required Inputs:**
- City name
- State/province (for certain countries)

**Decisions/Branches:**
- Guatemala City area → Special metro area handling
- City not found → Suggest closest matches or escalate
- Location required only for cash delivery methods

**What can go wrong:**
- City not in system → Route to agent
- Ambiguous location → Show options

---

#### Step 5: Delivery Method Selection
**What happens:**
- Show available delivery methods for beneficiary/country
- Collect additional info based on method type
- Validate account/card information

**Required Inputs:**
- Delivery method type selection
- Bank account details OR
- Card number OR
- Wallet account OR
- Cash pickup location

**Decisions/Branches:**
- Bank deposit → Collect bank, account number, type
- Cash pickup → Show location options
- Wallet → Collect wallet type and number
- Existing delivery method → Use stored info

**What can go wrong:**
- Invalid account number → Validation error
- Bank not supported → Show alternatives
- Store limit exceeded → Suggest split or alternative
- Account validation failed → Prompt to correct

**Colombia-Specific:**
- Wallet selection (Nequi, Daviplata)
- Account type required (savings/checking)
- Name validation on accounts

---

#### Step 6: Confirmation & Summary
**What happens:**
- Display transaction summary
- Show fees and exchange rate
- Allow modifications before confirming

**Required Inputs:**
- User confirmation (button press or "yes")

**What's Displayed:**
- Recipient name
- Amount to send (USD)
- Amount to receive (local currency)
- Exchange rate
- Fees breakdown (regular, cash, deposit)
- Delivery method details
- Estimated arrival time

**Decisions/Branches:**
- User confirms → Proceed to payment
- User wants to modify → Return to relevant step
- Rate changed significantly → Show rate change notice

**What can go wrong:**
- Rate expired during confirmation → Refresh and show new total
- User abandons → Save state for later

---

#### Step 7: Payment Link Generation
**What happens:**
- Create order in Overseer system
- Generate payment link (Stripe/payment processor)
- Send link to user

**Required Inputs:**
- Confirmed transaction details
- User profile (for payment eligibility)

**Decisions/Branches:**
- New user → Show onboarding link (collect payment method)
- Existing user → Show direct payment link
- Promotional flow → Apply special rates/discounts

**What can go wrong:**
- Order creation fails → Route to agent
- Payment link generation fails → Retry or escalate

---

#### Step 8: Post-Confirmation
**What happens:**
- User completes payment externally
- System receives payment notification
- Disbursement initiated
- User receives confirmation

**Notifications:**
- Payment received
- Money on the way
- Money delivered (cash available for pickup OR deposited)

---

## 4. RECIPIENTS (BENEFICIARIES)

### 4.1 Beneficiary Data Model

```
Beneficiary
├── id (unique identifier)
├── user_id (owner)
├── name
│   ├── first_name
│   ├── middle_name (optional)
│   ├── last_name
│   └── second_last_name (optional)
├── location
│   ├── city
│   ├── state
│   └── country
├── country (ISO code)
├── provided_by (FELIX_PAGO, MERCADO_PAGO, NUBANK, VISIFI)
├── delivery_methods[] (array of delivery methods)
├── displayable_name (formatted for UI)
├── created_at
└── updated_at
```

### 4.2 Multiple Recipients
- Users can have **unlimited beneficiaries**
- Beneficiaries are filtered by destination country
- Each beneficiary can have multiple delivery methods
- Beneficiaries are sorted by recency/frequency

### 4.3 Recipient Types by Delivery Method

| Recipient Type | Required Fields |
|----------------|-----------------|
| Bank Account | Bank name, account number, account type |
| Cash Pickup | Location preference (stored when first used) |
| Debit Card | Card number, card holder name |
| Wallet | Wallet type, phone number or account |

### 4.4 Name Validation
- Some delivery methods require name validation
- System compares provided name against account holder name
- Validation status: PENDING, PASSED, FAILED
- Failed validation → Block or flag for review

---

## 5. PRICING & LIMITS

### 5.1 Fee Structure

#### Fee Types
| Fee Type | Description | When Applied |
|----------|-------------|--------------|
| **REGULAR** | Base transfer fee | All transfers |
| **CASH** | Cash pickup surcharge | Cash delivery only |
| **DEPOSIT** | Bank deposit fee | Mexico bank transfers to certain banks |

#### Fee Calculation
- Fees are **tiered by amount** (higher amounts may have different fee structures)
- Fees vary by **destination country**
- Promotional discounts can reduce or eliminate fees

#### Example Fee Structure (Mexico)
| Amount Range | Fee |
|--------------|-----|
| $1 - $100 | $3.99 |
| $101 - $300 | $4.99 |
| $301 - $500 | $5.99 |
| $500+ | Variable |

#### Deposit Fee
- **$3.50** for Mexico bank transfers to banks that require it
- Applied to existing users only (not new users)
- Only for BANK or DEBIT delivery methods

### 5.2 Transfer Limits

#### Limit Windows
| Window | Description |
|--------|-------------|
| DAILY | Resets every 24 hours |
| WEEKLY | Resets every 7 days |
| MONTHLY | Resets every 30 days |
| SEMIANNUALLY | Resets every 180 days |
| HISTORIC | Lifetime cumulative |

#### KYC-Based Limits
| KYC Level | Description | Typical Limit |
|-----------|-------------|---------------|
| **KYC_LITE** | Basic verification | Lower limits |
| **SENDER_KYC_L2** | ID verification | Medium limits |
| **SENDER_KYC_L3** | Enhanced verification | Higher limits |
| **SELFIE_AND_DOCUMENTATION_KYC** | Full verification | Highest limits |

### 5.3 Exchange Rates

#### Rate Mechanics
- **Live rates** fetched from rate service
- **Rate lock period**: Configurable TTL (time-to-live in minutes)
- **Rate expiration**: Auto-refresh when expired
- **Rate change detection**: Notify user if rate changes significantly

#### Promotional Rates
- Better rates for new users
- Campaign-specific rate improvements
- Walmart delivery: 0.5% rate bonus
- Azteca bank promotions

#### Rate Response Structure
```
Rate
├── value (decimal rate)
├── from_currency (USD)
├── to_currency (destination)
├── expires_at (timestamp)
└── promotional_rate (optional)
    ├── rate (improved rate)
    └── limit (max amount eligible)
```

---

## 6. TRANSFER STATUS & LIFECYCLE

### 6.1 Transaction States

```
                    ┌─────────────────────────────────────────────┐
                    │            TRANSACTION LIFECYCLE            │
                    └─────────────────────────────────────────────┘

    ┌─────────┐    ┌─────────┐    ┌───────────┐    ┌─────────────┐
    │ CREATED │───▶│ STARTED │───▶│ CONFIRMED │───▶│ IN_PROGRESS │
    └─────────┘    └─────────┘    └───────────┘    └──────┬──────┘
         │              │                                  │
         │              │                    ┌─────────────┼─────────────┐
         │              │                    ▼             ▼             ▼
         │              │              ┌──────────┐  ┌──────────┐  ┌──────────┐
         │              │              │ COMPLETE │  │  FAILED  │  │CANCELLED │
         │              │              └──────────┘  └────┬─────┘  └────┬─────┘
         │              │                                 │             │
         ▼              ▼                                 ▼             ▼
    ┌─────────┐    ┌─────────┐                      ┌──────────┐  ┌──────────┐
    │ EXPIRED │    │ (retry) │                      │ REFUNDED │  │ REFUNDED │
    └─────────┘    └─────────┘                      └──────────┘  └──────────┘
```

### 6.2 State Definitions

| State | Description |
|-------|-------------|
| **CREATED** | Transaction initiated, awaiting user input |
| **STARTED** | User began the flow |
| **CONFIRMED** | User confirmed details, pending payment |
| **IN_PROGRESS** | Payment received, disbursement processing |
| **COMPLETE** | Money delivered to recipient |
| **FAILED** | Disbursement failed (can be refunded/retried) |
| **CANCELLED** | User or system cancelled |
| **EXPIRED** | Transaction timed out |
| **REFUNDED** | Money returned to sender |

### 6.3 Cancellation Rules

Cancellation eligibility depends on **provider** and **current state**:

| Provider | Cancellable States |
|----------|-------------------|
| Uniteller | CREATED, PAYABLE, TRANSMITTED, CANCELLATION_IN_PROGRESS |
| Transfer Directo | CREATED, HOLD, PAYABLE, TRANSMITTED |
| Intermex | CREATED, WIRE_RELEASED, WIRE_CONFIRMED, WIRE_CREATED, CANCELLATION_IN_PROGRESS |
| dLocal | None (once initiated) |
| Cobre | None (once processing) |

**General Rule**: Cannot cancel once disbursement is PAID/COMPLETED.

### 6.4 Transfer Tracking

Users can track transfers via:
- Transaction history list
- Individual transaction status messages
- Push notifications (payment received, delivered, etc.)

---

## 7. EDGE CASES & SPECIAL FLOWS

### 7.1 New User vs Returning User

#### New User Flow
1. Special greeting message
2. Onboarding information
3. Onboarding link (to collect payment method first)
4. May have promotional rates/fee discounts
5. Lower initial limits (KYC_LITE)

#### Returning User Flow
1. Standard greeting
2. Quick transaction options (repeat last)
3. Recent beneficiaries shown
4. Direct payment link (has payment method on file)
5. Limits based on KYC level

### 7.2 KYC/Verification Gates

#### When KYC is Required
- Amount exceeds current KYC level limit
- First-time high-value transfer
- Compliance trigger (suspicious pattern)
- Beneficiary compliance check

#### KYC Process
1. User hits limit → Show limit message
2. Offer "Verify Identity" button
3. Generate KYC verification link
4. User completes verification externally
5. Receive KYC resolution notification (PASSED/FAILED)
6. Update user limits

#### KYC Levels
| Level | Description |
|-------|-------------|
| KYC_LITE | Basic info, lowest limits |
| SENDER_KYC_L2 | ID verification |
| SENDER_KYC_L3 | Enhanced verification |
| COMPLIANT_BENEFICIARY | Beneficiary verification |

### 7.3 Agent Escalation Triggers

| Trigger | Queue Destination |
|---------|-------------------|
| Message not understood | Escalations |
| User says "talk to agent" | Escalations |
| KYC issues | Compliance |
| Suspected fraud | Compliance |
| Failed multiple attempts (10+) | Escalations |
| Beneficiary city not in list | Escalations |
| Wrong beneficiary info | Escalations |
| Cancellation request | Cancellations |
| Modification request | Modifications |
| Hold/compliance block | Hold Queue |
| Failed payments | Failed Payments |
| Deduplication (duplicate user) | Deduplication |

### 7.4 Compliance Blocks & Holds

#### Hold States
- **HOLD_BY_COMPLIANCE**: Under review by compliance team
- **HOLD_BY_PAYER**: Held by disbursement partner
- **PAUSED_PAYMENT**: Payment temporarily paused

#### Fraud/Risk Triggers
- Suspected fraud flag
- Deduplication (multiple accounts)
- Unusual transaction patterns
- Failed KYU (Know Your User) check

### 7.5 Partner-Specific Flows

#### Mercado Libre (Meli) Integration
- Special opening flow for Meli users
- Meli wallet as delivery method
- MercadoPago account support
- Meli Flow 2/3 for bank accounts

#### Nubank Integration
- Special Nubank user identification
- Nubank-specific greeting
- Direct routing to chat service

#### Felix API Partners
- External partner integrations
- Pre-populated transaction data
- Special confirmation flows

### 7.6 Quick Transactions
- "Repeat last send" functionality
- Pre-populated with last transaction details
- One-click initiation for frequent senders
- Feature-flagged rollout

---

## 8. KEY DECISION TREES

### 8.1 Country Routing Decision

```
IF user.default_remittance_country == "DO" OR "SV":
    → Route to chat service
ELSE IF user.default_remittance_country in ["MX", "GT", "HN", "CO", "NI"]:
    → Handle in conversations-api
ELSE:
    → Error: Country not supported
```

### 8.2 Delivery Method Selection by Country

```
MEXICO (MX):
├── Bank Deposit ✓
├── Cash Pickup ✓
├── Debit Card ✓
├── Mercado Pago Wallet ✓
└── Uniteller/Intermex/Transfer Directo ✓

GUATEMALA (GT):
├── Bank Deposit ✓
└── Cash Pickup ✓

HONDURAS (HN):
├── Bank Deposit ✓
└── Cash Pickup ✓

COLOMBIA (CO):
├── Bank Deposit ✓
├── Nequi Wallet ✓
├── Daviplata Wallet ✓
└── Zigi Wallet ✓

DOMINICAN REPUBLIC (DO):
├── Bank Deposit ✓
└── Cash Pickup ✓

EL SALVADOR (SV):
└── Bank Deposit ✓

NICARAGUA (NI):
├── Bank Deposit ✓
└── Cash Pickup ✓
```

### 8.3 KYC Limit Decision

```
IF transaction.amount > user.available_limit:
    IF limit_window == "DAILY":
        → "You've reached your 24-hour limit of $X"
    ELSE IF limit_window == "MONTHLY":
        → "You've reached your 30-day limit of $X"
    ELSE IF limit_window == "SEMIANNUALLY":
        → "You've reached your 180-day limit of $X"
    
    → Offer KYC upgrade button
    → Show remaining available amount
ELSE:
    → Continue with transaction
```

### 8.4 Fee Calculation Decision

```
base_fee = get_fee_by_country_and_amount(country, amount)

IF delivery_method.type == CASH:
    → Add cash_fee

IF country == "MX" AND delivery_method.type in [BANK, DEBIT]:
    IF user.is_existing AND bank_requires_deposit_fee(bank):
        → Add deposit_fee ($3.50)

IF user.has_promotional_discount:
    → Apply promotional discount to fees

final_fee = base_fee + cash_fee + deposit_fee - promotional_discount
```

### 8.5 Cancellation Eligibility Decision

```
provider = transaction.disbursement_provider
state = transaction.disbursement_status

cancellation_rules = get_rules_for_provider(provider)

IF state in cancellation_rules.cancellable_states:
    → Allow cancellation
ELSE IF state == "PAID":
    → "This transfer has already been completed and cannot be cancelled"
ELSE IF state in ["HOLD_BY_COMPLIANCE", "HOLD_BY_PAYER"]:
    → "This transfer is on hold and cannot be cancelled right now"
ELSE:
    → "This transfer cannot be cancelled at this time"
```

### 8.6 Rate Refresh Decision

```
IF rate.expires_at <= now():
    → Fetch new rate from rate service
    → Update transaction with new rate
    IF new_rate significantly different from old_rate:
        → Notify user of rate change
        → Recalculate destination amount

IF rate.to_currency != transaction.destination_currency:
    → Rate mismatch, fetch correct rate
```

---

## Appendix A: Message Types & Intents

### Recognized Intents
| Intent | Description |
|--------|-------------|
| SEND_MONEY | User wants to send money |
| CONFIRMATION | User confirms action |
| AGENT_HELP | User wants to talk to agent |
| DISPLAY_RATE | User asks about exchange rate |
| THANKING | User thanks the bot |
| FEEDBACK | User provides feedback |
| CANCELLATION | User wants to cancel |
| MODIFICATION | User wants to modify |

### FAQ Questions Handled
- What is Felix?
- How does it work?
- How much does it cost?
- Where can I send money?
- What banks are supported?
- When will money arrive?
- How do I cancel?
- What is my limit?
- How do I verify my identity?

---

## Appendix B: Provider Status Mappings

### Uniteller States
| State | Can Cancel | Can Refund |
|-------|------------|------------|
| CREATED | ✓ | ✗ |
| PAYABLE | ✓ | ✗ |
| TRANSMITTED | ✓ | ✗ |
| PAID | ✗ | ✗ |
| CANCELLED | ✗ | ✓ |
| FAILED | ✗ | ✓ |

### Intermex States
| State | Can Cancel | Can Refund |
|-------|------------|------------|
| CREATED | ✓ | ✗ |
| WIRE_CREATED | ✓ | ✗ |
| WIRE_RELEASED | ✓ | ✗ |
| WIRE_CONFIRMED | ✓ | ✗ |
| PAID | ✗ | ✗ |
| CANCELLED | ✗ | ✓ |
| FAILED | ✗ | ✓ |
| HOLD_BY_COMPLIANCE | ✗ | ✗ |
| HOLD_BY_PAYER | ✗ | ✗ |

---

## Appendix C: Currency Precision

| Currency | Precision (Decimal Places) |
|----------|---------------------------|
| USD | 2 |
| MXN | 2 |
| GTQ | 2 |
| HNL | 2 |
| COP | 0 (whole numbers) |
| DOP | 2 |
| NIO | 2 |

---

# PART 2: DECLARATIVE SYSTEM REQUIREMENTS

> **Purpose**: This section maps the remittances business logic to the format required by the new config-driven conversational system. It defines tools, subflows, data models, business rules, and error cases for JSON configuration.

---

## 9. USER ACTIONS (Tools)

Each tool represents an action the LLM agent can invoke based on user intent.

### 9.1 Financial Tools (Require Confirmation)

#### Tool: `send_money`
**Description**: Initiates a money transfer to a recipient  
**Requires Confirmation**: ✅ YES (financial action)

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `recipient_id` | string | Yes* | ID of existing recipient | `"rec_abc123"` |
| `recipient_name` | string | Yes* | Name for new recipient | `"Maria Garcia"` |
| `amount` | decimal | Yes | Amount to send | `100.00` |
| `amount_currency` | enum | No | USD or destination currency | `"USD"` (default) |
| `delivery_method_id` | string | No | Specific delivery method | `"dm_xyz789"` |
| `delivery_method_type` | enum | No | BANK, CASH, WALLET, DEBIT | `"BANK"` |

*Either `recipient_id` OR `recipient_name` required

**Triggers Subflow**: `send_money_flow` if missing required data

---

#### Tool: `cancel_transfer`
**Description**: Cancels a pending transfer (if eligible)  
**Requires Confirmation**: ✅ YES (financial action)

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `transfer_id` | string | Yes | Transfer to cancel | `"txn_abc123"` |

**Pre-conditions**: Transfer must be in cancellable state (see Section 6.3)

---

#### Tool: `request_refund`
**Description**: Requests refund for failed/cancelled transfer  
**Requires Confirmation**: ✅ YES (financial action)

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `transfer_id` | string | Yes | Transfer to refund | `"txn_abc123"` |

---

### 9.2 Information Tools (No Confirmation)

#### Tool: `get_exchange_rate`
**Description**: Returns current exchange rate for a corridor  
**Requires Confirmation**: ❌ NO

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `destination_country` | enum | No | Country code | `"MX"` (defaults to user's default) |
| `amount` | decimal | No | Amount for calculation | `100.00` |

**Returns**:
```json
{
  "rate": 17.25,
  "from_currency": "USD",
  "to_currency": "MXN",
  "destination_amount": 1725.00,
  "fee": 3.99,
  "total_to_pay": 103.99,
  "expires_at": "2026-01-11T15:30:00Z",
  "rate_valid_for_minutes": 15
}
```

---

#### Tool: `list_recipients`
**Description**: Lists user's saved recipients  
**Requires Confirmation**: ❌ NO

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `country` | enum | No | Filter by country | `"MX"` |
| `limit` | int | No | Max results | `10` |

**Returns**: Array of recipient objects (see Data Models)

---

#### Tool: `get_recipient`
**Description**: Gets details of a specific recipient  
**Requires Confirmation**: ❌ NO

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `recipient_id` | string | Yes | Recipient ID | `"rec_abc123"` |

---

#### Tool: `list_transfers`
**Description**: Lists user's transfer history  
**Requires Confirmation**: ❌ NO

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `status` | enum | No | Filter by status | `"IN_PROGRESS"` |
| `limit` | int | No | Max results | `10` |
| `recipient_id` | string | No | Filter by recipient | `"rec_abc123"` |

---

#### Tool: `get_transfer_status`
**Description**: Gets status of a specific transfer  
**Requires Confirmation**: ❌ NO

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `transfer_id` | string | Yes | Transfer ID | `"txn_abc123"` |

**Returns**:
```json
{
  "transfer_id": "txn_abc123",
  "status": "IN_PROGRESS",
  "status_message": "Tu dinero está en camino",
  "recipient_name": "Maria Garcia",
  "amount_sent": 100.00,
  "amount_received": 1725.00,
  "delivery_method": "Bank Deposit - BBVA",
  "estimated_delivery": "Within 24 hours",
  "created_at": "2026-01-11T10:00:00Z",
  "can_cancel": false
}
```

---

#### Tool: `get_limits`
**Description**: Gets user's current sending limits  
**Requires Confirmation**: ❌ NO

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| (none) | | | Uses authenticated user | |

**Returns**:
```json
{
  "daily_limit": 2999.00,
  "daily_used": 500.00,
  "daily_available": 2499.00,
  "monthly_limit": 10000.00,
  "monthly_used": 1500.00,
  "monthly_available": 8500.00,
  "kyc_level": "SENDER_KYC_L2",
  "can_upgrade": true
}
```

---

#### Tool: `get_delivery_methods`
**Description**: Gets available delivery methods for a recipient/country  
**Requires Confirmation**: ❌ NO

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `country` | enum | Yes | Destination country | `"MX"` |
| `recipient_id` | string | No | For saved methods | `"rec_abc123"` |

---

### 9.3 Management Tools (Conditional Confirmation)

#### Tool: `add_recipient`
**Description**: Creates a new recipient  
**Requires Confirmation**: ⚠️ YES (before saving)

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `first_name` | string | Yes | First name | `"Maria"` |
| `last_name` | string | Yes | Last name | `"Garcia"` |
| `middle_name` | string | No | Middle name | `"Elena"` |
| `country` | enum | Yes | Destination country | `"MX"` |
| `city` | string | Conditional | Required for cash | `"Guadalajara"` |
| `state` | string | Conditional | Required for cash | `"Jalisco"` |

**Triggers Subflow**: `add_recipient_flow` to collect delivery method

---

#### Tool: `add_delivery_method`
**Description**: Adds delivery method to existing recipient  
**Requires Confirmation**: ⚠️ YES (before saving)

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `recipient_id` | string | Yes | Recipient ID | `"rec_abc123"` |
| `type` | enum | Yes | BANK, CASH, WALLET, DEBIT | `"BANK"` |
| `bank_name` | string | Conditional | For BANK/DEBIT | `"BBVA"` |
| `account_number` | string | Conditional | For BANK | `"012345678901234567"` |
| `account_type` | enum | Conditional | For CO banks | `"SAVINGS"` |
| `card_number` | string | Conditional | For DEBIT | `"4152313012345678"` |
| `wallet_type` | enum | Conditional | For WALLET | `"NEQUI"` |
| `wallet_account` | string | Conditional | For WALLET | `"3001234567"` |

---

#### Tool: `delete_recipient`
**Description**: Deletes a recipient (soft delete)  
**Requires Confirmation**: ✅ YES

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `recipient_id` | string | Yes | Recipient to delete | `"rec_abc123"` |

---

#### Tool: `request_kyc_upgrade`
**Description**: Initiates KYC verification to increase limits  
**Requires Confirmation**: ❌ NO (just sends link)

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| (none) | | | Uses authenticated user | |

**Returns**: Verification link URL

---

#### Tool: `talk_to_agent`
**Description**: Escalates conversation to human agent  
**Requires Confirmation**: ❌ NO

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `reason` | string | No | Why user needs help | `"question about my transfer"` |

---

## 10. MULTI-STEP PROCESSES (Subflows)

### 10.1 Subflow: `send_money_flow`

**Purpose**: Complete money transfer requiring multiple steps  
**Trigger**: User wants to send money but missing required info

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SEND MONEY SUBFLOW                                   │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │    START    │
                              └──────┬──────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                                 ▼
            ┌───────────────┐                 ┌───────────────┐
            │ Has Recipient │─── NO ─────────▶│ SELECT/CREATE │
            │    Info?      │                 │  RECIPIENT    │
            └───────┬───────┘                 └───────┬───────┘
                    │ YES                             │
                    │◀────────────────────────────────┘
                    ▼
            ┌───────────────┐
            │  Has Amount?  │─── NO ─────────▶┌───────────────┐
            └───────┬───────┘                 │ COLLECT AMOUNT│
                    │ YES                     └───────┬───────┘
                    │◀────────────────────────────────┘
                    ▼
            ┌───────────────┐
            │ Has Delivery  │─── NO ─────────▶┌───────────────┐
            │   Method?     │                 │SELECT DELIVERY│
            └───────┬───────┘                 └───────┬───────┘
                    │ YES                             │
                    │◀────────────────────────────────┘
                    ▼
            ┌───────────────┐
            │    REVIEW     │
            │    SUMMARY    │
            └───────┬───────┘
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ CONFIRM │ │ MODIFY  │ │ CANCEL  │
    └────┬────┘ └────┬────┘ └────┬────┘
         │           │           │
         ▼           │           ▼
    ┌─────────┐      │      ┌─────────┐
    │ PAYMENT │      │      │  EXIT   │
    │  LINK   │      │      └─────────┘
    └────┬────┘      │
         │           │
         ▼           └──────▶ (back to relevant step)
    ┌─────────┐
    │COMPLETE │
    └─────────┘
```

#### State: `select_recipient`
**Instructions to LLM**: "User needs to pick a recipient. Show their saved recipients for {country} or offer to create new one."

| Collected Data | Type | Source |
|----------------|------|--------|
| `recipient_id` | string | User selection or new creation |
| `recipient_name` | string | From selection or user input |

**Transitions**:
- User selects existing → `collect_amount`
- User wants new recipient → `add_recipient_flow` (nested subflow)
- User says different country → `select_country` (if enabled)

---

#### State: `collect_amount`
**Instructions to LLM**: "Ask user how much they want to send. Accept USD or {destination_currency}. Show current rate: {rate}."

| Collected Data | Type | Validation |
|----------------|------|------------|
| `amount` | decimal | Min $1, Max based on limits |
| `amount_currency` | enum | USD or destination currency |

**Transitions**:
- Valid amount within limits → `select_delivery_method`
- Amount exceeds limit → Show limit error, offer `request_kyc_upgrade`
- Amount below minimum → Show error, re-prompt

---

#### State: `select_delivery_method`
**Instructions to LLM**: "Ask how the recipient should receive the money. Options: {available_methods_for_country}"

| Collected Data | Type | Source |
|----------------|------|--------|
| `delivery_method_id` | string | Existing method selection |
| `delivery_method_type` | enum | BANK, CASH, WALLET, DEBIT |

**Transitions**:
- Selects existing method → `review_summary`
- Wants new method → `add_delivery_method_flow` (nested)
- Cash selected, needs location → `collect_location`

---

#### State: `collect_location` (for cash pickup)
**Instructions to LLM**: "Ask what city the recipient will pick up the cash in."

| Collected Data | Type | Validation |
|----------------|------|------------|
| `city` | string | Must exist in system |
| `state` | string | Required for some countries |

**Transitions**:
- Valid location → `select_pickup_point`
- Invalid location → Show suggestions or escalate

---

#### State: `review_summary`
**Instructions to LLM**: "Show complete summary and ask for confirmation. Display all details clearly."

**Display Data**:
```
📤 Sending: $100.00 USD
📥 {Recipient} receives: $1,725.00 MXN
💱 Exchange rate: 1 USD = 17.25 MXN
💰 Fee: $3.99 USD
💳 Total to pay: $103.99 USD
🏦 Delivery: Bank deposit to BBVA ****1234
⏱️ Arrives: Within 24 hours
```

**Transitions**:
- User confirms → `generate_payment`
- User wants to change amount → `collect_amount`
- User wants different recipient → `select_recipient`
- User wants different delivery → `select_delivery_method`
- User cancels → `exit`

---

#### State: `generate_payment`
**Instructions to LLM**: "Generate payment link and send to user. Confirm next steps."

**Actions**:
1. Create order in backend
2. Generate payment link
3. Send link to user

**Message**: "¡Perfecto! Aquí está tu link de pago: {payment_link}. El dinero llegará a {recipient_name} dentro de {delivery_time} después de que completes el pago."

**Transitions**:
- Success → `complete`
- Error → `error_state` (escalate to agent)

---

### 10.2 Subflow: `add_recipient_flow`

**Purpose**: Create a new recipient with delivery method

```
States:
1. collect_name → Get first/last name
2. select_country → Pick destination country
3. select_delivery_type → BANK, CASH, WALLET, etc.
4. collect_delivery_details → Bank account, card, or wallet info
5. collect_location → City/state (if cash)
6. confirm_recipient → Review and save
```

#### State: `collect_name`
| Collected Data | Type | Required |
|----------------|------|----------|
| `first_name` | string | Yes |
| `middle_name` | string | No |
| `last_name` | string | Yes |
| `second_last_name` | string | No |

---

#### State: `collect_delivery_details`

**For BANK (Mexico)**:
| Field | Example | Validation |
|-------|---------|------------|
| `bank_name` | "BBVA" | Must be supported bank |
| `clabe` | "012345678901234567" | 18 digits |

**For BANK (Colombia)**:
| Field | Example | Validation |
|-------|---------|------------|
| `bank_name` | "Bancolombia" | Must be supported |
| `account_number` | "12345678901" | 11 digits |
| `account_type` | "SAVINGS" | SAVINGS or CHECKING |

**For WALLET (Colombia)**:
| Field | Example | Validation |
|-------|---------|------------|
| `wallet_type` | "NEQUI" | NEQUI, DAVIPLATA, ZIGI |
| `phone_number` | "3001234567" | 10 digits, starts with 3 |

**For DEBIT (Mexico)**:
| Field | Example | Validation |
|-------|---------|------------|
| `card_number` | "4152313012345678" | 16 digits |
| `bank_name` | "BBVA" | Derived from BIN |

---

### 10.3 Subflow: `modify_transfer_flow`

**Purpose**: Modify a pending transfer

```
States:
1. select_transfer → Pick which transfer to modify
2. select_modification → What to change (amount, delivery method)
3. apply_changes → Update transfer
4. confirm_changes → Review and confirm
```

**Eligibility**: Only transfers in modifiable states (CREATED, STARTED, CONFIRMED before payment)

---

### 10.4 Subflow: `quick_send_flow`

**Purpose**: Repeat a previous transaction with one confirmation

```
States:
1. show_quick_options → Display recent/frequent transfers
2. confirm_quick_send → "Send $100 to Maria again?"
3. generate_payment → Create payment link
```

**Data Pre-filled**: Recipient, amount, delivery method from previous transaction

---

## 11. DATA MODELS (For Mock Service)

### 11.1 Recipient Object

```json
{
  "id": "rec_abc123def456",
  "user_id": "usr_xyz789",
  "name": {
    "first_name": "Maria",
    "middle_name": "Elena",
    "last_name": "Garcia",
    "second_last_name": "Lopez",
    "display_name": "Maria Elena Garcia"
  },
  "country": "MX",
  "location": {
    "city": "Guadalajara",
    "state": "Jalisco",
    "country": "MX"
  },
  "delivery_methods": [
    {
      "id": "dm_bank001",
      "type": "BANK",
      "display_name": "BBVA ****1234",
      "bank_info": {
        "bank_name": "BBVA",
        "bank_code": "012",
        "account_number": "************1234",
        "clabe": "012345678901234567",
        "account_type": null
      },
      "is_default": true,
      "created_at": "2025-06-15T10:30:00Z"
    },
    {
      "id": "dm_cash001",
      "type": "CASH",
      "display_name": "Cash pickup - Guadalajara",
      "cash_info": {
        "preferred_store": "Elektra Centro",
        "city": "Guadalajara",
        "state": "Jalisco"
      },
      "is_default": false,
      "created_at": "2025-08-20T14:00:00Z"
    }
  ],
  "created_at": "2025-06-15T10:30:00Z",
  "updated_at": "2025-08-20T14:00:00Z",
  "last_transfer_at": "2026-01-05T16:45:00Z",
  "transfer_count": 12
}
```

### 11.2 Transfer Object

```json
{
  "id": "txn_abc123def456",
  "user_id": "usr_xyz789",
  "status": "IN_PROGRESS",
  "status_display": "Tu dinero está en camino",
  "recipient": {
    "id": "rec_abc123def456",
    "name": "Maria Elena Garcia",
    "country": "MX"
  },
  "amount": {
    "send_amount": 100.00,
    "send_currency": "USD",
    "receive_amount": 1725.00,
    "receive_currency": "MXN"
  },
  "rate": {
    "value": 17.25,
    "locked_at": "2026-01-11T10:00:00Z"
  },
  "fees": {
    "regular_fee": 3.99,
    "cash_fee": 0.00,
    "deposit_fee": 0.00,
    "total_fee": 3.99,
    "fee_currency": "USD"
  },
  "total_charged": 103.99,
  "delivery_method": {
    "id": "dm_bank001",
    "type": "BANK",
    "display_name": "BBVA ****1234"
  },
  "estimated_delivery": "Within 24 hours",
  "can_cancel": false,
  "can_modify": false,
  "payment": {
    "status": "COMPLETED",
    "payment_link": null,
    "paid_at": "2026-01-11T10:05:00Z"
  },
  "disbursement": {
    "provider": "UNITELLER",
    "status": "TRANSMITTED",
    "reference_number": "UTL123456789"
  },
  "created_at": "2026-01-11T10:00:00Z",
  "updated_at": "2026-01-11T10:30:00Z"
}
```

### 11.3 Quote/Rate Object

```json
{
  "quote_id": "qt_abc123",
  "from_currency": "USD",
  "to_currency": "MXN",
  "destination_country": "MX",
  "rate": 17.25,
  "rate_type": "STANDARD",
  "promotional_rate": null,
  "amount_breakdown": {
    "send_amount": 100.00,
    "receive_amount": 1725.00,
    "regular_fee": 3.99,
    "cash_fee": 0.00,
    "deposit_fee": 0.00,
    "total_fee": 3.99,
    "total_to_pay": 103.99
  },
  "delivery_methods_available": ["BANK", "CASH", "DEBIT", "WALLET"],
  "expires_at": "2026-01-11T10:30:00Z",
  "valid_for_seconds": 900
}
```

### 11.4 User Limits Object

```json
{
  "user_id": "usr_xyz789",
  "kyc_level": "SENDER_KYC_L2",
  "kyc_level_display": "ID Verified",
  "limits": {
    "per_transaction": {
      "max": 2999.00,
      "currency": "USD"
    },
    "daily": {
      "limit": 2999.00,
      "used": 500.00,
      "available": 2499.00,
      "resets_at": "2026-01-12T00:00:00Z"
    },
    "monthly": {
      "limit": 10000.00,
      "used": 1500.00,
      "available": 8500.00,
      "resets_at": "2026-02-01T00:00:00Z"
    },
    "semiannual": {
      "limit": 30000.00,
      "used": 5000.00,
      "available": 25000.00,
      "resets_at": "2026-07-01T00:00:00Z"
    }
  },
  "can_upgrade": true,
  "next_level": "SENDER_KYC_L3",
  "upgrade_benefits": "Increase your limits to $5,000/day"
}
```

### 11.5 Delivery Method Catalog

```json
{
  "country": "MX",
  "currency": "MXN",
  "delivery_methods": [
    {
      "type": "BANK",
      "display_name": "Depósito bancario",
      "description": "Deposit directly to any Mexican bank account",
      "delivery_time": "Within 24 hours",
      "delivery_time_hours": 24,
      "requires_fields": ["bank_name", "clabe"],
      "supported_banks": ["BBVA", "Santander", "Banamex", "Banorte", "HSBC", "Azteca"],
      "has_deposit_fee": true,
      "deposit_fee_banks": ["BBVA", "Santander"]
    },
    {
      "type": "CASH",
      "display_name": "Efectivo",
      "description": "Pick up cash at store locations",
      "delivery_time": "Within 1 hour",
      "delivery_time_hours": 1,
      "requires_fields": ["city", "state"],
      "pickup_networks": ["Elektra", "Walmart", "Bodega Aurrera", "OXXO"],
      "has_cash_fee": true,
      "cash_fee": 5.00
    },
    {
      "type": "DEBIT",
      "display_name": "Tarjeta de débito",
      "description": "Send directly to a debit card",
      "delivery_time": "Within 30 minutes",
      "delivery_time_hours": 0.5,
      "requires_fields": ["card_number"],
      "supported_bins": ["4152", "4915", "5579"]
    },
    {
      "type": "WALLET",
      "display_name": "Mercado Pago",
      "description": "Send to Mercado Pago wallet",
      "delivery_time": "Instant",
      "delivery_time_hours": 0,
      "requires_fields": ["wallet_account"],
      "wallet_types": ["MERCADO_PAGO"]
    }
  ]
}
```

---

## 12. BUSINESS RULES (Validation Config)

### 12.1 Supported Corridors

```json
{
  "source_country": "US",
  "source_currency": "USD",
  "corridors": [
    {
      "destination_country": "MX",
      "destination_currency": "MXN",
      "delivery_methods": ["BANK", "CASH", "DEBIT", "WALLET"],
      "typical_rate_range": [16.50, 18.00],
      "min_amount_usd": 1.00,
      "max_amount_usd": 2999.00
    },
    {
      "destination_country": "GT",
      "destination_currency": "GTQ",
      "delivery_methods": ["BANK", "CASH"],
      "typical_rate_range": [7.50, 8.00],
      "min_amount_usd": 1.00,
      "max_amount_usd": 2999.00
    },
    {
      "destination_country": "HN",
      "destination_currency": "HNL",
      "delivery_methods": ["BANK", "CASH"],
      "typical_rate_range": [24.00, 25.50],
      "min_amount_usd": 1.00,
      "max_amount_usd": 2999.00
    },
    {
      "destination_country": "CO",
      "destination_currency": "COP",
      "delivery_methods": ["BANK", "WALLET"],
      "typical_rate_range": [3800.00, 4200.00],
      "min_amount_usd": 1.00,
      "max_amount_usd": 2999.00,
      "currency_precision": 0
    },
    {
      "destination_country": "DO",
      "destination_currency": "DOP",
      "delivery_methods": ["BANK", "CASH"],
      "typical_rate_range": [56.00, 59.00],
      "min_amount_usd": 1.00,
      "max_amount_usd": 2999.00,
      "supports_usd_delivery": true
    },
    {
      "destination_country": "SV",
      "destination_currency": "USD",
      "delivery_methods": ["BANK"],
      "typical_rate_range": [1.00, 1.00],
      "min_amount_usd": 1.00,
      "max_amount_usd": 2999.00,
      "note": "Dollarized economy - no FX"
    },
    {
      "destination_country": "NI",
      "destination_currency": "NIO",
      "delivery_methods": ["BANK", "CASH"],
      "typical_rate_range": [36.00, 37.50],
      "min_amount_usd": 1.00,
      "max_amount_usd": 2999.00
    }
  ]
}
```

### 12.2 Fee Structure

```json
{
  "fee_type": "TIERED_BY_AMOUNT",
  "default_currency": "USD",
  "tiers": [
    { "min_amount": 0, "max_amount": 100, "fee": 3.99 },
    { "min_amount": 100.01, "max_amount": 300, "fee": 4.99 },
    { "min_amount": 300.01, "max_amount": 500, "fee": 5.99 },
    { "min_amount": 500.01, "max_amount": 999999, "fee": 6.99 }
  ],
  "additional_fees": {
    "cash_pickup": {
      "type": "FLAT",
      "amount": 5.00,
      "applies_to": ["CASH"]
    },
    "deposit_fee": {
      "type": "FLAT",
      "amount": 3.50,
      "applies_to": ["BANK", "DEBIT"],
      "countries": ["MX"],
      "banks": ["BBVA", "Santander"],
      "only_existing_users": true
    }
  },
  "promotions": {
    "new_user_discount": {
      "type": "PERCENTAGE",
      "value": 100,
      "max_discount": 10.00,
      "description": "First transfer free"
    },
    "walmart_rate_bonus": {
      "type": "RATE_MULTIPLIER",
      "value": 1.005,
      "applies_to_stores": ["Walmart", "Bodega Aurrera"]
    }
  }
}
```

### 12.3 KYC Limits by Level

```json
{
  "kyc_levels": [
    {
      "level": "KYC_LITE",
      "display_name": "Basic",
      "description": "Phone verification only",
      "limits": {
        "per_transaction": 500,
        "daily": 500,
        "monthly": 1000,
        "semiannual": 3000
      },
      "requirements": ["phone_verified"]
    },
    {
      "level": "SENDER_KYC_L2",
      "display_name": "ID Verified",
      "description": "Government ID verified",
      "limits": {
        "per_transaction": 2999,
        "daily": 2999,
        "monthly": 10000,
        "semiannual": 30000
      },
      "requirements": ["phone_verified", "id_verified"]
    },
    {
      "level": "SENDER_KYC_L3",
      "display_name": "Fully Verified",
      "description": "Enhanced verification complete",
      "limits": {
        "per_transaction": 5000,
        "daily": 5000,
        "monthly": 25000,
        "semiannual": 75000
      },
      "requirements": ["phone_verified", "id_verified", "address_verified", "selfie_verified"]
    }
  ]
}
```

### 12.4 Delivery Timeframes

| Country | Method | Typical Time | Display Text |
|---------|--------|--------------|--------------|
| MX | BANK | 24 hours | "Within 24 hours" |
| MX | CASH | 1 hour | "Within 1 hour" |
| MX | DEBIT | 30 min | "Within 30 minutes" |
| MX | WALLET | Instant | "Instant" |
| GT | BANK | 24-48 hours | "1-2 business days" |
| GT | CASH | 1 hour | "Within 1 hour" |
| HN | BANK | 24-48 hours | "1-2 business days" |
| CO | BANK | 24 hours | "Within 24 hours" |
| CO | WALLET | Instant | "Instant" |
| DO | BANK | 24 hours | "Within 24 hours" |
| SV | BANK | 24-48 hours | "1-2 business days" |
| NI | BANK | 24-48 hours | "1-2 business days" |

---

## 13. ERROR CASES (User-Facing Messages)

### 13.1 Amount Errors

| Error Code | Condition | User Message (Spanish) | User Message (English) |
|------------|-----------|------------------------|------------------------|
| `AMOUNT_BELOW_MINIMUM` | amount < $1 | "El monto mínimo es $1 USD" | "The minimum amount is $1 USD" |
| `AMOUNT_EXCEEDS_TRANSACTION_LIMIT` | amount > per_txn limit | "El monto máximo por envío es ${limit}" | "Maximum per transfer is ${limit}" |
| `AMOUNT_EXCEEDS_DAILY_LIMIT` | would exceed daily | "Excederías tu límite de 24 horas. Te quedan ${available} disponibles." | "This would exceed your 24-hour limit. You have ${available} remaining." |
| `AMOUNT_EXCEEDS_MONTHLY_LIMIT` | would exceed monthly | "Excederías tu límite mensual. Te quedan ${available} disponibles." | "This would exceed your monthly limit. You have ${available} remaining." |
| `AMOUNT_EXCEEDS_WALLET_LIMIT` | wallet-specific limit | "Este método tiene un límite de ${limit}. Prueba con otro método o divide el envío." | "This method has a ${limit} limit. Try another method or split the transfer." |
| `INVALID_AMOUNT_FORMAT` | can't parse | "No entendí el monto. Por favor ingresa un número como 100 o 100.50" | "I didn't understand the amount. Please enter a number like 100 or 100.50" |

### 13.2 Recipient Errors

| Error Code | Condition | User Message (Spanish) | User Message (English) |
|------------|-----------|------------------------|------------------------|
| `RECIPIENT_NOT_FOUND` | invalid ID | "No encontré ese beneficiario. ¿Quieres agregar uno nuevo?" | "I couldn't find that recipient. Would you like to add a new one?" |
| `INVALID_RECIPIENT_NAME` | empty/invalid | "Necesito el nombre completo del beneficiario (nombre y apellido)" | "I need the recipient's full name (first and last name)" |
| `RECIPIENT_COUNTRY_MISMATCH` | wrong country | "Este beneficiario es de {country}, pero seleccionaste {selected}." | "This recipient is in {country}, but you selected {selected}." |
| `DUPLICATE_RECIPIENT` | already exists | "Ya tienes un beneficiario con este nombre. ¿Quieres usarlo?" | "You already have a recipient with this name. Would you like to use it?" |

### 13.3 Delivery Method Errors

| Error Code | Condition | User Message (Spanish) | User Message (English) |
|------------|-----------|------------------------|------------------------|
| `INVALID_ACCOUNT_NUMBER` | wrong format | "El número de cuenta no parece válido. Por favor verifica que tenga {expected} dígitos." | "The account number doesn't look valid. Please verify it has {expected} digits." |
| `INVALID_CLABE` | wrong CLABE | "La CLABE debe tener 18 dígitos. Por favor verifica el número." | "The CLABE must be 18 digits. Please verify the number." |
| `INVALID_CARD_NUMBER` | wrong card | "El número de tarjeta no es válido. Debe tener 16 dígitos." | "The card number is invalid. It should be 16 digits." |
| `BANK_NOT_SUPPORTED` | unsupported bank | "Lo siento, no podemos enviar a {bank} por el momento. Prueba con otro banco." | "Sorry, we can't send to {bank} at the moment. Please try another bank." |
| `DELIVERY_METHOD_UNAVAILABLE` | not available | "Este método de envío no está disponible para {country}." | "This delivery method isn't available for {country}." |
| `NAME_VALIDATION_FAILED` | name mismatch | "El nombre no coincide con el titular de la cuenta. Por favor verifica los datos." | "The name doesn't match the account holder. Please verify the information." |

### 13.4 Transfer Errors

| Error Code | Condition | User Message (Spanish) | User Message (English) |
|------------|-----------|------------------------|------------------------|
| `TRANSFER_NOT_FOUND` | invalid ID | "No encontré ese envío. ¿Quieres ver tu historial de envíos?" | "I couldn't find that transfer. Would you like to see your transfer history?" |
| `TRANSFER_NOT_CANCELLABLE` | wrong state | "Este envío ya no se puede cancelar porque {reason}." | "This transfer can't be cancelled anymore because {reason}." |
| `TRANSFER_ALREADY_COMPLETED` | already done | "Este envío ya fue completado y el dinero fue entregado." | "This transfer is already complete and the money was delivered." |
| `RATE_EXPIRED` | rate too old | "El tipo de cambio cambió. El nuevo rate es {rate}. ¿Deseas continuar?" | "The exchange rate changed. The new rate is {rate}. Would you like to continue?" |
| `PAYMENT_FAILED` | payment issue | "Hubo un problema con el pago. Por favor intenta de nuevo o usa otro método de pago." | "There was a problem with the payment. Please try again or use another payment method." |

### 13.5 Compliance/KYC Errors

| Error Code | Condition | User Message (Spanish) | User Message (English) |
|------------|-----------|------------------------|------------------------|
| `KYC_REQUIRED` | needs upgrade | "Para enviar ${amount}, necesitas verificar tu identidad. Solo toma unos minutos." | "To send ${amount}, you need to verify your identity. It only takes a few minutes." |
| `KYC_PENDING` | in review | "Tu verificación está en proceso. Te notificaremos cuando esté lista." | "Your verification is in progress. We'll notify you when it's ready." |
| `KYC_FAILED` | verification failed | "No pudimos verificar tu identidad. Un agente te contactará para ayudarte." | "We couldn't verify your identity. An agent will contact you to help." |
| `COMPLIANCE_HOLD` | under review | "Tu envío está siendo revisado por nuestro equipo. Te contactaremos pronto." | "Your transfer is being reviewed by our team. We'll contact you soon." |
| `ACCOUNT_BLOCKED` | banned user | "Tu cuenta ha sido suspendida. Por favor contacta a soporte." | "Your account has been suspended. Please contact support." |
| `SUSPECTED_FRAUD` | fraud flag | "Detectamos actividad inusual. Un agente te contactará para verificar." | "We detected unusual activity. An agent will contact you to verify." |

### 13.6 System Errors

| Error Code | Condition | User Message (Spanish) | User Message (English) |
|------------|-----------|------------------------|------------------------|
| `SERVICE_UNAVAILABLE` | system down | "Estamos experimentando problemas técnicos. Por favor intenta en unos minutos." | "We're experiencing technical issues. Please try again in a few minutes." |
| `RATE_SERVICE_ERROR` | can't get rate | "No pudimos obtener el tipo de cambio. Por favor intenta de nuevo." | "We couldn't get the exchange rate. Please try again." |
| `ORDER_CREATION_FAILED` | can't create | "Hubo un error al procesar tu envío. Un agente te ayudará." | "There was an error processing your transfer. An agent will help you." |
| `UNKNOWN_ERROR` | catch-all | "Algo salió mal. ¿Te gustaría hablar con un agente?" | "Something went wrong. Would you like to talk to an agent?" |

---

## 14. MOCK DATA EXAMPLES

### 14.1 Sample Recipients (for testing)

```json
[
  {
    "id": "rec_mock_001",
    "name": { "first_name": "Maria", "last_name": "Garcia", "display_name": "Maria Garcia" },
    "country": "MX",
    "delivery_methods": [
      { "id": "dm_mock_001", "type": "BANK", "display_name": "BBVA ****5678" }
    ]
  },
  {
    "id": "rec_mock_002",
    "name": { "first_name": "Juan", "last_name": "Lopez", "display_name": "Juan Lopez" },
    "country": "MX",
    "delivery_methods": [
      { "id": "dm_mock_002", "type": "CASH", "display_name": "Cash - Guadalajara" }
    ]
  },
  {
    "id": "rec_mock_003",
    "name": { "first_name": "Carlos", "last_name": "Martinez", "display_name": "Carlos Martinez" },
    "country": "CO",
    "delivery_methods": [
      { "id": "dm_mock_003", "type": "WALLET", "display_name": "Nequi ****7890" }
    ]
  }
]
```

### 14.2 Sample Transfer History

```json
[
  {
    "id": "txn_mock_001",
    "status": "COMPLETE",
    "recipient_name": "Maria Garcia",
    "amount_sent": 100.00,
    "amount_received": 1725.00,
    "currency": "MXN",
    "created_at": "2026-01-10T10:00:00Z"
  },
  {
    "id": "txn_mock_002",
    "status": "IN_PROGRESS",
    "recipient_name": "Juan Lopez",
    "amount_sent": 200.00,
    "amount_received": 3450.00,
    "currency": "MXN",
    "created_at": "2026-01-11T09:00:00Z"
  }
]
```

### 14.3 Sample Exchange Rates (for mocks)

| Corridor | Rate | Fee ($100) |
|----------|------|------------|
| USD → MXN | 17.25 | $3.99 |
| USD → GTQ | 7.75 | $3.99 |
| USD → HNL | 24.75 | $3.99 |
| USD → COP | 4050 | $3.99 |
| USD → DOP | 57.50 | $3.99 |
| USD → USD (SV) | 1.00 | $3.99 |
| USD → NIO | 36.75 | $3.99 |

---

*Document generated from conversations-api codebase analysis*
*Last updated: January 2026*
