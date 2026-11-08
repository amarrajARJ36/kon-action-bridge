from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import ToolRegistry


class ToolRegistryService:
    """
    Manages registry definitions and JSON validation schemas for all commerce tools.
    """

    DEFAULT_TOOLS: List[Dict[str, Any]] = [
        {
            "tool_name": "search_products",
            "description": "Search grocery catalog by keyword query, brand, or category.",
            "permission_level": "public",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword for product name or variant"},
                    "category": {"type": "string", "description": "Filter by grocery category"},
                },
                "required": ["query"],
            },
        },
        {
            "tool_name": "get_product_details",
            "description": "Fetch real-time pricing, stock level, and details for a product by UUID.",
            "permission_level": "public",
            "input_schema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "format": "uuid", "description": "UUID of the product"},
                },
                "required": ["product_id"],
            },
        },
        {
            "tool_name": "add_to_cart",
            "description": "Add an available grocery product and quantity to the customer's shopping basket.",
            "permission_level": "restricted",
            "input_schema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "format": "uuid", "description": "UUID of the product to add"},
                    "quantity": {"type": "number", "minimum": 0.01, "maximum": 100, "description": "Quantity to purchase"},
                },
                "required": ["product_id", "quantity"],
            },
        },
        {
            "tool_name": "update_cart_item",
            "description": "Update the quantity of a specific item already present in the customer's cart.",
            "permission_level": "restricted",
            "input_schema": {
                "type": "object",
                "properties": {
                    "cart_item_id": {"type": "string", "format": "uuid", "description": "UUID of the cart item"},
                    "quantity": {"type": "number", "minimum": 0.01, "maximum": 100, "description": "New target quantity"},
                },
                "required": ["cart_item_id", "quantity"],
            },
        },
        {
            "tool_name": "remove_from_cart",
            "description": "Remove an item line completely from the customer's cart.",
            "permission_level": "restricted",
            "input_schema": {
                "type": "object",
                "properties": {
                    "cart_item_id": {"type": "string", "format": "uuid", "description": "UUID of the cart item to delete"},
                },
                "required": ["cart_item_id"],
            },
        },
        {
            "tool_name": "get_cart",
            "description": "Retrieve current basket items, verified subtotal, and grand total in AED.",
            "permission_level": "public",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "tool_name": "get_checkout_preview",
            "description": "Generate a verified pre-checkout order breakdown without placing any order.",
            "permission_level": "restricted",
            "input_schema": {
                "type": "object",
                "properties": {
                    "explicit_confirmation": {
                        "type": "boolean",
                        "description": "Acknowledgment flag that this is a non-binding preview",
                    }
                },
            },
        },
        {
            "tool_name": "submit_order",
            "description": "Submit a shopping basket for final binding order execution. High-risk operation requiring Human-in-the-Loop supervisor approval.",
            "permission_level": "restricted",
            "input_schema": {
                "type": "object",
                "properties": {
                    "delivery_address": {
                        "type": "string",
                        "description": "Customer delivery address",
                    },
                    "payment_method": {
                        "type": "string",
                        "description": "Payment method preview",
                    },
                },
            },
        },
    ]

    async def get_tool(self, tool_name: str, db: AsyncSession) -> Optional[ToolRegistry]:
        stmt = select(ToolRegistry).where(ToolRegistry.tool_name == tool_name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tools(self, db: AsyncSession) -> List[ToolRegistry]:
        stmt = select(ToolRegistry).order_by(ToolRegistry.tool_name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def initialize_tools(self, db: AsyncSession) -> None:
        """
        Seeds all 7 standard tools if they do not yet exist in the registry.
        Preserves existing tools and any administrator modifications (e.g. is_active, permission_level).
        """
        for tool_def in self.DEFAULT_TOOLS:
            existing = await self.get_tool(tool_def["tool_name"], db)
            if existing:
                # Do NOT overwrite administrator-managed fields (is_active, permission_level) on restart
                pass
            else:
                new_tool = ToolRegistry(
                    tool_name=tool_def["tool_name"],
                    description=tool_def["description"],
                    input_schema=tool_def["input_schema"],
                    permission_level=tool_def["permission_level"],
                    is_active=True,
                )
                db.add(new_tool)
        await db.commit()

    def get_gemini_tool_declarations(
        self,
        allowed_tool_names: Optional[List[str]] = None,
    ) -> List[Any]:
        """
        Generates google.genai types.FunctionDeclaration objects for permitted agent tools.
        Ensures admin tools or unpermitted actions are never exposed to Gemini.
        """
        from google.genai import types

        def _json_schema_to_genai(s: Dict[str, Any]) -> types.Schema:
            type_map = {
                "string": types.Type.STRING,
                "number": types.Type.NUMBER,
                "integer": types.Type.INTEGER,
                "boolean": types.Type.BOOLEAN,
                "array": types.Type.ARRAY,
                "object": types.Type.OBJECT,
            }
            stype = type_map.get(s.get("type", "object"), types.Type.OBJECT)
            props = {}
            for k, v in s.get("properties", {}).items():
                props[k] = _json_schema_to_genai(v)

            items_schema = None
            if "items" in s and isinstance(s["items"], dict):
                items_schema = _json_schema_to_genai(s["items"])

            return types.Schema(
                type=stype,
                description=s.get("description"),
                properties=props if props else None,
                items=items_schema,
                required=s.get("required"),
            )

        declarations: List[types.FunctionDeclaration] = []
        for tool_def in self.DEFAULT_TOOLS:
            t_name = tool_def["tool_name"]
            if allowed_tool_names is not None and t_name not in allowed_tool_names:
                continue

            decl = types.FunctionDeclaration(
                name=t_name,
                description=tool_def["description"],
                parameters=_json_schema_to_genai(tool_def.get("input_schema", {})),
            )
            declarations.append(decl)
        return declarations


tool_registry_service = ToolRegistryService()
