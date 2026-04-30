from __future__ import annotations

from typing import Dict

from healthcoach.agents.react_executor import run_supervisor_react
from healthcoach.graph.state import HealthCoachState
from healthcoach.services.health_data import get_user_context


def load_context(state: HealthCoachState) -> Dict:
    profile = get_user_context(state["user_id"])
    profile.update(state.get("user_profile", {}))
    return {"user_profile": profile, "current_stage": "supervisor"}


def supervisor_agent(state: HealthCoachState) -> Dict:
    result = run_supervisor_react(state)
    return {
        "final_response": result["final_response"],
        "collected_facts": result.get("collected_facts", {}),
        "agent_steps": result.get("agent_steps", []),
        "current_stage": "done",
    }
