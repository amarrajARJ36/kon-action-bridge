from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.products import router as products_router
from app.api.cart import router as cart_router
from app.api.admin import router as admin_router

__all__ = [
    "auth_router",
    "chat_router",
    "products_router",
    "cart_router",
    "admin_router",
]
