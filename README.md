# KON Action Bridge

> **Enterprise AI Commerce Action Bridge — Governed Autonomous Agents & Observability Gateway**

A production-grade architectural MVP demonstrating how a conversational AI shopping agent (powered by Google Gemini native function calling) interacts with enterprise commerce APIs under a **strict, fail-closed governance gateway**.

Every autonomous tool proposal by the AI must pass schema validation, identity/session ownership verification, permission matrices, and human-in-the-loop authorization before execution. Complete lifecycle observability is captured with OpenTelemetry distributed tracing and cryptographically verifiable audit logs.

---

## 🏛️ Architectural Overview

```
                                  Customer Voice / Chat Message
                                               │
                                               ▼
                              ┌──────────────────────────────────┐
                              │     KON Conversation Engine      │
                              │  (Bounded Multi-Round Loop)      │
                              └────────────────┬─────────────────┘
                                               │
                     Proposes Tool Call        ▼        Explains Tool Output
          ┌────────────────────────────────────────────────────────────────────────┐
          │                                                                        │
          ▼                                                                        │
┌───────────────────────────┐                                                      │
│    Google Gemini GenAI    │                                                      │
│  (Native Function Calling │                                                      │
│   Manual Mode disable=True│                                                      │
│   Configurable Model)     │                                                      │
└─────────────┬─────────────┘                                                      │
              │                                                                    │
              │ Proposes Tool Name + JSON Arguments (search, cart, submit_order)   │
              ▼                                                                    │
┌────────────────────────────────────────────────────────────────────────┐         │
│                 KON FAIL-CLOSED GOVERNANCE GATEWAY                     │         │
│                                                                        │         │
│  1. Tool Registry Verification (Active & Registered)                   │         │
│  2. Strict Pydantic Argument Schema Validation                         │         │
│  3. Agent Permission Matrix Check (Active & Permitted Tool)            │         │
│  4. Policy Engine Evaluation:                                          │         │
│     ├── [DENY] ─────────────► Block Execution + Persist Denial Audit   │         │
│     ├── [REQUIRES_APPROVAL] ► Queue HITL Approval in Admin Console     │         │
│     └── [ALLOW] ────────────► Authorize Execution                      │         │
└────────────────────────────────────────┬───────────────────────────────┘         │
                                         │                                         │
                                         ▼                                         │
                       ┌──────────────────────────────────┐                        │
                       │   Governed Tool Executor         │                        │
                       │  (Commerce APIs / Catalog / DB)  │                        │
                       └─────────────────┬────────────────┘                        │
                                         │                                         │
                                         ▼                                         │
                       ┌──────────────────────────────────┐                        │
                       │   Cryptographic Audit Logger &   │                        │
                       │   OpenTelemetry Trace Pipeline   │                        │
                       └─────────────────┬────────────────┘                        │
                                         │                                         │
                                         └─────────────────────────────────────────┘
                                                Returns Verified Result
```

### Key Architectural Tenets
1. **Gemini Native Tool Selection**: Gemini understands unstructured natural language and proposes structured tool calls using the modern `google-genai` SDK.
2. **Manual Controlled Execution**: `automatic_function_calling` is explicitly **disabled**. The model cannot execute Python functions or touch databases autonomously.
3. **Fail-Closed Governance Gateway**: If a tool, agent status, schema, session ownership, or business boundary fails verification, the action is denied immediately and logged.
4. **Human-in-the-Loop (HITL) Queue**: High-risk actions like `submit_order` trigger a `REQUIRES_APPROVAL` state, queuing in the supervisor console via real-time Server-Sent Events (SSE).
5. **Deterministic Fallback Engine**: If Gemini credentials are not supplied or an upstream network error occurs, the system smoothly falls back to an internal deterministic state-machine agent with 0 downtime.
6. **Separated Telemetry & Precision Latency**: Distinguishes unique agent requests, actual tool invocations, affected items, and policy outcomes, with millisecond-accurate phase profiling (`time.perf_counter()`).

---

## 📁 Repository Structure

```
Kon/
├── backend/                         # FastAPI Python backend
│   ├── app/
│   │   ├── main.py                  # App entrypoint + DB lifespan seeder
│   │   ├── config.py                # Config settings (.env loader)
│   │   ├── database.py              # Async SQLAlchemy + aiosqlite / Postgres
│   │   ├── models/                  # Governance, user, cart, product models
│   │   ├── schemas/                 # Strict Pydantic v2 schemas
│   │   ├── api/                     # Endpoints (auth, chat, cart, admin)
│   │   ├── agents/                  # Gemini native provider + fallback + engine
│   │   ├── tools/                   # Registry schemas + cart/product tools
│   │   ├── governance/              # PolicyEngine, permissions, tool schemas
│   │   ├── observability/           # AuditLogger, metrics, tracing, evaluator
│   │   └── commerce/                # Catalog + basket services + adapters
│   ├── tests/                       # 21 automated pytest scenarios
│   ├── seed.py                      # Database seeder (catalog, 4 AI employees)
│   ├── requirements.txt
│   ├── .dockerignore
│   └── Dockerfile
├── frontend/                        # Next.js 14 App Router + TypeScript + Tailwind
│   ├── app/
│   │   ├── page.tsx                 # Landing presentation
│   │   ├── login/                   # Secure authentication
│   │   ├── shop/                    # Voice & text shopping interface
│   │   └── admin/                   # Enterprise Governance Dashboard (8 modules)
│   │       ├── page.tsx             # Overview KPI metrics & rates
│   │       ├── approvals/           # HITL Supervisor Authorization Queue
│   │       ├── traces/              # Distributed Trace Span Explorer
│   │       ├── agents/              # Enterprise AI Employee Directory
│   │       ├── tools/               # Tool Registry & JSON Schema definitions
│   │       ├── policies/            # Live Policy Matrix & principles
│   │       ├── logs/                # Cryptographic Activity & Audit Log
│   │       ├── security/            # Security Denials & Blocked Actions
│   │       └── evaluations/         # Conversation Quality Checks
│   ├── lib/                         # Axios client with auto-refresh + types
│   └── Dockerfile
├── docker-compose.yml               # Multi-container orchestration (Backend + Frontend + Jaeger)
├── .env.example
└── README.md
```

---

## ⚡ Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (including modern google-genai SDK)
pip install -r requirements.txt

# Seed the database (creates 17 catalog products, default users, 4 AI employees)
python seed.py

# Start backend server
uvicorn app.main:app --reload --port 8000
```
* Backend API: **http://localhost:8000**
* Interactive Swagger Docs: **http://localhost:8000/docs**

### 2. Frontend Setup

```bash
cd frontend

# Install Node modules
npm install

# Start development server
npm run dev
```
* Shop & Admin Portal: **http://localhost:3000**

---

## 🐳 Docker Deployment

Run the complete multi-service stack with one command:

```bash
docker-compose up --build
```

Services exposed:
* **Frontend Web App**: http://localhost:3000
* **Backend Governance API**: http://localhost:8000
* **Jaeger Distributed Tracing UI**: http://localhost:16686

---

## 🔑 Demo Credentials

| Role | Username | Password | Purpose |
|------|----------|----------|---------|
| **Enterprise Admin** | `admin` | `admin123` | Full access to Governance Console & Approvals |
| **Retail Customer** | `demo_customer` | `customer123` | Conversational Shopping Experience |

---

## 🤖 AI Employees Directory

The system models AI agents as recognized enterprise employees with defined departments, assigned models, and strict tool boundaries:

| Agent ID | Employee Name | Department | Model & Provider | Permitted Tools |
| :--- | :--- | :--- | :--- | :--- |
| `kon-shopping-agent` | KON Retail Commerce Assistant | Retail Commerce | Google Gemini (`gemini-3.5-flash-lite`) | `search_products`, `get_product_details`, `add_to_cart`, `update_cart_item`, `remove_from_cart`, `get_cart`, `get_checkout_preview`, `submit_order` |
| `kon-support-agent` | KON Customer Care Agent | Customer Care | Anthropic Claude (`claude-3-5-sonnet`) | `search_faq`, `track_delivery`, `open_ticket` |
| `kon-finance-agent` | KON Invoicing & Settlement Agent | Finance & Accounting | OpenAI (`gpt-4o`) | `query_ledger`, `generate_invoice` |
| `kon-hr-agent` | KON Employee Operations Agent | Human Resources | OpenAI (`gpt-4o-mini`) | `search_hr_policy`, `request_leave` |

Administrators can toggle employee status (1-click active/inactive) and update tool permissions dynamically in `/admin/agents`.

---

## 🛡️ Governance & Policy Controls

### Registered Commerce Tools (7 Standard Tools)
1. `search_products`: Query catalog by keyword or category.
2. `get_product_details`: Lookup product pricing and live inventory by UUID.
3. `add_to_cart`: Add product by UUID with positive quantity. Prices are **strictly read from the database**, never from user input or LLM claims.
4. `update_cart_item`: Adjust quantity of an existing item in the customer's session.
5. `remove_from_cart`: Delete an item from the customer's session.
6. `get_cart`: Read current subtotal and tax calculation in AED.
7. `get_checkout_preview`: Generate pre-checkout pricing breakdown (non-binding).
8. `submit_order`: Request order submission. Classified as **HIGH RISK** requiring human supervisor authorization.

### Human-in-the-Loop (HITL) Workflow
* When an agent requests `submit_order`, the Policy Engine returns `REQUIRES_APPROVAL`.
* A pending `ApprovalRequest` record is written to the database with itemized cart details and risk rating.
* Real-time SSE alert `approval_request` appears on `/admin/approvals`.
* An administrator reviews and either **Approves** or **Rejects** the action with audit notes.
* *Honest Boundary*: In this MVP, approvals record the supervisor decision for demonstration; no real financial card charge or physical courier delivery is executed.
* State transitions accept decisions **only** when requests are in `pending` status.

---

## 🧪 Automated Test Suite (21 Passing Tests)

Run the comprehensive pytest test suite covering all security, governance, and tracing scenarios:

```bash
cd backend
python -m pytest tests/test_scenarios.py -v
```

### Verified Test Matrix:
| Test # | Test Scenario | Description |
|:---|:---|:---|
| **Test 1** | Normal Shopping Journey | End-to-end multi-turn catalog search and cart addition. |
| **Test 2** | Block Unregistered Tool | Attempts `admin_drop_database` $\rightarrow$ Denied with `tool_not_registered`. |
| **Test 3** | Block Inactive Agent | Deactivated agent attempts tool execution $\rightarrow$ Denied. |
| **Test 4** | Block Unauthorized Tool | Agent attempts tool outside its permitted tool list $\rightarrow$ Denied. |
| **Test 5** | Add to Cart Validation | Validates positive quantity and catalog stock checks. |
| **Test 6** | Update & Remove Items | Verifies cart item mutations and basket recalculation. |
| **Test 7** | Session Isolation | Ensures customer A cannot read or modify customer B's basket. |
| **Test 8** | Failure Handling | Simulates upstream commerce exception $\rightarrow$ Recorded as execution failure in audit trail. |
| **Test 9** | Conversational Add to Cart | Natural speech command adds items directly to basket. |
| **Test 10** | Semantic Disambiguation | Product with variants prompts interactive clarification choice. |
| **Test 11** | Fail-Closed Token Auth | Missing/expired JWT returns 401 Unauthorized securely. |
| **Test 12** | Multi-Item Batch Validation | Validates every item in multi-product commands; rejects invalid sub-items. |
| **Test 13** | Unit Conversion Engine | Converts grams to canonical kilograms accurately. |
| **Test 14** | Hallucination Prevention | Model claiming addition of out-of-stock item is flagged in Quality Checks. |
| **Test 15** | Pydantic Schema Enforcement | Malformed JSON parameters rejected before executor dispatch. |
| **Test 16** | Registry Persistence | Administrator modifications persist safely across application restarts. |
| **Test 17** | SHA-256 Audit Immutability | Verifies cryptographic hash chain integrity of the audit log. |
| **Test 18** | Request Journey Spans | Confirms root-to-leaf span timings (`request_received`, `ai_inference`, etc.). |
| **Test 19** | Separated Telemetry Metrics | Non-skewed separated calculations for requests, tool calls, and latencies. |
| **Test 20** | HITL Approval Workflow | High-risk `submit_order` intercepts into pending approval queue; blocks re-approval. |
| **Test 21** | AI Employee Directory | Dynamic request/failure counters, 1-click status toggle, and permission edits. |

---

## 📊 Observability & Telemetry

### Trace Journey Timeline
Every conversation turn creates an end-to-end trace with parent/child spans:
1. `request_received` (Context validation & normalization)
2. `ai_inference` (Gemini function-calling turn latency)
3. `policy_evaluation` (Fail-closed authorization check)
4. `tool_execution` (Commerce API execution latency measured accurately via `time.perf_counter()`)
5. `audit_persistence` (Cryptographic log recording)
6. `avatar_response` (Neural TTS speech generation)

Inspect live traces directly in the internal **Trace Explorer** (`/admin/traces`) or in **Jaeger** (`http://localhost:16686`).

---

## 🔒 Security Best Practices
* **No Database Access for LLM**: The model never touches SQL, database connections, or shell environments.
* **Backend Pricing Authority**: Prices and stock are read solely from authoritative database records.
* **Automatic Silent Token Renewal**: The frontend Axios client automatically renews expired session tokens via `/auth/login` to ensure uninterrupted customer experience while enforcing strict fail-secure JWT validation on the backend.
* **Docker Image Hygiene**: Includes a `.dockerignore` preventing `.env`, SQLite databases, and caches from being copied into container images.
