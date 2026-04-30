from __future__ import annotations

import sys
from time import perf_counter
from pathlib import Path

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


st.set_page_config(page_title="MyHealthCoach", page_icon=":material/health_and_safety:", layout="wide")

st.title("MyHealthCoach")
st.caption("Supervisor-driven wellness assistant built with LangGraph, Azure-ready services, and LangSmith tracing.")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = "demo-conversation"

with st.sidebar:
    st.subheader("User context")
    user_id = st.text_input("User ID", value="demo-user")
    gender = st.radio("Gender", ["Male", "Female", "Other"], index=0, horizontal=True)
    age = st.slider("Age", min_value=16, max_value=90, value=30, step=1)
    zip_code_raw = st.text_input("Zip / Pin code", value="", max_chars=10, placeholder="e.g. 08816")
    zip_code = zip_code_raw.strip() if zip_code_raw.strip().isdigit() else ""
    if zip_code_raw.strip() and not zip_code:
        st.warning("Zip code must contain digits only.")
    fitness_goal = st.selectbox("Primary goal", ["fat-loss", "muscle-gain", "maintenance", "recovery"])
    dietary_preference = st.selectbox("Dietary preference", ["balanced", "high-protein", "vegetarian", "vegan"])
    show_debug = st.toggle("Show agent facts", value=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask about workouts, nutrition, sleep, or recovery")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    graph = get_graph()
    initial_state = create_initial_state(
        conversation_id=st.session_state.conversation_id,
        user_id=user_id,
        user_message=prompt,
        profile={
            "gender": gender,
            "age": age,
            "zip_code": zip_code or None,
            "fitness_goal": fitness_goal,
            "dietary_preference": dietary_preference,
        },
    )
    started = perf_counter()
    final_state = graph.invoke(initial_state)
    elapsed_ms = int((perf_counter() - started) * 1000)
    answer = final_state.get("final_response", "I need more context before I can answer that.")
    eval_report = evaluate_agentic_run(
        user_message=prompt,
        final_response=answer,
        collected_facts=final_state.get("collected_facts", {}),
        elapsed_ms=elapsed_ms,
    )
    langsmith_feedback = build_langsmith_feedback_payload(eval_report, prefix="myhealthcoach")

    with st.chat_message("assistant"):
        st.markdown(answer)
        if show_debug:
            with st.expander("Collected facts and evaluation"):
                st.caption(
                    f"Latency: {elapsed_ms} ms | Overall score: {eval_report['overall_score']} | Passed: {eval_report['passed']}"
                )
                st.json(final_state.get("collected_facts", {}))
                st.json({"evaluation": eval_report})
                st.json({"langsmith_feedback": langsmith_feedback})

    st.session_state.messages.append({"role": "assistant", "content": answer})
