from __future__ import annotations

import sys
from time import perf_counter
from pathlib import Path

from PIL import Image
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from healthcoach.graph.workflow import build_graph
from healthcoach.graph.state import create_initial_state
from healthcoach.evaluation import evaluate_agentic_run
from healthcoach.evaluation.langsmith_feedback import build_langsmith_feedback_payload


@st.cache_resource
def get_graph():
    return build_graph()


def display_name_from_user_id(raw_user_id: str) -> str:
    cleaned = (raw_user_id or "").strip().replace("-", " ").replace("_", " ")
    return cleaned.title() if cleaned else "User"


def build_domain_directive(selected_domain: str) -> str:
    if selected_domain == "auto":
        return ""
    if selected_domain == "medicines":
        return (
            "Domain preference: medicines. Prioritize the medicines specialist for symptom-aware, "
            "non-prescriptive guidance and include a physician consultation disclaimer."
        )
    return f"Domain preference: {selected_domain}. Prioritize this specialist unless user intent strongly requires others."


def format_agent_contributions(collected_facts: dict) -> str:
    ordered_domains = [
        ("wellness", "Wellness Agent"),
        ("fitness", "Fitness Agent"),
        ("dietitian", "Dietitian Agent"),
        ("mental_health", "Mental Health Agent"),
        ("maternal_health", "Maternal Health Agent"),
        ("women_health", "Women Health Agent"),
        ("medicines", "Medicines Agent"),
    ]

    sections: list[str] = []
    for domain_key, agent_label in ordered_domains:
        facts = collected_facts.get(domain_key)
        if not isinstance(facts, dict):
            continue

        recommendation = str(facts.get("recommendation") or "").strip()
        rationale = str(facts.get("rationale") or "").strip()
        safety_note = str(facts.get("safety_note") or "").strip()
        confidence = str(facts.get("confidence") or "").strip()

        content_parts: list[str] = []
        if recommendation:
            content_parts.append(f"Recommendation: {recommendation}")
        if rationale:
            content_parts.append(f"Why: {rationale}")
        if safety_note:
            content_parts.append(f"Safety: {safety_note}")
        if confidence:
            content_parts.append(f"Confidence: {confidence}")

        if content_parts:
            sections.append(f"#### {agent_label}\n" + "\n\n".join(content_parts))

    if not sections:
        return ""

    return "### Agent responses by specialist\n\n" + "\n\n".join(sections)


st.set_page_config(page_title="MyHealthCoach", page_icon=":material/health_and_safety:", layout="wide")

_banner_path = ROOT / "assets" / "banner.png"
if _banner_path.exists():
    st.image(str(_banner_path), use_container_width=True)
else:
    _logo_path = ROOT / "assets" / "logo.png"
    if _logo_path.exists():
        st.image(str(_logo_path), width=480)
    else:
        st.title("MyHealthCoach")
st.caption("Supervisor-driven wellness assistant built with LangGraph, Azure-ready services, and LangSmith tracing.")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = "demo-conversation"

with st.sidebar:
    _sidebar_logo = ROOT / "assets" / "logo.png"
    if _sidebar_logo.exists():
        st.image(str(_sidebar_logo), use_container_width=True)
        st.divider()
    st.subheader("User context")
    user_id = st.text_input("User ID", value="demo-user")
    gender = st.radio("Gender", ["Male", "Female", "Other"], index=0, horizontal=True)
    age = st.slider("Age", min_value=16, max_value=90, value=30, step=1)
    zip_code_raw = st.text_input("Zip / Pin code", value="", max_chars=10, placeholder="e.g. 08816")
    zip_code = zip_code_raw.strip() if zip_code_raw.strip().isdigit() else ""
    if zip_code_raw.strip() and not zip_code:
        st.warning("Zip code must contain digits only.")
    fitness_goal = st.selectbox(
        "Primary goal",
        [
            "fat-loss",
            "muscle-gain",
            "maintenance",
            "recovery",
            "improve-endurance",
            "increase-flexibility",
            "manage-diabetes",
            "manage-hypertension",
            "manage-cholesterol",
            "improve-sleep",
            "stress-reduction",
            "weight-gain",
            "post-injury-rehab",
            "pre-diabetic-management",
            "heart-health",
        ],
    )
    dietary_preference = st.selectbox("Dietary preference", ["balanced", "high-protein", "vegetarian", "vegan"])
    domain_choice = st.selectbox(
        "Preferred advisor domain",
        [
            "auto",
            "wellness",
            "fitness",
            "dietitian",
            "medicines",
            "mental_health",
            "maternal_health",
            "women_health",
        ],
        index=0,
        help="Choose a specialist to prioritize. Select medicines to explicitly route medicine/symptom requests.",
    )
    show_agent_responses = st.toggle("Show per-agent responses", value=True)
    st.caption("Shows what each specialist agent (Medicines, Wellness, Fitness…) individually recommended. Reveals which agents were consulted for your query.")
    show_debug = st.toggle("Show agent facts", value=True)
    st.caption("Shows raw JSON: collected facts, evaluation scores (6 checks), latency, and LangSmith feedback payload. Useful for debugging and demos.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)

prompt = st.chat_input("Ask about workouts, nutrition, sleep, recovery, or medicines")

if prompt:
    is_first_assistant_response = not any(msg.get("role") == "assistant" for msg in st.session_state.messages)
    display_name = display_name_from_user_id(user_id)
    domain_directive = build_domain_directive(domain_choice)
    effective_prompt = f"{domain_directive}\n\nUser question: {prompt}" if domain_directive else prompt

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    graph = get_graph()
    initial_state = create_initial_state(
        conversation_id=st.session_state.conversation_id,
        user_id=user_id,
        user_message=effective_prompt,
        profile={
            "gender": gender,
            "age": age,
            "zip_code": zip_code or None,
            "fitness_goal": fitness_goal,
            "dietary_preference": dietary_preference,
            "preferred_domain": domain_choice,
        },
    )
    started = perf_counter()
    final_state = graph.invoke(initial_state)
    elapsed_ms = int((perf_counter() - started) * 1000)
    answer = final_state.get("final_response", "I need more context before I can answer that.")
    agent_contributions_md = format_agent_contributions(final_state.get("collected_facts", {}))
    eval_report = evaluate_agentic_run(
        user_message=effective_prompt,
        final_response=answer,
        collected_facts=final_state.get("collected_facts", {}),
        elapsed_ms=elapsed_ms,
    )
    langsmith_feedback = build_langsmith_feedback_payload(eval_report, prefix="myhealthcoach")

    _goal_label = fitness_goal.replace("-", " ").title()
    _diet_label = dietary_preference.replace("-", " ").title()
    _domain_label = domain_choice.replace("_", " ").title() if domain_choice != "auto" else ""
    _context_parts = [f"primary goal: <b>{_goal_label}</b>", f"dietary preference: <b>{_diet_label}</b>"]
    if _domain_label:
        _context_parts.append(f"focus area: <b>{_domain_label}</b>")
    _context_str = ", ".join(_context_parts)

    # Use the raw user prompt as the highlighted condition (capped at 60 chars for readability)
    _condition_raw = prompt.strip()
    _condition_short = _condition_raw if len(_condition_raw) <= 60 else _condition_raw[:57] + "…"
    _condition_span = (
        f"<span style='color:#E65100; font-weight:700;'>&ldquo;{_condition_short}&rdquo;</span>"
    )

    _greeting_html = (
        f"<span style='color:#0C3D82; font-weight:700; font-size:1.05rem;'>"
        f"Hello {display_name}! I am your MyHealthCoach assistant. "
        f"Based on your profile ({_context_str}), "
        f"I am here to help you with {_condition_span}"
        f"<span style='color:#0C3D82; font-weight:700; font-size:1.05rem;'>"
        f" with personalized workouts, nutrition, recovery, medicines, "
        f"and practical daily wellness guidance tailored to your needs."
        f"</span>"
        f"</span>"
    )
    _agent_section = agent_contributions_md if show_agent_responses else ""
    _assistant_with_agents = f"{answer}\n\n{_agent_section}" if _agent_section else answer
    assistant_content = (
        f"{_greeting_html}\n\n{_assistant_with_agents}"
        if is_first_assistant_response
        else _assistant_with_agents
    )

    with st.chat_message("assistant"):
        if is_first_assistant_response:
            st.markdown(_greeting_html, unsafe_allow_html=True)
            st.markdown(answer)
            if _agent_section:
                st.markdown(_agent_section)
        else:
            st.markdown(assistant_content)
        if show_debug:
            with st.expander("Collected facts and evaluation"):
                st.caption(
                    f"Latency: {elapsed_ms} ms | Overall score: {eval_report['overall_score']} | Passed: {eval_report['passed']}"
                )
                st.json(final_state.get("collected_facts", {}))
                st.json({"evaluation": eval_report})
                st.json({"langsmith_feedback": langsmith_feedback})

    st.session_state.messages.append({"role": "assistant", "content": assistant_content})
