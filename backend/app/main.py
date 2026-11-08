from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.registry import agent_registry_service
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.cart import router as cart_router
from app.api.chat import router as chat_router
from app.api.products import router as products_router
from app.config import settings
from app.database import AsyncSessionLocal, create_tables, get_db
from app.governance.permissions import AgentPermissions
from app.tools.registry import tool_registry_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager ensuring database tables, tools, products,
    and governed shopping agent registries are initialized at boot against
    the active runtime database.
    """
    # 1. Ensure all database schemas and tables exist
    await create_tables()

    # 2. Seed runtime database with default users, products, tools, and agent if needed
    try:
        from seed import seed_database
        await seed_database()
    except Exception as err:
        import logging
        logging.getLogger(__name__).warning(f"Runtime database initialization: {err}")

    # 3. Pre-populate Jaeger collector with recent traces if Jaeger is active
    try:
        from app.database import AsyncSessionLocal
        from app.observability.tracing import sync_database_spans_to_jaeger
        async with AsyncSessionLocal() as session:
            await sync_database_spans_to_jaeger(session)
    except Exception as err:
        import logging
        logging.getLogger(__name__).warning(f"Jaeger span pre-population: {err}")

    yield


app = FastAPI(
    title="KON Action Bridge",
    description="Conversational AI Shopping Assistant with Enterprise Governance & Security Layer",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Sub-Routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/chat", tags=["Conversational AI"])
app.include_router(products_router, prefix="/products", tags=["Product Catalog"])
app.include_router(cart_router, prefix="/cart", tags=["Shopping Basket"])
app.include_router(admin_router, prefix="/admin", tags=["Governance & Admin"])


@app.get("/health", tags=["System"])
async def health_check():
    """
    Standard health check endpoint for monitoring and uptime probes.
    """
    return {
        "status": "healthy",
        "service": "kon-action-bridge",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
    }


@app.get("/neon/status", tags=["Neon Cloud Services"])
async def neon_status(db: AsyncSession = Depends(get_db)):
    """
    Status probe for wired Neon Lakebase services:
    Postgres, Functions, AI Gateway, and Realtime.
    """
    from sqlalchemy import text
    import httpx

    services = {}

    # 1. Postgres
    try:
        res = await db.execute(text("SELECT version(), current_database(), (SELECT count(*) FROM products) as products_count;"))
        row = res.mappings().first()
        services["postgres"] = {
            "status": "connected",
            "driver": "SQLAlchemy + asyncpg",
            "database": row["current_database"],
            "version": row["version"],
            "products_count": row["products_count"],
        }
    except Exception as e:
        services["postgres"] = {"status": "error", "error": str(e)}

    # 2. Neon Functions
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            fn_res = await client.get(settings.NEON_FUNCTION_URL)
            services["functions"] = {
                "status": "connected" if fn_res.status_code == 200 else "error",
                "status_code": fn_res.status_code,
                "url": settings.NEON_FUNCTION_URL,
                "output": fn_res.text.strip(),
            }
    except Exception as e:
        services["functions"] = {"status": "error", "error": str(e)}

    # 3. AI Gateway
    if settings.NEON_AI_GATEWAY_BASE_URL and settings.NEON_AI_GATEWAY_TOKEN:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                gw_res = await client.get(
                    f"{settings.NEON_AI_GATEWAY_BASE_URL}/v1/models",
                    headers={"Authorization": f"Bearer {settings.NEON_AI_GATEWAY_TOKEN}"}
                )
                gw_data = gw_res.json()
                services["ai_gateway"] = {
                    "status": "connected" if gw_res.status_code == 200 else "error",
                    "status_code": gw_res.status_code,
                    "catalog_count": len(gw_data.get("data", [])),
                    "availability": gw_data.get("request_context_availability", {}).get("http", {}).get("status", "active"),
                }
        except Exception as e:
            services["ai_gateway"] = {"status": "error", "error": str(e)}
    else:
        services["ai_gateway"] = {"status": "not_configured"}

    # 4. Realtime
    services["realtime"] = {
        "status": "configured" if settings.NEON_REALTIME_URL else "not_configured",
        "url": settings.NEON_REALTIME_URL,
        "branch": settings.NEON_BRANCH,
        "branch_id": settings.NEON_BRANCH_ID,
    }

    return {
        "status": "operational",
        "neon_branch": settings.NEON_BRANCH,
        "services": services
    }
