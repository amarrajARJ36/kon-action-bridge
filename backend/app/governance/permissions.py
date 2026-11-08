from typing import Dict, List

# Role Constants
ROLE_CUSTOMER = "customer"
ROLE_ADMIN = "admin"

# Permission Level Constants
PERMISSION_PUBLIC = "public"
PERMISSION_RESTRICTED = "restricted"

# Mapping of all standard tools to their required minimum user role
TOOL_PERMISSIONS: Dict[str, str] = {
    "search_products": ROLE_CUSTOMER,
    "get_product_details": ROLE_CUSTOMER,
    "add_to_cart": ROLE_CUSTOMER,
    "update_cart_item": ROLE_CUSTOMER,
    "remove_from_cart": ROLE_CUSTOMER,
    "get_cart": ROLE_CUSTOMER,
    "get_checkout_preview": ROLE_CUSTOMER,
    "submit_order": ROLE_CUSTOMER,
}


class AgentPermissions:
    """
    Default permission sets and allowed tools by agent ID.
    """
    SHOPPING_AGENT_ID = "kon-shopping-agent"

    ALLOWED_TOOLS_SHOPPING_AGENT: List[str] = [
        "search_products",
        "get_product_details",
        "add_to_cart",
        "update_cart_item",
        "remove_from_cart",
        "get_cart",
        "get_checkout_preview",
        "submit_order",
    ]
