from __future__ import annotations

from langgraph.graph import END, StateGraph

from healthcoach.graph.nodes import load_context, supervisor_agent
from healthcoach.graph.state import HealthCoachState


def build_graph():
    graph = StateGraph(HealthCoachState)
    graph.add_node("load_context", load_context)
    graph.add_node("supervisor", supervisor_agent)

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "supervisor")
    graph.add_edge("supervisor", END)

    return graph.compile()
