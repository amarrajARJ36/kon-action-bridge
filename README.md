# KON Action Bridge

> **Enterprise AI Commerce Action Bridge — Governed Autonomous Agents & Observability Gateway**

An **enterprise-oriented engineering prototype** demonstrating how a conversational AI shopping agent (powered by Google Gemini native function calling) interacts with enterprise commerce APIs under a **strict, fail-closed governance gateway**.

Every autonomous tool proposal by the AI must pass schema validation, identity and session ownership verification, dynamic permission matrices, and human-in-the-loop authorization prior to execution. Complete lifecycle observability is captured with OpenTelemetry distributed tracing and SHA-256 hash-chained, tamper-evident audit logging.

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
                       │   SHA-256 Tamper-Evident Logger  │                        │
                       │   & OpenTelemetry Trace Pipeline │                        │
                       └─────────────────┬────────────────┘                        │
                                         │                                         │
                                         └─────────────────────────────────────────┘
                                                Returns Verified Result
```

### Key Architectural Tenets
1. **Gemini Native Tool Selection**: Gemini parses unstructured natural language and proposes structured tool calls using the official `google-genai` SDK.
2. **Manual Controlled Execution**: `automatic_function_calling` is explicitly **disabled**. The model cannot execute Python functions or touch databases autonomously.
3. **Fail-Closed Governance Gateway**: If a tool, agent status, schema, session ownership, or business boundary fails verification, the action is denied immediately and logged.
4. **Human-in-the-Loop (HITL) Queue**: High-risk actions like `submit_order` trigger a `REQUIRES_APPROVAL` state, queuing in the supervisor console via real-time Server-Sent Events (SSE).
5. **Tamper-Evident Audit Logging**: Implements SHA-256 cryptographic hash chaining (`prev_hash` $\to$ `entry_hash`). Any retroactive row alteration, insertion, or deletion breaks chain integrity and is flagged via the verification endpoint.
6. **Deterministic Fallback Engine**: If Gemini credentials are not supplied or an upstream network error occurs, the system smoothly falls back to an internal deterministic state-machine agent with 0 downtime.
7. **Separated Telemetry & Precision Latency**: Distinguishes unique agent requests, actual tool invocations, affected items, and policy outcomes, with millisecond-accurate phase profiling (`time.perf_counter()`).

---

## 📁 Repository Structure

```
Kon/
├── backend/                         # FastAPI Python 3.13 backend
│   ├── app/
│   │   ├── main.py                  # App entrypoint + DB lifespan seeder
│   │   ├── config.py                # Config settings (.env loader)
│   │   ├── database.py              # Async SQLAlchemy + Neon PostgreSQL / SQLite
│   │   ├── models/                  # Governance, user, cart, product models
│   │   ├── schemas/                 # Strict Pydantic v2 schemas
│   │   ├── api/                     # Endpoints (auth, chat, cart, admin)
│   │   ├── agents/                  # Gemini native provider + fallback + engine
│   │   ├── tools/                   # Registry schemas + cart/product tools
│   │   ├── governance/              # PolicyEngine, permissions, tool schemas
│   │   ├── observability/           # AuditLogger, metrics, tracing, evaluator
│   │   └── commerce/                # Catalog + basket services + adapters
│   ├── tests/                       # 21 automated pytest scenarios
│   ├── seed.py                      # Database seeder (catalog, AI employees)
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
│   │       ├── logs/                # Tamper-Evident Activity & Audit Log
│   │       └── security/            # Security Denials & Blocked Actions
│   ├── lib/                         # Axios client with auto-refresh + types
│   └── Dockerfile
├── start_jaeger.sh                  # 1-click standalone Jaeger launcher for macOS
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

# Install dependencies
pip install -r requirements.txt

# Seed the database (creates catalog products, roles, AI employees)
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

## 🔑 Authentication & Evaluation Accounts

| Role | Test Username | Credential Management | Scope & Capabilities |
| :--- | :--- | :--- | :--- |
| **Retail Customer** | `demo_customer` | Auto-initialized for demo / `customer123` | Conversational grocery shopping, basket management, voice interface |
| **Enterprise Supervisor** | `admin` | Set securely via `.env` / Admin Setup | Governance Console, HITL Approvals, Agent & Tool Management, Trace Explorer |

> [!IMPORTANT]
> **Administrative Credential Security**: In adherence to secure engineering standards, administrative passwords are not published in public documentation. For evaluation and development environments, administrative credentials are initialized from local environment configurations (`.env`) or securely seeded via `backend/seed.py`.

---

## 🤖 AI Employees Directory

The system models AI agents as recognized enterprise employees with defined departments, assigned models, and strict tool boundaries:

| Agent ID | Employee Name | Department | Model & Provider | Permitted Tools |
| :--- | :--- | :--- | :--- | :--- |
| `kon-shopping-agent` | KON Retail Commerce Assistant | Retail Commerce | Google Gemini (`gemini-2.5-flash-lite`) | `search_products`, `get_product_details`, `add_to_cart`, `update_cart_item`, `remove_from_cart`, `get_cart`, `get_checkout_preview`, `submit_order` |
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
* *Prototype Boundary*: In this engineering prototype, approvals record the supervisor decision for demonstration; no real financial card charge or physical courier delivery is executed.
* State transitions accept decisions **only** when requests are in `pending` status.

---

## 📜 Tamper-Evident Audit Logging (SHA-256 Hash Chain)

Rather than claiming unconditional database immutability, KON Action Bridge implements **cryptographic SHA-256 hash chaining** to ensure verifiable **tamper-evidence**:

* **Hash Formula**:
  $$\text{entry\_hash} = \text{SHA256}(\text{prev\_hash} \,\|\, \text{event\_id} \,\|\, \text{trace\_id} \,\|\, \text{action} \,\|\, \text{decision} \,\|\, \text{status} \,\|\, \text{resource})$$
* **Genesis Anchor**: The initial entry binds to `GENESIS_ROOT_HASH_00000000000000000000000000000000000000000000`.
* **Tamper-Evidence**: Any retroactive row modification, dropped event, or injected record creates a hash mismatch across the chain.
* **Integrity Endpoint**: `/admin/audit-logs-verify-chain` programmatically verifies the sequential hash chain across all records and pinpoints the exact record index if tampering occurs.

---

## 📊 Observability & OpenTelemetry Distributed Tracing

### Distributed Trace Pipeline
Every conversation turn creates an end-to-end W3C-standard trace with parent/child spans:
1. `request_received` (Context validation & normalization)
2. `ai_inference` (Gemini function-calling turn latency)
3. `policy_evaluation` (Fail-closed authorization check)
4. `tool_execution` (Commerce API execution latency measured accurately via `time.perf_counter()`)
5. `audit_persistence` (Cryptographic log recording)
6. `avatar_response` (Neural TTS speech generation)

### Inspecting Traces
* **In-App Trace Explorer**: Navigate to `/admin/traces` for visual waterfall journeys, span hierarchy, and stage latencies.
* **External Jaeger UI**: Traces are broadcast to the local OpenTelemetry collector on port `4318`. View traces in Jaeger at **`http://localhost:16686`**.
* **macOS 1-Click Jaeger**: On macOS (Apple Silicon `arm64`), run `./start_jaeger.sh` to download and launch the standalone binary instantly without Docker.

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
| **Test 17** | TTS Endpoint Security | Authenticates voice synthesis requests and enforces maximum character limits. |
| **Test 18** | Request Journey Spans | Confirms root-to-leaf span timings (`request_received`, `ai_inference`, etc.). |
| **Test 19** | Separated Telemetry Metrics | Non-skewed separated calculations for requests, tool calls, and latencies. |
| **Test 20** | HITL Approval Workflow | High-risk `submit_order` intercepts into pending approval queue; blocks re-approval. |
| **Test 21** | AI Employee Directory | Dynamic request/failure counters, 1-click status toggle, and permission edits. |

---

## 🔒 Security Best Practices
* **No Database Access for LLM**: The model never touches SQL, database connections, or shell environments.
* **Backend Pricing Authority**: Prices and stock are read solely from authoritative database records.
* **Automatic Silent Token Renewal**: The frontend Axios client automatically renews expired session tokens via `/auth/login` to ensure uninterrupted customer experience while enforcing strict fail-secure JWT validation on the backend.
* **Docker Image Hygiene**: Includes a `.dockerignore` preventing `.env`, SQLite databases, and caches from being copied into container images.
