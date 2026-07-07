"""AI interaction seam for the simulation.

The MVP deliberately returns curated, deterministic hiring-manager responses.
A future version can replace this function with a hosted language-model call while
keeping scenario facts and scoring outside the model.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def generate_manager_response(
    question_id: str,
    scenario: Mapping[str, Any],
    conversation_history: Sequence[Mapping[str, str]] | None = None,
) -> str:
    """Return the approved manager response for an intake question.

    Parameters
    ----------
    question_id:
        Stable ID of the selected intake question.
    scenario:
        Loaded scenario dictionary.
    conversation_history:
        Reserved for a future LLM implementation. It is ignored in the MVP.
    """
    del conversation_history
    for item in scenario.get("intake_questions", []):
        if item.get("id") == question_id:
            return str(item.get("response", "No additional information is available."))
    return "The hiring manager cannot provide additional information on that point."
