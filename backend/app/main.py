from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.registry import agent_registry_service
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.cart import router as cart_router
from app.api.chat import router as chat_router
from app.api.products import router as products_router
from app.config import settings
from app.database import AsyncSessionLocal, create_tables
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
