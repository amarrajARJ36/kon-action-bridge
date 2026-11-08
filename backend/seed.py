import asyncio
import uuid
from decimal import Decimal
from sqlalchemy import select

from app.api.auth import get_password_hash
from app.database import AsyncSessionLocal, create_tables
from app.governance.permissions import AgentPermissions
from app.models.governance import AgentRegistry, ToolRegistry
from app.models.product import Product
from app.models.user import User
from app.tools.registry import tool_registry_service

# Deterministic product catalog data (UAE market)
SEED_PRODUCTS = [
    # --- ATTA ---
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111101"),
        "sku": "ATTA-ALBAKER-01",
        "name": "Al Baker Chakki Atta",
        "brand": "Al Baker",
        "category": "Atta",
        "variant": "Chakki Fresh Atta",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("8.50"),
        "stock_quantity": 200.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff",
    },
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111102"),
        "sku": "ATTA-AASHIRVAAD-01",
        "name": "Aashirvaad Chakki Atta",
        "brand": "Aashirvaad",
        "category": "Atta",
        "variant": "Chakki Fresh Atta",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("12.00"),
        "stock_quantity": 150.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff",
    },
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111103"),
        "sku": "ATTA-HOUSE-01",
        "name": "Whole Wheat Atta (Generic)",
        "brand": "House Brand",
        "category": "Atta",
        "variant": "Whole Wheat",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("5.75"),
        "stock_quantity": 300.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff",
    },
    # --- BANANAS ---
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222201"),
        "sku": "BAN-REG-01",
        "name": "Regular Bananas",
        "brand": "Fresh Farms",
        "category": "Bananas",
        "variant": "Cavendish Bananas",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("4.25"),
        "stock_quantity": 50.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222202"),
        "sku": "BAN-ORG-01",
        "name": "Organic Bananas",
        "brand": "Organic Valley",
        "category": "Bananas",
        "variant": "Organic Cavendish",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("7.50"),
        "stock_quantity": 30.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222203"),
        "sku": "BAN-BABY-01",
        "name": "Baby Bananas",
        "brand": "Fresh Farms",
        "category": "Bananas",
        "variant": "Mini/Lady Finger Bananas",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("9.00"),
        "stock_quantity": 20.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e",
    },
    # --- CHICKEN ---
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333301"),
        "sku": "CHK-WHOLE-01",
        "name": "Whole Chicken",
        "brand": "Al Rawdah",
        "category": "Chicken",
        "variant": "Fresh Whole Chicken",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("22.00"),
        "stock_quantity": 100.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1587593810167-a84920ea0781",
    },
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333302"),
        "sku": "CHK-BREAST-01",
        "name": "Chicken Breast",
        "brand": "Al Rawdah",
        "category": "Chicken",
        "variant": "Fresh Boneless Breast Fillet",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("38.50"),
        "stock_quantity": 80.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1604503468506-a8da13d82791",
    },
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333303"),
        "sku": "CHK-CUBES-01",
        "name": "Boneless Chicken Cubes",
        "brand": "Al Rawdah",
        "category": "Chicken",
        "variant": "Fresh Boneless Cubes",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("35.00"),
        "stock_quantity": 60.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1604503468506-a8da13d82791",
    },
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333304"),
        "sku": "CHK-THIGHS-01",
        "name": "Chicken Thighs",
        "brand": "Al Rawdah",
        "category": "Chicken",
        "variant": "Boneless Thigh Fillet",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("32.00"),
        "stock_quantity": 70.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1604503468506-a8da13d82791",
    },
    # --- RICE ---
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444401"),
        "sku": "RICE-DAAWAT-01",
        "name": "Basmati Rice",
        "brand": "Daawat",
        "category": "Rice",
        "variant": "Extra Long Basmati",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("15.00"),
        "stock_quantity": 200.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1586201375761-83865001e31c",
    },
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444402"),
        "sku": "RICE-ROZANA-01",
        "name": "Sella Basmati Rice",
        "brand": "Rozana",
        "category": "Rice",
        "variant": "Sella (Parboiled)",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("11.50"),
        "stock_quantity": 180.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1586201375761-83865001e31c",
    },
    # --- EGGS ---
    {
        "id": uuid.UUID("55555555-5555-5555-5555-555555555501"),
        "sku": "EGG-ALAIN-01",
        "name": "Fresh Eggs (12 pack)",
        "brand": "Al Ain Farms",
        "category": "Eggs",
        "variant": "Large White Eggs",
        "unit_of_measurement": "pack",
        "price_aed": Decimal("12.00"),
        "stock_quantity": 100.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f",
    },
    # --- MILK ---
    {
        "id": uuid.UUID("66666666-6666-6666-6666-666666666601"),
        "sku": "MILK-ALAIN-01",
        "name": "Full Fat Milk 1L",
        "brand": "Al Ain Farms",
        "category": "Milk",
        "variant": "Fresh Full Fat",
        "unit_of_measurement": "litre",
        "price_aed": Decimal("5.50"),
        "stock_quantity": 120.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1550583724-b2692b85b150",
    },
    {
        "id": uuid.UUID("66666666-6666-6666-6666-666666666602"),
        "sku": "MILK-ALMARAI-01",
        "name": "Low Fat Milk 1L",
        "brand": "Almarai",
        "category": "Milk",
        "variant": "Long Life Low Fat",
        "unit_of_measurement": "litre",
        "price_aed": Decimal("6.25"),
        "stock_quantity": 90.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1550583724-b2692b85b150",
    },
    # --- OLIVE OIL ---
    {
        "id": uuid.UUID("77777777-7777-7777-7777-777777777701"),
        "sku": "OIL-RAHMA-01",
        "name": "Extra Virgin Olive Oil 750ml",
        "brand": "Rahma",
        "category": "Olive Oil",
        "variant": "Extra Virgin Cold Pressed",
        "unit_of_measurement": "bottle",
        "price_aed": Decimal("28.00"),
        "stock_quantity": 60.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5",
    },
    # --- TOMATOES ---
    {
        "id": uuid.UUID("88888888-8888-8888-8888-888888888801"),
        "sku": "VEG-TOMATO-01",
        "name": "Fresh Tomatoes",
        "brand": "Local Farm",
        "category": "Tomatoes",
        "variant": "Round Tomatoes",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("3.50"),
        "stock_quantity": 80.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea",
    },
    # --- APPLES, ORANGES, POMEGRANATES (Fresh Fruits) ---
    {
        "id": uuid.UUID("99999999-9999-9999-9999-999999999901"),
        "sku": "FRT-APPLE-01",
        "name": "Fresh Royal Gala Apples",
        "brand": "Fresh Farms",
        "category": "Fruits",
        "variant": "Royal Gala Apples",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("7.50"),
        "stock_quantity": 100.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6",
    },
    {
        "id": uuid.UUID("99999999-9999-9999-9999-999999999902"),
        "sku": "FRT-ORANGE-01",
        "name": "Fresh Valencia Oranges",
        "brand": "Citrus Valley",
        "category": "Fruits",
        "variant": "Valencia Oranges",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("5.50"),
        "stock_quantity": 120.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1582979512210-99b6a53386f9",
    },
    {
        "id": uuid.UUID("99999999-9999-9999-9999-999999999903"),
        "sku": "FRT-POM-01",
        "name": "Fresh Ruby Pomegranates",
        "brand": "Organic Oasis",
        "category": "Fruits",
        "variant": "Ruby Red Pomegranates",
        "unit_of_measurement": "kg",
        "price_aed": Decimal("14.00"),
        "stock_quantity": 80.0,
        "is_available": True,
        "image_url": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5",
    },
]


async def seed_database():
    print("Beginning KON Action Bridge database initialization...")
    await create_tables()

    async with AsyncSessionLocal() as session:
        # 1. Seed Demo Users
        users_to_seed = [
            {
                "id": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                "username": "admin",
                "email": "admin@kon.local",
                "password": "admin123",
                "role": "admin",
            },
            {
                "id": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                "username": "demo_customer",
                "email": "customer@kon.local",
                "password": "customer123",
                "role": "customer",
            },
        ]

        for u in users_to_seed:
            res = await session.execute(select(User).where(User.username == u["username"]))
            existing_user = res.scalar_one_or_none()
            if not existing_user:
                new_user = User(
                    id=u["id"],
                    username=u["username"],
                    email=u["email"],
                    hashed_password=get_password_hash(u["password"]),
                    role=u["role"],
                    is_active=True,
                )
                session.add(new_user)
                print(f" -> Created user '{u['username']}' ({u['role']})")

        # 2. Seed Tools
        await tool_registry_service.initialize_tools(session)
        print(" -> Seeded 7 standard commerce tools into ToolRegistry")

        # 3. Seed AI Employees Registry
        ai_employees = [
            {
                "agent_id": AgentPermissions.SHOPPING_AGENT_ID,
                "name": "Retail Shopping Assistant",
                "description": "Conversational grocery shopping assistant with governed catalogue & basket tool access",
                "role": "shopping_assistant",
                "department": "Retail Commerce",
                "model_provider": "Google Gemini",
                "model_version": "gemini-1.5-flash",
                "owner_tenant": "KON Retail E-Commerce",
                "status": "active",
                "allowed_tools": AgentPermissions.ALLOWED_TOOLS_SHOPPING_AGENT,
            },
            {
                "agent_id": "kon-support-agent",
                "name": "Customer Support Agent",
                "description": "Handles inquiries, store policies, order status, and customer service requests",
                "role": "customer_support",
                "department": "Customer Care",
                "model_provider": "Google Gemini",
                "model_version": "gemini-1.5-flash",
                "owner_tenant": "Support Operations",
                "status": "active",
                "allowed_tools": ["search_products", "get_product_details", "get_cart"],
            },
            {
                "agent_id": "kon-finance-agent",
                "name": "Finance & Invoicing Agent",
                "description": "Processes tax calculations, VAT previews, checkout breakdowns, and billing inquiries",
                "role": "finance_controller",
                "department": "Finance & Accounting",
                "model_provider": "Google Gemini",
                "model_version": "gemini-1.5-pro",
                "owner_tenant": "Corporate Finance",
                "status": "active",
                "allowed_tools": ["get_checkout_preview"],
            },
            {
                "agent_id": "kon-hr-agent",
                "name": "Internal HR Assistant",
                "description": "Internal employee onboarding, policy FAQs, and employee benefits assistance",
                "role": "people_operations",
                "department": "Human Resources",
                "model_provider": "Google Gemini",
                "model_version": "gemini-1.5-flash",
                "owner_tenant": "People & Culture",
                "status": "active",
                "allowed_tools": [],  # Strictly zero commerce tool permissions
            },
        ]

        for ag in ai_employees:
            agent_res = await session.execute(
                select(AgentRegistry).where(AgentRegistry.agent_id == ag["agent_id"])
            )
            existing_agent = agent_res.scalar_one_or_none()
            if not existing_agent:
                new_agent = AgentRegistry(
                    agent_id=ag["agent_id"],
                    name=ag["name"],
                    description=ag["description"],
                    role=ag["role"],
                    department=ag["department"],
                    model_provider=ag["model_provider"],
                    model_version=ag["model_version"],
                    owner_tenant=ag["owner_tenant"],
                    status=ag["status"],
                    allowed_tools=ag["allowed_tools"],
                )
                session.add(new_agent)
                print(f" -> Registered AI Employee '{ag['name']}' ({ag['department']})")

        # 4. Seed Products
        for prod_data in SEED_PRODUCTS:
            p_res = await session.execute(select(Product).where(Product.sku == prod_data["sku"]))
            existing_prod = p_res.scalar_one_or_none()
            if not existing_prod:
                new_prod = Product(**prod_data)
                session.add(new_prod)

        await session.commit()
        print(f" -> Seeded {len(SEED_PRODUCTS)} grocery catalog products")

    print("KON Action Bridge seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
