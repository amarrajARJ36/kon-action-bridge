"""
LLM-as-a-Judge Evaluation Layer
================================
Runs asynchronously after every conversation turn. Checks:
  1. Hallucination  — did the agent claim an action happened without tool execution?
  2. Omission       — did the agent silently skip items the user requested?
  3. Premature Action — did the agent add an ambiguous product without asking first?
  4. Intent Coverage — fraction of requested items that were addressed (available/explained).

Writes an EvaluationLog record to the database for the observability dashboard.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import EvaluationLog

logger = logging.getLogger(__name__)

# Products that have multiple variants and require disambiguation before adding
AMBIGUOUS_PRODUCTS = {
    "milk": ["Full Fat Milk 1L", "Low Fat Milk 1L"],
    "atta": ["Al Baker Chakki Fresh Atta", "Aashirvaad Chakki Fresh Atta", "Whole Wheat Atta"],
    "chicken": ["Fresh Whole Chicken", "Fresh Chicken Breast Fillet", "Fresh Boneless Chicken Cubes", "Fresh Chicken Thighs"],
    "rice": ["Daawat Basmati Rice", "Sella Basmati Rice"],
    "bananas": ["Regular Cavendish Bananas", "Organic Bananas", "Baby Bananas"],
}


class ConversationEvaluator:
    """
    Post-turn semantic quality evaluator (LLM-as-a-Judge pattern).
    Runs synchronously after tool execution but before returning the response
    so that every turn has a scored evaluation record.
    """

    async def evaluate(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
        trace_id: Optional[uuid.UUID],
        user_message: str,
        agent_response: str,
        tool_name_called: Optional[str],
        tool_params: Dict[str, Any],
        items_requested: List[Dict],      # from intent parser
        items_unavailable: List[Dict],    # search_products returned 0 results
        items_ambiguous: List[Dict],      # multi-variant products that need clarification
        items_added: List[Dict],          # actually cart-committed
        basket_updated: bool,
    ) -> EvaluationLog:
        """
        Score one conversation turn and persist the EvaluationLog record.
        """
        notes: List[str] = []
        hallucination = False
        omission = False
        premature_action = False
        verdict = "pass"

        # ── 1. Hallucination check ───────────────────────────────────────────
        # Agent claimed basket was updated but no add_to_cart tool ran
        if basket_updated and tool_name_called != "add_to_cart":
            hallucination = True
            notes.append(
                "HALLUCINATION: agent claimed basket_updated=True but tool was "
                f"'{tool_name_called}' (not add_to_cart)."
            )

        # Agent response mentions "added" / "in your cart" without tool execution
        add_phrases = ["added", "in your cart", "to your cart", "in your basket", "basket updated"]
        if tool_name_called not in ("add_to_cart", "update_cart_item") and any(
            p in agent_response.lower() for p in add_phrases
        ):
            hallucination = True
            notes.append(
                "HALLUCINATION: response text implies cart addition but no cart tool ran."
            )

        # ── 2. Omission check ────────────────────────────────────────────────
        # Items the user requested that were neither added, nor explained as unavailable,
        # nor awaiting disambiguation
        addressed_names = (
            {it["name"] for it in items_added}
            | {it["name"] for it in items_unavailable}
            | {it["name"] for it in items_ambiguous}
        )
        silently_dropped = [
            it for it in items_requested
            if it["name"] not in addressed_names
        ]
        if silently_dropped:
            omission = True
            dropped_str = ", ".join(it["name"] for it in silently_dropped)
            notes.append(
                f"OMISSION: the following requested items were silently skipped: {dropped_str}."
            )

        # ── 3. Premature Action check ────────────────────────────────────────
        # Agent added an ambiguous product (e.g. "milk") without first asking
        # which variant the user wants
        if tool_name_called == "add_to_cart":
            for it in items_added:
                if it["name"] in AMBIGUOUS_PRODUCTS and not _user_specified_variant(
                    user_message.lower(), it["name"]
                ):
                    premature_action = True
                    variants_str = " / ".join(AMBIGUOUS_PRODUCTS[it["name"]])
                    notes.append(
                        f"PREMATURE ACTION: '{it['name']}' was added without disambiguation. "
                        f"Available variants: {variants_str}."
                    )

        # ── 4. Intent Coverage Score ─────────────────────────────────────────
        total_requested = len(items_requested)
        total_addressed = len(addressed_names & {it["name"] for it in items_requested})
        coverage = (total_addressed / total_requested) if total_requested > 0 else 1.0

        if coverage < 1.0:
            notes.append(
                f"COVERAGE: only {total_addressed}/{total_requested} requested items addressed "
                f"(score: {coverage:.0%})."
            )

        # ── 5. Verdict ───────────────────────────────────────────────────────
        if hallucination or premature_action:
            verdict = "fail"
        elif omission or coverage < 1.0:
            verdict = "warn"
        else:
            verdict = "pass"

        # ── 6. Persist record ────────────────────────────────────────────────
        try:
            record = EvaluationLog(
                session_id=session_id,
                user_id=user_id,
                trace_id=trace_id,
                user_message=user_message,
                agent_response=agent_response,
                tool_name_called=tool_name_called,
                tool_params=tool_params,
                items_requested=items_requested,
                items_unavailable=items_unavailable,
                items_ambiguous=items_ambiguous,
                items_added=items_added,
                hallucination_detected=hallucination,
                omission_detected=omission,
                premature_action_detected=premature_action,
                intent_coverage_score=round(coverage, 4),
                evaluation_notes="\n".join(notes) if notes else "All checks passed.",
                evaluation_verdict=verdict,
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            logger.info(
                "EvalLog[%s] verdict=%s hallucination=%s omission=%s premature=%s coverage=%.0f%%",
                str(record.id)[:8],
                verdict,
                hallucination,
                omission,
                premature_action,
                coverage * 100,
            )
            return record
        except Exception as exc:
            logger.warning("EvaluationLog write failed (non-fatal): %s", exc)
            # Return an un-persisted record so callers still have the result
            return EvaluationLog(
                session_id=session_id,
                user_message=user_message,
                agent_response=agent_response,
                evaluation_verdict=verdict,
                evaluation_notes="\n".join(notes) if notes else "All checks passed.",
                hallucination_detected=hallucination,
                omission_detected=omission,
                premature_action_detected=premature_action,
                intent_coverage_score=round(coverage, 4),
            )


def _user_specified_variant(lower_msg: str, canonical: str) -> bool:
    """Returns True when the user message already specifies a known variant keyword."""
    variant_keywords: Dict[str, List[str]] = {
        "milk": ["full fat", "low fat", "skimmed", "semi"],
        "atta": ["al baker", "aashirvaad", "whole wheat", "chakki"],
        "chicken": ["boneless", "breast", "whole", "thigh", "cubes", "fillet"],
        "rice": ["basmati", "sella", "daawat"],
        "bananas": ["organic", "baby", "cavendish", "regular", "mini"],
    }
    for kw in variant_keywords.get(canonical, []):
        if kw in lower_msg:
            return True
    return False


# Singleton
conversation_evaluator = ConversationEvaluator()

