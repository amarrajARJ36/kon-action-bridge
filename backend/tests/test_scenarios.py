import asyncio
import uuid
from decimal import Decimal
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.auth import create_access_token, get_password_hash
from app.config import settings
from app.database import Base, get_db
from app.governance.permissions import AgentPermissions
from app.governance.policy_engine import policy_engine
from app.main import app
from app.models.cart import Cart, CartItem
from app.models.governance import AgentRegistry, AuditLog, ToolRegistry
from app.models.product import Product
from app.models.user import User
from app.observability.audit_logger import audit_logger
from app.tools.cart_tools import cart_tools, tool_executor
from app.tools.product_tools import product_tools
from app.tools.registry import tool_registry_service

# Isolated Test Database
TEST_DB_URL = "sqlite+aiosqlite:///./test_kon_scenarios.db"
test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

CUSTOMER_USER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
ADMIN_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_B_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

PRODUCT_ATTA_ID = uuid.UUID("11111111-1111-1111-1111-111111111101")
PRODUCT_CHICKEN_ID = uuid.UUID("33333333-3333-3333-3333-333333333301")


@pytest_asyncio.fixture(scope="session", autouse=True)
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        # Seed Admin
        admin = User(
            id=ADMIN_USER_ID,
            username="admin",
            email="admin@kon.local",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True,
        )
        # Seed Customer A
        customer_a = User(
            id=CUSTOMER_USER_ID,
            username="demo_customer",
            email="customer@kon.local",
            hashed_password=get_password_hash("customer123"),
            role="customer",
            is_active=True,
        )
        # Seed Customer B
        customer_b = User(
            id=USER_B_ID,
            username="customer_b",
            email="customer_b@kon.local",
            hashed_password=get_password_hash("customer123"),
            role="customer",
            is_active=True,
        )
        session.add_all([admin, customer_a, customer_b])

        # Seed Tools and Agent
        await tool_registry_service.initialize_tools(session)
        agents = [
            AgentRegistry(
                agent_id=AgentPermissions.SHOPPING_AGENT_ID,
                name="KON Retail Commerce Assistant",
                description="Autonomous commerce assistant handling grocery catalog queries and basket operations under strict governance.",
                role="shopping_assistant",
                department="Retail Commerce",
                model_provider="Google Gemini",
                model_version="gemini-1.5-pro",
                owner_tenant="KON Retail Org",
                status="active",
                allowed_tools=AgentPermissions.ALLOWED_TOOLS_SHOPPING_AGENT,
            ),
            AgentRegistry(
                agent_id="kon-support-agent",
                name="KON Customer Care Agent",
                description="Assists shoppers with FAQ resolution, delivery tracking, and returns policies.",
                role="customer_support",
                department="Customer Care",
                model_provider="Anthropic Claude",
                model_version="claude-3-5-sonnet",
                owner_tenant="KON Support Ops",
                status="active",
                allowed_tools=["search_faq", "track_delivery", "open_ticket"],
            ),
            AgentRegistry(
                agent_id="kon-finance-agent",
                name="KON Invoicing & Settlement Agent",
                description="Internal corporate agent for merchant reconciliation and tax reporting.",
                role="finance_specialist",
                department="Finance & Accounting",
                model_provider="OpenAI GPT-4",
                model_version="gpt-4o",
                owner_tenant="KON Corporate Finance",
                status="active",
                allowed_tools=["query_ledger", "generate_invoice"],
            ),
            AgentRegistry(
                agent_id="kon-hr-agent",
                name="KON Employee Operations Agent",
                description="Internal HR representative managing internal employee policy inquiries.",
                role="hr_specialist",
                department="Human Resources",
                model_provider="OpenAI GPT-4",
                model_version="gpt-4o-mini",
                owner_tenant="KON Internal HR",
                status="active",
                allowed_tools=["search_hr_policy", "request_leave"],
            ),
        ]
        session.add_all(agents)

        # Seed Products
        p_atta = Product(
            id=PRODUCT_ATTA_ID,
            sku="ATTA-ALBAKER-01",
            name="Al Baker Chakki Atta",
            brand="Al Baker",
            category="Atta",
            variant="Chakki Fresh Atta",
            unit_of_measurement="kg",
            price_aed=Decimal("8.50"),
            stock_quantity=200.0,
            is_available=True,
        )
        p_chicken1 = Product(
            id=PRODUCT_CHICKEN_ID,
            sku="CHK-WHOLE-01",
            name="Whole Chicken",
            brand="Al Rawdah",
            category="Chicken",
            variant="Fresh Whole Chicken",
            unit_of_measurement="kg",
            price_aed=Decimal("22.00"),
            stock_quantity=100.0,
            is_available=True,
        )
        p_chicken2 = Product(
            id=uuid.UUID("33333333-3333-3333-3333-333333333302"),
            sku="CHK-BREAST-01",
            name="Chicken Breast",
            brand="Al Rawdah",
            category="Chicken",
            variant="Fresh Boneless Breast Fillet",
            unit_of_measurement="kg",
            price_aed=Decimal("38.50"),
            stock_quantity=80.0,
            is_available=True,
        )
        p_chicken3 = Product(
            id=uuid.UUID("33333333-3333-3333-3333-333333333303"),
            sku="CHK-CUBES-01",
            name="Boneless Chicken Cubes",
            brand="Al Rawdah",
            category="Chicken",
            variant="Fresh Boneless Cubes",
            unit_of_measurement="kg",
            price_aed=Decimal("35.00"),
            stock_quantity=60.0,
            is_available=True,
        )
        session.add_all([p_atta, p_chicken1, p_chicken2, p_chicken3])
        await session.commit()

        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from app.agents.conversation import conversation_engine
    from app.agents.llm_provider import FallbackProvider

    original_provider = conversation_engine.provider
    conversation_engine.provider = FallbackProvider()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    conversation_engine.provider = original_provider


@pytest.fixture
def customer_headers() -> dict:
    token = create_access_token(
        user_id=str(CUSTOMER_USER_ID),
        username="demo_customer",
        role="customer",
        session_id="customer-session-1",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_b_headers() -> dict:
    token = create_access_token(
        user_id=str(USER_B_ID),
        username="customer_b",
        role="customer",
        session_id="customer-b-session",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers() -> dict:
    token = create_access_token(
        user_id=str(ADMIN_USER_ID),
        username="admin",
        role="admin",
        session_id="admin-session",
    )
    return {"Authorization": f"Bearer {token}"}


# =========================================================================
# TEST 1: Normal Shopping Journey
# POST /chat/message "I need 2 kg atta", verify audit log created, no DB error
# =========================================================================
@pytest.mark.asyncio
async def test_normal_shopping_journey(
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
):
    payload = {
        "message": "I need 2 kg atta",
        "session_id": "journey-session-1",
    }
    response = await client.post("/chat/message", json=payload, headers=customer_headers)
    assert response.status_code == 200
    data = response.json()
    assert "atta" in data["message"].lower() or "chakki" in data["message"].lower()

    # Verify audit log was created in DB
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.user_id == str(CUSTOMER_USER_ID),
            AuditLog.session_id == "journey-session-1",
        )
    )
    res = await db_session.execute(stmt)
    logs = res.scalars().all()
    assert len(logs) >= 1
    assert logs[0].governance_decision == "allowed"
    assert logs[0].execution_status == "success"


# =========================================================================
# TEST 2: Ambiguous Product
# search_products "chicken", verify multiple results returned, no auto-add
# =========================================================================
@pytest.mark.asyncio
async def test_ambiguous_product(
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
):
    # Perform search directly via product tools
    products = await product_tools.search_products(query="chicken", db=db_session)
    assert len(products) >= 3  # Whole chicken, breast, boneless cubes

    # Verify user cart remains empty (no auto-add)
    cart = await cart_tools.get_cart(
        user_id=CUSTOMER_USER_ID,
        session_id="ambiguous-session",
        db=db_session,
    )
    assert len(cart.items) == 0
    assert cart.grand_total_aed == 0.0


# =========================================================================
# TEST 3: Unavailable Product
# set stock=0 on a product, attempt add_to_cart, expect 400 or controlled error
# =========================================================================
@pytest.mark.asyncio
async def test_unavailable_product(
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
):
    # Set stock of atta to 0
    stmt = select(Product).where(Product.id == PRODUCT_ATTA_ID)
    res = await db_session.execute(stmt)
    product = res.scalar_one()
    product.stock_quantity = 0.0
    await db_session.commit()

    # Attempt to add out-of-stock product via API
    add_payload = {
        "product_id": str(PRODUCT_ATTA_ID),
        "quantity": 1.0,
    }
    response = await client.post(
        "/cart/items?session_id=stock-session",
        json=add_payload,
        headers=customer_headers,
    )
    assert response.status_code == 400
    assert "Insufficient inventory" in response.json()["detail"]


# =========================================================================
# TEST 4: Unauthorized Tool
# Manually call PolicyEngine.check() with agent trying tool not in allowed_tools
# =========================================================================
@pytest.mark.asyncio
async def test_unauthorized_tool(db_session: AsyncSession):
    decision = await policy_engine.check(
        agent_id="kon-shopping-agent",
        tool_name="unauthorized_database_drop",
        params={},
        session_context={"user_id": str(CUSTOMER_USER_ID), "session_id": "sec-test"},
        db=db_session,
    )
    assert decision.allowed is False
    assert "not registered" in decision.reason or "not permitted" in decision.reason


# =========================================================================
# TEST 5: Invalid Quantity
# attempt add_to_cart with quantity=-1, expect validation error
# =========================================================================
@pytest.mark.asyncio
async def test_invalid_quantity(
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
):
    # 1. API validation test
    payload = {
        "product_id": str(PRODUCT_ATTA_ID),
        "quantity": -1.0,
    }
    response = await client.post(
        "/cart/items?session_id=qty-session",
        json=payload,
        headers=customer_headers,
    )
    assert response.status_code == 422  # Pydantic validation rejection

    # 2. Policy engine validation check
    policy_check = await policy_engine.check(
        agent_id="kon-shopping-agent",
        tool_name="add_to_cart",
        params={"product_id": str(PRODUCT_ATTA_ID), "quantity": -5.0},
        session_context={"user_id": str(CUSTOMER_USER_ID), "session_id": "qty-session"},
        db=db_session,
    )
    assert policy_check.allowed is False
    assert "quantity must be > 0" in policy_check.reason


# =========================================================================
# TEST 6: Checkout Boundary
# call get_checkout_preview, verify no order is created, verify audit log
# =========================================================================
@pytest.mark.asyncio
async def test_checkout_boundary(
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
):
    # Add an item first
    await cart_tools.add_to_cart(
        product_id=PRODUCT_ATTA_ID,
        quantity=2.0,
        user_id=CUSTOMER_USER_ID,
        session_id="checkout-session",
        db=db_session,
    )

    # Call checkout preview endpoint
    response = await client.get(
        "/cart/checkout-preview?session_id=checkout-session",
        headers=customer_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "NON-BINDING CHECKOUT PREVIEW" in data["note"]
    assert data["subtotal_aed"] == 17.00  # 2 * 8.50 AED
    assert data["vat_aed"] == 0.85        # 5% UAE VAT
    assert data["grand_total_aed"] == 17.85  # Subtotal + VAT

    # Ensure items remain in cart (not wiped by preview)
    cart = await cart_tools.get_cart(
        user_id=CUSTOMER_USER_ID,
        session_id="checkout-session",
        db=db_session,
    )
    assert len(cart.items) == 1


# =========================================================================
# TEST 7: Tenant / Session Isolation
# Create two users with different sessions; User B cannot access User A's cart
# =========================================================================
@pytest.mark.asyncio
async def test_tenant_session_isolation(
    client: AsyncClient,
    customer_headers: dict,
    user_b_headers: dict,
    db_session: AsyncSession,
):
    # User A adds item to their cart directly via DB
    cart_a_obj = await cart_tools.get_or_create_cart(
        user_id=CUSTOMER_USER_ID,
        session_id="session-user-a",
        db=db_session,
    )
    new_item = CartItem(
        cart_id=cart_a_obj.id,
        product_id=PRODUCT_ATTA_ID,
        quantity=1.0,
        unit_price_aed=Decimal("8.50"),
    )
    db_session.add(new_item)
    await db_session.commit()
    await db_session.refresh(new_item)
    item_a_id = new_item.id

    # User B tries to update User A's cart item
    update_payload = {"quantity": 5.0}
    res_update = await client.put(
        f"/cart/items/{item_a_id}?session_id=session-user-b",
        json=update_payload,
        headers=user_b_headers,
    )
    # Must fail because cart item belongs to User A
    assert res_update.status_code in (400, 404)

    # User B tries to delete User A's cart item
    res_delete = await client.delete(
        f"/cart/items/{item_a_id}?session_id=session-user-b",
        headers=user_b_headers,
    )
    assert res_delete.status_code in (400, 404)

    # User B's own cart must be completely empty
    cart_b_res = await client.get(
        "/cart?session_id=session-user-b",
        headers=user_b_headers,
    )
    assert cart_b_res.status_code == 200
    assert len(cart_b_res.json()["items"]) == 0


# =========================================================================
# TEST 8: Failure Handling
# mock a commerce tool exception, verify audit log shows 'failed' status
# =========================================================================
@pytest.mark.asyncio
async def test_failure_handling(
    monkeypatch,
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
):
    async def mock_execute_failure(*args, **kwargs):
        raise RuntimeError("Commerce provider upstream connection timeout")

    # Monkeypatch the executor execute method
    monkeypatch.setattr(tool_executor, "execute", mock_execute_failure)

    # Send chat message that would trigger tool call
    # Use "add 1 unit of <UUID>" pattern so quantity=1.0 passes governance
    # and the monkeypatched executor raises RuntimeError
    payload = {
        "message": f"add 1 kg of product {PRODUCT_ATTA_ID}",
        "session_id": "fail-session-1",
    }
    response = await client.post("/chat/message", json=payload, headers=customer_headers)
    assert response.status_code == 200
    data = response.json()
    assert "Tool execution failed" in data["message"]

    # Verify audit log captures failed status and error message
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.user_id == str(CUSTOMER_USER_ID),
            AuditLog.session_id == "fail-session-1",
        )
    )
    res = await db_session.execute(stmt)
    logs = res.scalars().all()
    assert len(logs) >= 1
    assert logs[0].governance_decision == "allowed"
    assert logs[0].execution_status == "failed"
    assert "upstream connection timeout" in logs[0].denial_reason


# =========================================================================
# TEST 9: Conversational Add to Cart
# Send natural voice/text command "Add 2 kg of Al Baker atta"
# Verify item added directly to cart, basket_updated=True
# =========================================================================
@pytest.mark.asyncio
async def test_conversational_add_to_cart(
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
):
    # 1. Direct speech/text addition
    payload = {
        "message": "Add 2 kg of Al Baker atta",
        "session_id": "speech-add-session",
    }
    response = await client.post("/chat/message", json=payload, headers=customer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["basket_updated"] is True
    assert data["action_taken"] == "add_to_cart"
    assert data["cart"] is not None
    assert len(data["cart"]["items"]) == 1
    assert data["cart"]["items"][0]["quantity"] == 2.0
    assert data["cart"]["subtotal_aed"] == 17.0  # 2 kg * 8.50 AED
    assert data["cart"]["vat_aed"] == 0.85       # 5% UAE VAT
    assert data["cart"]["grand_total_aed"] == 17.85  # Subtotal + VAT


# =========================================================================
# TEST 10: Authentication Must Fail Securely
# Missing token -> 401; Invalid token -> 401; Customer on Admin API -> 403
# =========================================================================
@pytest.mark.asyncio
async def test_authentication_fails_securely(
    client: AsyncClient,
    customer_headers: dict,
    admin_headers: dict,
):
    orig_bypass = settings.ALLOW_DEMO_AUTH_BYPASS
    settings.ALLOW_DEMO_AUTH_BYPASS = False
    try:
        # 1. Missing token -> 401 Unauthorized
        resp_no_auth = await client.get("/cart")
        assert resp_no_auth.status_code == 401
        assert "Authentication required" in resp_no_auth.json()["detail"]

        # 2. Invalid or corrupt token -> 401 Unauthorized
        bad_headers = {"Authorization": "Bearer not-a-real-jwt-token"}
        resp_bad_token = await client.get("/cart", headers=bad_headers)
        assert resp_bad_token.status_code == 401
        assert "Invalid or expired access token" in resp_bad_token.json()["detail"]

        # 3. Customer role attempting to access admin API -> 403 Forbidden
        resp_forbidden = await client.get("/admin/dashboard", headers=customer_headers)
        assert resp_forbidden.status_code == 403
        assert "Admin privileges required" in resp_forbidden.json()["detail"]

        # 4. Legitimate admin accessing admin API -> 200 OK
        resp_admin = await client.get("/admin/dashboard", headers=admin_headers)
        assert resp_admin.status_code == 200
    finally:
        settings.ALLOW_DEMO_AUTH_BYPASS = orig_bypass


# =========================================================================
# TEST 11: Governed Assistant Product Selection
# Assistant product selection passes through policy check and logs under agent
# =========================================================================
@pytest.mark.asyncio
async def test_governed_assistant_product_selection(
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
):
    payload = {
        "product_id": str(PRODUCT_ATTA_ID),
        "quantity": 1.0,
        "session_id": "assistant-selection-session",
    }
    response = await client.post(
        "/chat/confirm-product-selection",
        json=payload,
        headers=customer_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["basket_updated"] is True
    assert data["action_taken"] == "add_to_cart"

    # Verify audit log recorded under AI agent identity
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.session_id == "assistant-selection-session",
            AuditLog.action == "assistant_confirmed_selection",
        )
    )
    res = await db_session.execute(stmt)
    logs = res.scalars().all()
    assert len(logs) >= 1
    assert logs[0].agent_id == "kon-shopping-agent"
    assert logs[0].governance_decision == "allowed"
    assert logs[0].execution_status == "success"


# =========================================================================
# TEST 12: Unit Model & Conversion
# 500 grams converts to 0.5 kg; incompatible units rejected
# =========================================================================
@pytest.mark.asyncio
async def test_unit_conversion_and_incompatible_rejection(
    client: AsyncClient,
    customer_headers: dict,
):
    # 1. 500 grams chicken converts to 0.5 kg
    payload = {
        "product_id": str(PRODUCT_CHICKEN_ID),
        "quantity": 500.0,
        "unit": "grams",
        "session_id": "unit-test-session",
    }
    response = await client.post("/cart/items", json=payload, headers=customer_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["items"][0]["quantity"] == 0.5  # 500g -> 0.5 kg

    # 2. Incompatible unit (e.g. litres of chicken) is rejected with 400
    bad_payload = {
        "product_id": str(PRODUCT_CHICKEN_ID),
        "quantity": 2.0,
        "unit": "litre",
        "session_id": "unit-test-session-2",
    }
    bad_resp = await client.post("/cart/items", json=bad_payload, headers=customer_headers)
    assert bad_resp.status_code == 400
    assert "sold by weight" in bad_resp.json()["detail"]


# =========================================================================
# TEST 13: Multi-Item All-Or-Nothing Atomic Rollback
# If one item in multi-product request fails, zero items are added
# =========================================================================
@pytest.mark.asyncio
async def test_multi_item_atomic_all_or_nothing(
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
):
    # Atta is available, but nonexistent UUID will fail
    fake_id = "00000000-0000-0000-0000-999999999999"
    payload = {
        "items": [
            {"product_id": str(PRODUCT_ATTA_ID), "quantity": 1.0},
            {"product_id": fake_id, "quantity": 1.0},
        ],
        "user_id": str(CUSTOMER_USER_ID),
        "session_id": "atomic-fail-session",
    }

    # Attempt multi-item add through tool executor
    from app.tools.cart_tools import tool_executor
    with pytest.raises(ValueError):
        await tool_executor.execute("add_to_cart", params=payload, db=db_session)

    # Verify atomic rollback: cart has 0 items committed
    cart = await cart_tools.get_cart(
        user_id=CUSTOMER_USER_ID,
        session_id="atomic-fail-session",
        db=db_session,
    )
    assert len(cart.items) == 0
    assert cart.grand_total_aed == 0.0


# =========================================================================
# TEST 14: Strict Pydantic Tool Schema Validation
# Prohibits arbitrary extra fields, malicious SQL, and unvalidated arguments
# =========================================================================
@pytest.mark.asyncio
async def test_tool_schema_strict_validation(db_session: AsyncSession):
    # 1. Reject arbitrary unmapped fields (extra = forbid)
    bad_params = {
        "query": "fresh apples",
        "arbitrary_injected_field": "exploit_payload",
    }
    decision = await policy_engine.check(
        agent_id="kon-shopping-agent",
        tool_name="search_products",
        params=bad_params,
        session_context={"user_id": str(CUSTOMER_USER_ID), "session_id": "schema-test"},
        db=db_session,
    )
    assert decision.allowed is False
    assert "extra inputs are not permitted" in decision.reason.lower() or "validation failed" in decision.reason.lower()

    # 2. Reject SQL injection patterns in query
    sql_params = {
        "query": "milk'; DROP TABLE users;--",
    }
    sql_decision = await policy_engine.check(
        agent_id="kon-shopping-agent",
        tool_name="search_products",
        params=sql_params,
        session_context={"user_id": str(CUSTOMER_USER_ID), "session_id": "schema-test"},
        db=db_session,
    )
    assert sql_decision.allowed is False
    assert "unsafe characters or sql patterns" in sql_decision.reason.lower()


# =========================================================================
# TEST 15: Registry Behavior on Restart Preserves Admin Modifications
# Re-initialization must not overwrite deactivated tools or agent status
# =========================================================================
@pytest.mark.asyncio
async def test_registry_restart_preserves_admin_settings(db_session: AsyncSession):
    from app.agents.registry import agent_registry_service
    from app.tools.registry import tool_registry_service

    # Admin deactivates search_products
    tool_stmt = select(ToolRegistry).where(ToolRegistry.tool_name == "search_products")
    tool = (await db_session.execute(tool_stmt)).scalar_one()
    tool.is_active = False

    # Admin deactivates shopping agent
    agent_stmt = select(AgentRegistry).where(AgentRegistry.agent_id == AgentPermissions.SHOPPING_AGENT_ID)
    agent = (await db_session.execute(agent_stmt)).scalar_one()
    agent.status = "inactive"
    await db_session.commit()

    # Simulate application restart re-initialization
    await tool_registry_service.initialize_tools(db_session)
    await agent_registry_service.initialize_default_agent(
        {
            "agent_id": AgentPermissions.SHOPPING_AGENT_ID,
            "name": "KON Shopping Assistant",
            "role": "shopping_assistant",
            "status": "active",
            "allowed_tools": AgentPermissions.ALLOWED_TOOLS_SHOPPING_AGENT,
        },
        db=db_session,
    )

    # Re-fetch records and verify admin settings were NOT overwritten
    tool_after = (await db_session.execute(tool_stmt)).scalar_one()
    assert tool_after.is_active is False  # Still inactive!

    agent_after = (await db_session.execute(agent_stmt)).scalar_one()
    assert agent_after.status == "inactive"  # Still inactive!

    # Cleanup: restore to active for subsequent tests
    tool_after.is_active = True
    agent_after.status = "active"
    await db_session.commit()


# =========================================================================
# TEST 16: Cryptographic Audit Trail Hash Chain Verification
# Tamper-evident SHA-256 chain of custody
# =========================================================================
@pytest.mark.asyncio
async def test_cryptographic_audit_chain_verification(
    client: AsyncClient,
    admin_headers: dict,
    db_session: AsyncSession,
):
    # Log an event to populate the cryptographic chain
    await audit_logger.log(
        db=db_session,
        agent_id="kon-shopping-agent",
        user_id=str(CUSTOMER_USER_ID),
        session_id="chain-test",
        tool_name="get_cart",
        action="test:audit_chain",
        target_resource="cart",
        governance_decision="allowed",
        execution_status="success",
    )

    chain_check = await audit_logger.verify_chain(db_session)
    assert chain_check["valid"] is True
    assert chain_check["total_records"] >= 1

    # Test admin verification endpoint
    resp = await client.get("/admin/audit-logs-verify-chain", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


# =========================================================================
# TEST 17: TTS Endpoint Protected by Authentication
# =========================================================================
@pytest.mark.asyncio
async def test_tts_endpoint_security(
    client: AsyncClient,
    customer_headers: dict,
):
    orig_bypass = settings.ALLOW_DEMO_AUTH_BYPASS
    settings.ALLOW_DEMO_AUTH_BYPASS = False
    try:
        # Missing token -> 401
        resp_no_auth = await client.post("/chat/tts", json={"text": "Hello Dubai"})
        assert resp_no_auth.status_code == 401

        # Oversized payload (> 1000 chars) -> 400
        huge_text = "a" * 1500
        resp_huge = await client.post("/chat/tts", json={"text": huge_text}, headers=customer_headers)
        assert resp_huge.status_code == 400
    finally:
        settings.ALLOW_DEMO_AUTH_BYPASS = orig_bypass


# =========================================================================
# TEST 18: OpenTelemetry Distributed Tracing Pipeline
# Every chat request produces a waterfall of spans: request_received,
# ai_inference, policy_evaluation, tool_execution, audit_persistence, avatar_response.
# =========================================================================
@pytest.mark.asyncio
async def test_opentelemetry_distributed_tracing(
    client: AsyncClient,
    customer_headers: dict,
    admin_headers: dict,
):
    # 1. Send chat request
    chat_resp = await client.post(
        "/chat/message",
        json={"message": "Please add 1 kg chicken to my basket", "session_id": "test-trace-pipeline"},
        headers=customer_headers,
    )
    assert chat_resp.status_code == 200

    # 2. Query trace list from Admin API
    traces_resp = await client.get("/admin/traces", headers=admin_headers)
    assert traces_resp.status_code == 200
    traces = traces_resp.json()
    assert len(traces) > 0

    top_trace = traces[0]
    trace_id = top_trace["trace_id"]
    assert top_trace["total_duration_ms"] > 0
    assert top_trace["spans_count"] >= 6

    # 3. Query granular trace journey
    journey_resp = await client.get(f"/admin/traces/{trace_id}", headers=admin_headers)
    assert journey_resp.status_code == 200
    journey = journey_resp.json()
    assert journey["trace_id"] == trace_id

    span_names = {s["name"] for s in journey["spans"]}
    expected_stages = {
        "request_received",
        "ai_inference",
        "policy_evaluation",
        "tool_execution",
        "audit_persistence",
        "avatar_response",
    }
    assert expected_stages.issubset(span_names)

    for s in journey["spans"]:
        assert "duration_ms" in s
        assert "status" in s
        assert s["status"] in ("ok", "error")


# =========================================================================
# TEST 19: Separated Observability & Metrics Definitions
# Verifies non-skewed separated calculations for agent requests, tool calls,
# policy decisions, and per-stage OpenTelemetry latencies.
# =========================================================================
@pytest.mark.asyncio
async def test_separated_observability_metrics(
    client: AsyncClient,
    admin_headers: dict,
):
    resp = await client.get("/admin/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    d = resp.json()

    assert "total_agent_requests" in d
    assert "total_tool_calls" in d
    assert "policy_allow_rate" in d
    assert "policy_denial_rate" in d
    assert "approval_required_actions" in d
    assert "tool_execution_success_rate" in d
    assert "tool_execution_failure_rate" in d
    assert "avg_ai_inference_ms" in d
    assert "avg_tool_execution_ms" in d
    assert "avg_e2e_latency_ms" in d

    # Verify rates are bounded between 0 and 100
    assert 0.0 <= d["policy_allow_rate"] <= 100.0
    assert 0.0 <= d["policy_denial_rate"] <= 100.0
    assert 0.0 <= d["tool_execution_success_rate"] <= 100.0


# =========================================================================
# TEST 20: Human-in-the-Loop (HITL) Approvals Workflow
# Verifies submit_order returns requires_approval, creates pending request,
# and allows admin approval with supervisor notes.
# =========================================================================
@pytest.mark.asyncio
async def test_hitl_approval_workflow(
    client: AsyncClient,
    customer_headers: dict,
    admin_headers: dict,
):
    # 1. User attempts to submit order via chat
    chat_resp = await client.post(
        "/chat/message",
        json={"message": "Please submit my order now", "session_id": "test-hitl-session"},
        headers=customer_headers,
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "supervisor approval" in chat_data["message"].lower() or "authorization" in chat_data["message"].lower()

    # 2. Admin retrieves pending approvals
    list_resp = await client.get("/admin/approvals?status_filter=pending", headers=admin_headers)
    assert list_resp.status_code == 200
    pending_list = list_resp.json()
    assert len(pending_list) >= 1
    target_req = next((r for r in pending_list if r["tool_name"] == "submit_order"), None)
    assert target_req is not None
    assert target_req["status"] == "pending"
    assert target_req["risk_level"] == "HIGH"

    # 3. Admin approves the pending request
    approval_id = target_req["id"]
    approve_resp = await client.post(
        f"/admin/approvals/{approval_id}/approve",
        json={"notes": "Supervisor verified user and order contents."},
        headers=admin_headers,
    )
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["status"] == "approved"
    assert approved_data["resolved_by"] == "admin"
    assert "Supervisor verified" in approved_data["resolution_notes"]

    # 4. Attempting to approve or reject an already resolved request must return 400
    re_approve = await client.post(
        f"/admin/approvals/{approval_id}/approve",
        json={"notes": "Duplicate approval attempt"},
        headers=admin_headers,
    )
    assert re_approve.status_code == 400
    assert "already been resolved" in re_approve.json()["detail"]


# =========================================================================
# TEST 21: AI Employee Directory & Tool Permissions Management
# Verifies enterprise agent directory, status toggle, and tool updates.
# =========================================================================
@pytest.mark.asyncio
async def test_agent_employee_directory_management(
    client: AsyncClient,
    admin_headers: dict,
):
    # 1. Fetch AI employee directory
    resp = await client.get("/admin/agents", headers=admin_headers)
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) >= 4

    agent_ids = {a["agent_id"] for a in agents}
    assert "kon-shopping-agent" in agent_ids
    assert "kon-support-agent" in agent_ids
    assert "kon-finance-agent" in agent_ids
    assert "kon-hr-agent" in agent_ids

    # Verify employee metadata fields
    shopping_agent = next(a for a in agents if a["agent_id"] == "kon-shopping-agent")
    assert shopping_agent["department"] == "Retail Commerce"
    assert shopping_agent["model_provider"] == "Google Gemini"
    assert "total_requests" in shopping_agent

    # 2. Toggle active status
    toggle_resp = await client.post(
        "/admin/agents/kon-support-agent/toggle-status",
        headers=admin_headers,
    )
    assert toggle_resp.status_code == 200
    toggled = toggle_resp.json()
    assert toggled["status"] == "inactive"

    # Toggle back to active
    toggle_back = await client.post(
        "/admin/agents/kon-support-agent/toggle-status",
        headers=admin_headers,
    )
    assert toggle_back.status_code == 200
    assert toggle_back.json()["status"] == "active"

    # 3. Update permitted tools
    new_tools = ["search_products", "get_product_details"]
    update_resp = await client.patch(
        "/admin/agents/kon-support-agent",
        json={"allowed_tools": new_tools, "department": "Customer Experience"},
        headers=admin_headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["allowed_tools"] == new_tools
    assert updated["department"] == "Customer Experience"





