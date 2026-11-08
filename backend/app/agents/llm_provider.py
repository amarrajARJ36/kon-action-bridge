import asyncio
import json
import logging
import re
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.schemas.chat import ChatMessage
from app.tools.unit_converter import convert_quantity_to_canonical

logger = logging.getLogger(__name__)


def _build_confirmation_str(to_add: List[Dict], unit_labels: Dict[str, str]) -> str:
    """Builds human-readable cart confirmation like '1 kg of Fresh Royal Gala Apples, 2 litres of Full Fat Milk 1L'."""
    parts = []
    for it in to_add:
        name = it.get("resolved_name", it.get("name", "item")).capitalize()
        qty = it.get("quantity", 1.0)
        unit = unit_labels.get(it.get("name", ""), "unit")
        qty_str = int(qty) if isinstance(qty, float) and qty.is_integer() else qty
        if unit == "kg":
            parts.append(f"{qty_str} kg of {name}")
        elif unit == "litre":
            parts.append(f"{qty_str}× {name} (1L)")
        elif unit == "pack":
            parts.append(f"{qty_str}× {name}")
        else:
            parts.append(f"{qty_str}× {name}")
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + f" and {parts[-1]}"


class ToolCallProposal(BaseModel):
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[str] = None


class LLMResponse(BaseModel):
    tool_name: Optional[str] = None
    tool_params: Dict[str, Any] = Field(default_factory=dict)
    text_response: str = ""
    proposed_calls: List[ToolCallProposal] = Field(default_factory=list)


class LLMProvider(ABC):
    """
    Abstract base class for conversational AI providers.
    """

    @abstractmethod
    async def generate_response(
        self,
        message: str,
        session_id: str,
        history: Optional[List[ChatMessage]] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        pass

    async def generate_truthful_response(self, prompt: str) -> Optional[str]:
        return None


class FallbackProvider(LLMProvider):
    """
    Deterministic rule-based state machine that parses customer grocery requests,
    manages multi-turn clarification dialogues, and emits governed commerce tool calls.
    Requires no external API keys.
    """

    # Pre-known demo product IDs for reliable fallback dispatch
    KNOWN_PRODUCT_LOOKUP = {
        "al baker": "11111111-1111-1111-1111-111111111101",
        "aashirvaad": "11111111-1111-1111-1111-111111111102",
        "whole wheat": "11111111-1111-1111-1111-111111111103",
        "flour": "11111111-1111-1111-1111-111111111101",
        "atta": "11111111-1111-1111-1111-111111111101",
        "regular bananas": "22222222-2222-2222-2222-222222222201",
        "cavendish bananas": "22222222-2222-2222-2222-222222222201",
        "bananas": "22222222-2222-2222-2222-222222222201",
        "banana": "22222222-2222-2222-2222-222222222201",
        "organic bananas": "22222222-2222-2222-2222-222222222202",
        "baby bananas": "22222222-2222-2222-2222-222222222203",
        "whole chicken": "33333333-3333-3333-3333-333333333301",
        "chicken": "33333333-3333-3333-3333-333333333301",
        "chicken breast": "33333333-3333-3333-3333-333333333302",
        "boneless chicken": "33333333-3333-3333-3333-333333333303",
        "chicken cubes": "33333333-3333-3333-3333-333333333303",
        "chicken thighs": "33333333-3333-3333-3333-333333333304",
        "basmati rice": "44444444-4444-4444-4444-444444444401",
        "daawat rice": "44444444-4444-4444-4444-444444444401",
        "rice": "44444444-4444-4444-4444-444444444401",
        "sella rice": "44444444-4444-4444-4444-444444444402",
        "eggs": "55555555-5555-5555-5555-555555555501",
        "egg": "55555555-5555-5555-5555-555555555501",
        "fresh eggs": "55555555-5555-5555-5555-555555555501",
        "milk": "66666666-6666-6666-6666-666666666601",
        "full fat milk": "66666666-6666-6666-6666-666666666601",
        "low fat milk": "66666666-6666-6666-6666-666666666602",
        "olive oil": "77777777-7777-7777-7777-777777777701",
        "oil": "77777777-7777-7777-7777-777777777701",
        "tomatoes": "88888888-8888-8888-8888-888888888801",
        "tomato": "88888888-8888-8888-8888-888888888801",
        "apple": "99999999-9999-9999-9999-999999999901",
        "apples": "99999999-9999-9999-9999-999999999901",
        "royal gala": "99999999-9999-9999-9999-999999999901",
        "orange": "99999999-9999-9999-9999-999999999902",
        "oranges": "99999999-9999-9999-9999-999999999902",
        "valencia": "99999999-9999-9999-9999-999999999902",
        "pomegranate": "99999999-9999-9999-9999-999999999903",
        "pomegranates": "99999999-9999-9999-9999-999999999903",
        "pom": "99999999-9999-9999-9999-999999999903",
    }

    # Products that need a clarifying question before adding.
    # Maps canonical name → (question, {keyword → product_id})
    DISAMBIGUATION_MAP: Dict[str, Any] = {
        "milk": {
            "question": "We carry two types of milk: Al Ain Full Fat Milk 1L (AED 5.50) or Almarai Low Fat Milk 1L (AED 6.25). Which would you prefer?",
            "options": {
                "full fat": "66666666-6666-6666-6666-666666666601",
                "low fat": "66666666-6666-6666-6666-666666666602",
                "al ain": "66666666-6666-6666-6666-666666666601",
                "almarai": "66666666-6666-6666-6666-666666666602",
                "skimmed": "66666666-6666-6666-6666-666666666602",
                "semi": "66666666-6666-6666-6666-666666666602",
            },
            "default_name": "Full Fat Milk 1L",
        },
        "atta": {
            "question": "For atta we have: Al Baker Chakki Fresh Atta (AED 8.50/kg), Aashirvaad Chakki (AED 12.00/kg), or Whole Wheat Atta (AED 7.75/kg). Which would you like?",
            "options": {
                "al baker": "11111111-1111-1111-1111-111111111101",
                "aashirvaad": "11111111-1111-1111-1111-111111111102",
                "whole wheat": "11111111-1111-1111-1111-111111111103",
                "chakki": "11111111-1111-1111-1111-111111111101",
            },
            "default_name": "Al Baker Chakki Fresh Atta",
        },
        "chicken": {
            "question": "For chicken we carry: Fresh Whole Chicken (AED 29/kg), Chicken Breast Fillet (AED 34/kg), or Boneless Cubes (AED 38/kg). Which cut would you prefer?",
            "options": {
                "whole": "33333333-3333-3333-3333-333333333301",
                "breast": "33333333-3333-3333-3333-333333333302",
                "boneless": "33333333-3333-3333-3333-333333333303",
                "cubes": "33333333-3333-3333-3333-333333333303",
                "thigh": "33333333-3333-3333-3333-333333333304",
                "fillet": "33333333-3333-3333-3333-333333333302",
            },
            "default_name": "Fresh Whole Chicken",
        },
        "rice": {
            "question": "We have Daawat Basmati Rice (AED 15/kg) and Sella Basmati Rice (AED 11.50/kg). Which one?",
            "options": {
                "daawat": "44444444-4444-4444-4444-444444444401",
                "basmati": "44444444-4444-4444-4444-444444444401",
                "sella": "44444444-4444-4444-4444-444444444402",
            },
            "default_name": "Daawat Basmati Rice",
        },
        "bananas": {
            "question": "We have Regular Cavendish Bananas (AED 5/kg), Organic Bananas (AED 9/kg), or Baby Bananas (AED 11/kg). Which type?",
            "options": {
                "organic": "22222222-2222-2222-2222-222222222202",
                "baby": "22222222-2222-2222-2222-222222222203",
                "mini": "22222222-2222-2222-2222-222222222203",
                "regular": "22222222-2222-2222-2222-222222222201",
                "cavendish": "22222222-2222-2222-2222-222222222201",
            },
            "default_name": "Regular Cavendish Bananas",
        },
    }

    # Unit labels for confirmation messages
    UNIT_LABELS: Dict[str, str] = {
        "apples": "kg", "oranges": "kg", "pomegranates": "kg",
        "bananas": "kg", "chicken": "kg", "atta": "kg", "tomatoes": "kg",
        "milk": "litre", "eggs": "pack", "rice": "kg", "olive oil": "bottle",
    }

    # Catalog of items we do NOT carry (to give fast truthful answers)
    KNOWN_UNAVAILABLE = {
        "broccoli", "mango", "mangoes", "strawberry", "strawberries",
        "grapes", "watermelon", "pineapple", "kiwi", "avocado",
        "spinach", "lettuce", "cabbage", "cauliflower", "carrot", "carrots",
        "onion", "onions", "potato", "potatoes", "pepper", "peppers",
    }

    def __init__(self):
        # Session state keyed by session_id
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "state": "IDLE",
                "pending_items": [],
                "current_item": None,
                "current_step": None,
                "selected_brand": None,
                "last_product_id": None,
            }
        return self.sessions[session_id]

    def _normalize_text(self, text: str) -> str:
        """
        Normalizes spoken phonetics, speech recognition homophones, and word numbers.
        """
        lower = text.lower()
        lower = re.sub(r"\b(at court|in court|to court|at caught|to card|to caught)\b", "to cart", lower)
        lower = re.sub(r"\b(atavan|ataven|atvan|atta-and|atta an)\b", "atta and", lower)
        lower = re.sub(r"\b(cut|had to cut|you had to cut)\b", "add", lower)
        lower = re.sub(r"\b(a couple of|a couple)\b", "2", lower)
        lower = re.sub(r"\b(a dozen|one dozen)\b", "12", lower)
        lower = re.sub(r"\b(half a dozen|half dozen)\b", "6", lower)
        lower = re.sub(r"\b(half a kilo|half kg|half a kg)\b", "0.5 kg", lower)
        lower = re.sub(r"\b(a|an|one)\b", "1", lower)
        lower = re.sub(r"\btwo\b", "2", lower)
        lower = re.sub(r"\bthree\b", "3", lower)
        lower = re.sub(r"\bfour\b", "4", lower)
        lower = re.sub(r"\bfive\b", "5", lower)
        lower = re.sub(r"\bsix\b", "6", lower)
        return lower

    def _extract_items(self, text: str) -> List[Dict[str, Any]]:
        """
        Parses item names, quantities, and units from the message.
        Matches patterns like '2 kg atta', '1 apple 1 orange and 2 pomegranates', 'atta'.
        """
        items: List[Dict[str, Any]] = []
        normalized = self._normalize_text(text)

        # Regular expressions for quantity + unit + item
        grocery_tokens = (
            r"(atta|flour|bananas?|banana|chicken|rice|eggs?|milk|olive oil|tomatoes?|"
            r"apples?|apple|oranges?|orange|pomegranates?|pomegranate|"
            r"broccoli|mango(?:es)?|strawberr(?:y|ies)|grapes|spinach|lettuce|cabbage|cauliflower|carrots?|onions?|potatoes?|peppers?)"
        )
        patterns = [
            rf"(\d+(?:\.\d+)?)\s*(kg|kilos?|kilo|g|grams?|packs?|pack|litres?|litre|l|bottles?|bottle|piece|pieces)?\s*(?:of\s+)?(?:[a-zA-Z]+\s+)*?{grocery_tokens}\b",
            rf"\b{grocery_tokens}\b",
        ]

        found_names = set()

        for match in re.finditer(patterns[0], normalized):
            qty_str = match.group(1)
            unit_str = match.group(2)
            raw_item = match.group(3)
            canonical = self._canonical_name(raw_item)
            if canonical not in found_names:
                canonical_unit = self.UNIT_LABELS.get(canonical, "unit")
                raw_qty = float(qty_str)
                try:
                    norm_qty = convert_quantity_to_canonical(
                        quantity=raw_qty,
                        user_unit=unit_str,
                        canonical_unit=canonical_unit,
                        product_name=canonical,
                    )
                except ValueError:
                    norm_qty = raw_qty
                items.append({
                    "name": canonical,
                    "quantity": norm_qty,
                    "unit": canonical_unit,
                })
                found_names.add(canonical)

        # Catch items mentioned without explicit quantity (default qty = 1.0)
        for match in re.finditer(patterns[1], normalized):
            canonical = self._canonical_name(match.group(1))
            if canonical not in found_names:
                items.append({
                    "name": canonical,
                    "quantity": 1.0,
                    "unit": "kg" if canonical in ("atta", "bananas", "chicken", "tomatoes", "apples", "oranges", "pomegranates") else "unit",
                })
                found_names.add(canonical)

        return items

    def _canonical_name(self, raw: str) -> str:
        r = raw.strip().lower()
        if "atta" in r or "flour" in r:
            return "atta"
        if "banana" in r:
            return "bananas"
        if "chicken" in r:
            return "chicken"
        if "rice" in r:
            return "rice"
        if "egg" in r:
            return "eggs"
        if "milk" in r:
            return "milk"
        if "oil" in r:
            return "olive oil"
        if "tomato" in r:
            return "tomatoes"
        if "apple" in r:
            return "apples"
        if "orange" in r:
            return "oranges"
        if "pom" in r:
            return "pomegranates"
        if "broccoli" in r:
            return "broccoli"
        if "mango" in r:
            return "mango"
        return r

    async def generate_response(
        self,
        message: str,
        session_id: str,
        history: Optional[List[ChatMessage]] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        session = self._get_or_create_session(session_id)
        text = message.strip()
        normalized_text = self._normalize_text(text)
        lower = normalized_text.lower()

        # ── Utility helpers ──────────────────────────────────────────────────

        def _resolve_variant(canonical: str, lower_msg: str) -> Optional[str]:
            """Return product_id if the message specifies a known variant, else None."""
            opts = self.DISAMBIGUATION_MAP.get(canonical, {}).get("options", {})
            for kw, pid in opts.items():
                if kw in lower_msg:
                    return pid
            return None

        def _build_add_response(pid: str, qty: float, name: str, unit: str) -> LLMResponse:
            unit_note = f"{int(qty) if qty.is_integer() else qty} {unit} of " if unit != "unit" else f"{int(qty) if qty.is_integer() else qty}× "
            return LLMResponse(
                tool_name="add_to_cart",
                tool_params={"product_id": pid, "quantity": qty},
                text_response=f"Got it! Adding {unit_note}{name} to your basket.",
            )

        # ── Handle special commands ───────────────────────────────────────────
        if re.search(r"\b(submit|place|confirm)\s+(?:the\s+|my\s+|this\s+)?order\b|\bbuy\s+now\b", lower) or any(term in lower for term in ["submit order", "place order", "confirm order", "buy now"]):
            return LLMResponse(
                tool_name="submit_order",
                tool_params={"delivery_address": "Downtown Dubai, UAE", "payment_method": "Card"},
                text_response="Submitting your basket for final order commitment.",
            )
        if any(term in lower for term in ["checkout", "preview order"]):
            return LLMResponse(
                tool_name="get_checkout_preview",
                tool_params={},
                text_response="Here is your checkout preview. Please review before confirming.",
            )
        if lower in ["view cart", "show cart", "cart", "basket", "my cart"]:
            return LLMResponse(
                tool_name="get_cart",
                tool_params={},
                text_response="Here is your current shopping basket.",
            )

        # ── Direct UUID add ───────────────────────────────────────────────────
        uuid_match = re.search(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", lower)
        if ("add" in lower or "cart" in lower) and uuid_match:
            prod_id = uuid_match.group(0)
            qty_match = re.search(r"(\d+(?:\.\d+)?)", lower)
            qty = float(qty_match.group(1)) if qty_match else 1.0
            return LLMResponse(
                tool_name="add_to_cart",
                tool_params={"product_id": prod_id, "quantity": qty},
                text_response=f"Adding {qty} unit(s) of product {prod_id} to your basket.",
            )

        # ── Catalog availability inquiry ──────────────────────────────────────
        availability_match = re.search(
            r"\b(?:do you have|do you carry|do you sell|have you got|is there|are there|can i get|any)\s+([a-zA-Z\s]+?)(?:\s+in stock|\s+available|\s+today|\?|$)",
            lower,
        )
        if availability_match:
            raw_q = availability_match.group(1).strip()
            clean_q = re.sub(r"^(some|any|fresh|a|an)\s+", "", raw_q).strip()
            if clean_q and clean_q not in ["cart", "basket", "it", "discount", "code"]:
                canonical = self._canonical_name(clean_q)
                if canonical in self.KNOWN_UNAVAILABLE:
                    return LLMResponse(
                        tool_name="search_products",
                        tool_params={"query": canonical},
                        text_response=f"Searching catalog for '{canonical}'...",
                    )
                return LLMResponse(
                    tool_name="search_products",
                    tool_params={"query": clean_q},
                    text_response=f"Searching our catalog for '{clean_q}'...",
                )

        # ── State machine: disambiguation responses ───────────────────────────
        state = session.get("state", "IDLE")
        awaiting_canon = session.get("awaiting_disambiguation_for")

        if state == "AWAITING_DISAMBIGUATION" and awaiting_canon:
            pid = _resolve_variant(awaiting_canon, lower)
            qty = session.get("pending_qty", 1.0)
            dm = self.DISAMBIGUATION_MAP.get(awaiting_canon, {})
            if pid:
                # Resolve the proper display name from options
                name = dm.get("default_name", awaiting_canon)
                for kw, kpid in dm.get("options", {}).items():
                    if kpid == pid and kw in lower:
                        # Look up the full display name from KNOWN_PRODUCT_LOOKUP
                        lookup_name = {
                            "66666666-6666-6666-6666-666666666601": "Al Ain Full Fat Milk 1L",
                            "66666666-6666-6666-6666-666666666602": "Almarai Low Fat Milk 1L",
                            "11111111-1111-1111-1111-111111111101": "Al Baker Chakki Fresh Atta",
                            "11111111-1111-1111-1111-111111111102": "Aashirvaad Chakki Fresh Atta",
                            "11111111-1111-1111-1111-111111111103": "Whole Wheat Atta",
                            "33333333-3333-3333-3333-333333333301": "Fresh Whole Chicken",
                            "33333333-3333-3333-3333-333333333302": "Fresh Chicken Breast Fillet",
                            "33333333-3333-3333-3333-333333333303": "Fresh Boneless Chicken Cubes",
                            "33333333-3333-3333-3333-333333333304": "Fresh Chicken Thighs",
                            "44444444-4444-4444-4444-444444444401": "Daawat Basmati Rice",
                            "44444444-4444-4444-4444-444444444402": "Sella Basmati Rice",
                            "22222222-2222-2222-2222-222222222201": "Regular Cavendish Bananas",
                            "22222222-2222-2222-2222-222222222202": "Organic Bananas",
                            "22222222-2222-2222-2222-222222222203": "Baby Bananas",
                        }
                        name = lookup_name.get(pid, name)
                        break
                unit = self.UNIT_LABELS.get(awaiting_canon, "unit")
                session["state"] = "IDLE"
                session["awaiting_disambiguation_for"] = None

                # Are there still pending multi-items?
                pending = session.get("pending_items", [])
                resp = _build_add_response(pid, qty, name, unit)
                if pending:
                    next_it = pending.pop(0)
                    session["pending_items"] = pending
                    next_canon = next_it["name"]
                    next_dm = self.DISAMBIGUATION_MAP.get(next_canon)
                    if next_dm:
                        session["state"] = "AWAITING_DISAMBIGUATION"
                        session["awaiting_disambiguation_for"] = next_canon
                        session["pending_qty"] = next_it["quantity"]
                        resp.text_response += f" Now, {next_dm['question']}"
                    else:
                        # Directly add unambiguous next item
                        next_pid = self.KNOWN_PRODUCT_LOOKUP.get(next_canon)
                        if next_pid:
                            session["state"] = "IDLE"
                            resp.tool_name = "add_to_cart"
                            resp.tool_params = {
                                "product_id": pid,
                                "quantity": qty,
                                "items": [
                                    {"product_id": pid, "quantity": qty, "name": awaiting_canon},
                                    {"product_id": next_pid, "quantity": next_it["quantity"], "name": next_canon},
                                ],
                            }
                return resp
            else:
                # Still can't resolve — re-ask
                return LLMResponse(
                    tool_name=None,
                    tool_params={},
                    text_response=dm.get("question", f"Which {awaiting_canon} would you prefer?"),
                )

        # ── Multi-item parsing ────────────────────────────────────────────────
        extracted = self._extract_items(normalized_text)
        is_add_intent = any(verb in lower for verb in [
            "add", "buy", "put", "cart", "order", "include", "need", "want", "get", "i need", "i want"
        ])

        if extracted and (is_add_intent or len(extracted) > 1):
            unavailable: List[Dict] = []
            ambiguous: List[Dict] = []
            to_add: List[Dict] = []

            for it in extracted:
                canonical = it["name"]
                # Check unavailable first
                if canonical in self.KNOWN_UNAVAILABLE:
                    unavailable.append(it)
                    continue
                # Check if needs disambiguation
                if canonical in self.DISAMBIGUATION_MAP:
                    pid = _resolve_variant(canonical, lower)
                    if pid:
                        name = self.DISAMBIGUATION_MAP[canonical].get("default_name", canonical)
                        to_add.append({**it, "product_id": pid, "resolved_name": name})
                    else:
                        ambiguous.append(it)
                else:
                    pid = self.KNOWN_PRODUCT_LOOKUP.get(canonical)
                    if pid:
                        to_add.append({**it, "product_id": pid, "resolved_name": canonical})
                    else:
                        unavailable.append(it)

            # Store classification for evaluator access
            session["last_items_unavailable"] = unavailable
            session["last_items_ambiguous"] = ambiguous
            session["last_items_to_add"] = to_add
            session["last_items_requested"] = extracted

            # Build response parts
            parts: List[str] = []

            # 1. Report unavailable items
            if unavailable:
                unavail_str = ", ".join(it["name"] for it in unavailable)
                parts.append(f"Sorry, we don't carry {unavail_str} in our store right now.")

            # 2. First ambiguous item → ask clarification, queue rest
            if ambiguous:
                first_ambig = ambiguous[0]
                remaining_ambig = ambiguous[1:]
                canon = first_ambig["name"]
                dm = self.DISAMBIGUATION_MAP[canon]

                session["state"] = "AWAITING_DISAMBIGUATION"
                session["awaiting_disambiguation_for"] = canon
                session["pending_qty"] = first_ambig["quantity"]
                # Queue remaining ambiguous + to_add for after disambiguation
                session["pending_items"] = [
                    *remaining_ambig,
                    *[{"name": it["resolved_name"], "quantity": it["quantity"]} for it in to_add]
                ]

                parts.append(dm["question"])

                # If there are items to add already (non-ambiguous), include them
                if to_add:
                    items_payload = [{"product_id": it["product_id"], "quantity": it["quantity"], "name": it["resolved_name"]} for it in to_add]
                    added_str = _build_confirmation_str(to_add, self.UNIT_LABELS)
                    parts.insert(-1, f"I'll add {added_str} now.")
                    return LLMResponse(
                        tool_name="add_to_cart",
                        tool_params={
                            "product_id": to_add[0]["product_id"],
                            "quantity": to_add[0]["quantity"],
                            "items": items_payload,
                        },
                        text_response=" ".join(parts),
                    )
                return LLMResponse(
                    tool_name="search_products",
                    tool_params={"query": canon},
                    text_response=" ".join(parts),
                )

            # 3. All items resolved and ready to add
            if to_add:
                added_str = _build_confirmation_str(to_add, self.UNIT_LABELS)
                parts.append(f"Adding {added_str} to your basket!")
                has_kg = any(self.UNIT_LABELS.get(it["name"], "unit") == "kg" for it in to_add)
                if has_kg:
                    parts.append("Fresh produce is sold by the kilo — min 1 kg per item.")
                items_payload = [
                    {"product_id": it["product_id"], "quantity": it["quantity"], "name": it["resolved_name"]}
                    for it in to_add
                ]
                session["state"] = "IDLE"
                return LLMResponse(
                    tool_name="add_to_cart",
                    tool_params={
                        "product_id": to_add[0]["product_id"],
                        "quantity": to_add[0]["quantity"],
                        "items": items_payload,
                    },
                    text_response=" ".join(parts),
                )

            # Only unavailable items in request
            if unavailable and not to_add and not ambiguous:
                parts.append("Would you like to pick something else? We have fresh apples, oranges, pomegranates, eggs, milk, chicken, and more.")
                return LLMResponse(
                    tool_name="search_products",
                    tool_params={"query": unavailable[0]["name"]},
                    text_response=" ".join(parts),
                )

        # ── Single add intent, single item ───────────────────────────────────
        if is_add_intent and extracted:
            it = extracted[0]
            canonical = it["name"]
            qty = it["quantity"]
            unit = self.UNIT_LABELS.get(canonical, "unit")

            if canonical in self.KNOWN_UNAVAILABLE:
                return LLMResponse(
                    tool_name="search_products",
                    tool_params={"query": canonical},
                    text_response=f"Sorry, we don't carry {canonical} right now. Can I help with something else?",
                )

            if canonical in self.DISAMBIGUATION_MAP:
                pid = _resolve_variant(canonical, lower)
                if pid:
                    dm = self.DISAMBIGUATION_MAP[canonical]
                    name = dm.get("default_name", canonical)
                    return _build_add_response(pid, qty, name, unit)
                else:
                    session["state"] = "AWAITING_DISAMBIGUATION"
                    session["awaiting_disambiguation_for"] = canonical
                    session["pending_qty"] = qty
                    session["pending_items"] = []
                    return LLMResponse(
                        tool_name="search_products",
                        tool_params={"query": canonical},
                        text_response=self.DISAMBIGUATION_MAP[canonical]["question"],
                    )

            pid = self.KNOWN_PRODUCT_LOOKUP.get(canonical)
            if pid:
                session["state"] = "IDLE"
                return _build_add_response(pid, qty, canonical.capitalize(), unit)
            else:
                # Unknown item — verify via search
                return LLMResponse(
                    tool_name="search_products",
                    tool_params={"query": canonical},
                    text_response=f"Let me check if we carry {canonical}...",
                )

        # ── Unknown add request with no parsed items ──────────────────────────
        if is_add_intent:
            add_match = re.search(
                r"\b(?:add|buy|put|get|need|want)\s+(?:\d+\s+)?(?:of\s+)?([a-zA-Z\s]+?)(?:\s+to cart|\s+in cart|\s+to basket|\s+in my basket|\s+please|$)",
                lower,
            )
            if add_match:
                item_requested = add_match.group(1).strip()
                item_clean = re.sub(r"^(one|two|a|an|some|fresh)\s+", "", item_requested).strip()
                if item_clean and item_clean not in ["it", "this", "them", "that", "cart", "basket", "court"]:
                    return LLMResponse(
                        tool_name="search_products",
                        tool_params={"query": item_clean},
                        text_response=f"Let me check if we carry {item_clean}...",
                    )

        # ── Default fallback ─────────────────────────────────────────────────
        return LLMResponse(
            tool_name=None,
            tool_params={},
            text_response=(
                "I'm your KON Commerce AI assistant! You can say things like "
                "'add 2 kg atta', 'I need an apple and two milk', or 'show my cart'."
            ),
        )


class GeminiProvider(LLMProvider):
    """
    Google Gemini AI provider utilizing native function calling declarations
    to propose governed commerce tools via manual execution mode.
    Uses the modern google-genai SDK.
    Gracefully falls back to FallbackProvider if credentials are not supplied or network fails.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        self.fallback = FallbackProvider()
        self._client: Optional[Any] = None
        self._initialized = False

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                self._initialized = True
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai Client: {e}")
                self._initialized = False

    def is_available(self) -> bool:
        return bool(self._initialized and self._client and self.api_key)

    async def generate_response(
        self,
        message: str,
        session_id: str,
        history: Optional[List[ChatMessage]] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Tool selection and conversational reasoning via Gemini native function calling.
        When Gemini is unavailable or fails, gracefully falls back to FallbackProvider.
        """
        if not self.is_available():
            return await self.fallback.generate_response(message, session_id, history, available_tools)

        try:
            from google.genai import types
            from app.tools.registry import tool_registry_service
            from app.governance.permissions import AgentPermissions

            allowed = AgentPermissions.ALLOWED_TOOLS_SHOPPING_AGENT
            decls = tool_registry_service.get_gemini_tool_declarations(allowed)

            config = types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=decls)] if decls else None,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                system_instruction=(
                    "You are the official KON AI Grocery Shopping Assistant in Dubai. "
                    "Your role is to understand customer grocery requests, choose appropriate commerce tools "
                    "(search_products, get_product_details, add_to_cart, update_cart_item, remove_from_cart, get_cart, get_checkout_preview, submit_order), "
                    "and explain results warmly in concise spoken language. "
                    "Do not invent product IDs; call search_products first if an ID is unknown."
                ),
            )

            contents = [types.Content(role="user", parts=[types.Part.from_text(text=message)])]
            res = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                ),
                timeout=5.0,
            )

            calls = res.function_calls or []
            if calls:
                first = calls[0]
                proposals = [
                    ToolCallProposal(name=c.name, args=dict(c.args or {}), id=getattr(c, "id", None))
                    for c in calls
                ]
                return LLMResponse(
                    tool_name=first.name,
                    tool_params=dict(first.args or {}),
                    text_response=res.text or "",
                    proposed_calls=proposals,
                )

            return LLMResponse(
                tool_name=None,
                tool_params={},
                text_response=res.text or "How can I help with your groceries today?",
            )
        except Exception as e:
            logger.warning(f"Gemini generation exception, falling back: {e}")
            return await self.fallback.generate_response(message, session_id, history, available_tools)

    async def generate_truthful_response(self, prompt: str) -> Optional[str]:
        if not self.is_available():
            return None
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=(
                    "You are KON AI speaking in Gemini Live Mode. "
                    "Be truthful, natural, and concise in exactly 1 spoken sentence. "
                    "Never hallucinate items that are not in stock or claim you added items that were not added."
                )
            )
            res = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self.model_name,
                    contents=[prompt],
                    config=config,
                ),
                timeout=3.0,
            )
            if res.text:
                return res.text.strip()
        except Exception as e:
            logger.warning(f"Truthful response generation skipped: {e}")
        return None
        return None
