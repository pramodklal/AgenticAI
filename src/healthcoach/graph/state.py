from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class HealthCoachState(TypedDict):
    conversation_id: str
    user_id: str
    user_message: str
    user_profile: Dict[str, Any]
    collected_facts: Dict[str, Any]
    tool_results: List[Dict[str, Any]]
    agent_steps: List[Dict[str, Any]]
    current_stage: str
    final_response: Optional[str]
    requires_human_escalation: bool


def create_initial_state(
    conversation_id: str,
    user_id: str,
    user_message: str,
    profile: Dict[str, Any] | None = None,
) -> HealthCoachState:
    return HealthCoachState(
        conversation_id=conversation_id,
        user_id=user_id,
        user_message=user_message,
        user_profile=profile or {},
        collected_facts={},
        tool_results=[],
        agent_steps=[],
        current_stage="load_context",
        final_response=None,
        requires_human_escalation=False,
    )
