"""
Unit of Measurement Model & Converter
=====================================
Normalizes conversational quantity and unit inputs (e.g., 500g, 0.5kg, 2 litres, 1 pack)
into canonical product measurement units stored in the catalog (kg, litre, pack, bottle).
Enforces unit compatibility checks and rejects mismatched dimensions (e.g. litres of chicken).
"""
from typing import Optional, Tuple


# Unit alias mapping to canonical dimension
UNIT_ALIASES = {
    # Mass
    "g": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    # Volume
    "ml": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "l": "litre",
    "litre": "litre",
    "litres": "litre",
    "liter": "litre",
    "liters": "litre",
    # Discrete items / packaging
    "pack": "pack",
    "packs": "pack",
    "packet": "pack",
    "packets": "pack",
    "box": "pack",
    "boxes": "pack",
    "bottle": "bottle",
    "bottles": "bottle",
    "piece": "unit",
    "pieces": "unit",
    "item": "unit",
    "items": "unit",
    "unit": "unit",
    "units": "unit",
}


def normalize_unit_string(unit: Optional[str]) -> Optional[str]:
    """Returns normalized unit identifier or None if unspecified."""
    if not unit:
        return None
    cleaned = unit.strip().lower()
    return UNIT_ALIASES.get(cleaned, cleaned)


def convert_quantity_to_canonical(
    quantity: float,
    user_unit: Optional[str],
    canonical_unit: str,
    product_name: str = "item",
) -> float:
    """
    Validates unit dimension compatibility and converts quantity into
    the product's canonical unit of measurement.

    Examples:
      500 grams of chicken (canonical: kg) -> 0.5 kg
      1.5 kg of apples (canonical: kg)     -> 1.5 kg
      1000 ml of milk (canonical: litre)   -> 1.0 litre
      2 packs of eggs (canonical: pack)    -> 2.0 packs

    Raises:
      ValueError if the requested unit is incompatible with the product unit.
    """
    if quantity <= 0:
        raise ValueError(f"Quantity must be positive, got {quantity}")

    norm_user_unit = normalize_unit_string(user_unit)
    norm_canonical = (canonical_unit or "unit").strip().lower()

    # 1. Product is measured by weight (kg)
    if norm_canonical == "kg":
        if norm_user_unit == "g":
            return round(quantity / 1000.0, 4)
        elif norm_user_unit == "kg":
            return round(quantity, 4)
        elif norm_user_unit in ("unit", None, ""):
            # Unspecified unit on weight produce (e.g. "1 apple" or "2 bananas")
            # In UAE grocery catalog, produce is packaged/sold in 1 kg increments
            return round(quantity, 4)
        else:
            raise ValueError(
                f"Invalid unit '{user_unit}' for {product_name}. "
                f"This item is sold by weight ({canonical_unit})."
            )

    # 2. Product is measured by liquid volume (litre)
    elif norm_canonical in ("litre", "liter"):
        if norm_user_unit == "ml":
            return round(quantity / 1000.0, 4)
        elif norm_user_unit in ("litre", "bottle", "pack", "unit", None, ""):
            return round(quantity, 4)
        else:
            raise ValueError(
                f"Invalid unit '{user_unit}' for {product_name}. "
                f"This liquid product is sold by volume ({canonical_unit})."
            )

    # 3. Product is packaged / discrete (pack, bottle, unit)
    elif norm_canonical in ("pack", "bottle", "unit"):
        if norm_user_unit in ("pack", "bottle", "unit", "piece", None, ""):
            return round(quantity, 4)
        else:
            raise ValueError(
                f"Invalid unit '{user_unit}' for {product_name}. "
                f"This packaged item is sold by the {canonical_unit}."
            )

    # Fallback: direct numeric passthrough if units match or user unit is None
    if norm_user_unit is None or norm_user_unit == norm_canonical:
        return round(quantity, 4)

    raise ValueError(
        f"Unsupported unit '{user_unit}' for {product_name} (sold in {canonical_unit})."
    )

