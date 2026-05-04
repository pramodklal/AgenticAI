from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Tuple

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from healthcoach.graph.state import HealthCoachState
from healthcoach.services.health_data import (
    get_sleep_summary,
    get_user_context,
    get_workout_summary,
    search_nutrition_documents,
    search_wellness_documents,
)
from healthcoach.services.llm import get_chat_model


DOMAIN_TOOLSETS: Dict[str, Tuple[str, ...]] = {
    "wellness": ("sleep_summary", "wellness_docs", "user_context"),
    "fitness": ("workout_summary", "sleep_summary", "user_context"),
    "dietitian": ("nutrition_docs", "user_context"),
    "medicines": ("wellness_docs", "nutrition_docs", "user_context"),
    "mental_health": ("wellness_docs", "user_context"),
    "maternal_health": ("nutrition_docs", "wellness_docs", "user_context"),
    "women_health": ("wellness_docs", "nutrition_docs", "user_context"),
}


DOMAIN_INSTRUCTIONS: Dict[str, str] = {
    "wellness": "Focus on sleep, recovery load, stress management, and practical next-day habits.",
    "fitness": "Focus on safe training intensity, progressive overload tradeoffs, and recovery-adjusted plans.",
    "dietitian": "Focus on nutrition quality, macro balance, hydration, and practical meals for the stated goal.",
    "medicines": (
        "Always suggest relevant over-the-counter (OTC) remedies first — e.g. paracetamol/acetaminophen or ibuprofen for fever/pain, "
        "antihistamines for allergies, antacids for acidity, ORS for dehydration, lozenges for sore throat, saline drops for congestion. "
        "Be specific about the OTC category (not brand) and when to take it. "
        "Then, if the symptom description contains any red-flag pattern — fever lasting more than 3 days, chest pain, difficulty breathing, "
        "severe or worsening pain, confusion, persistent vomiting, blood in stool or urine, high/uncontrolled blood sugar, "
        "or any symptom persisting beyond a week — add a clearly marked RED FLAG warning recommending immediate medical evaluation. "
        "Do NOT raise a red flag for mild or short-duration symptoms. "
        "Do not provide diagnosis, specific doses, or prescription medication names."
    ),
    "mental_health": "Focus on supportive lifestyle strategies, stress de-escalation, and when to seek licensed support.",
    "maternal_health": "Focus on prenatal/postpartum-safe guidance, low-risk routines, and explicit escalation safety notes.",
    "women_health": "Focus on menstrual-cycle-aware habits, symptom-aware training and nutrition, and gynecology escalation signals.",
}

MEDICATION_DISCLAIMER = (
    "Medication suggestions are for informational purposes only. "
    "Consult a qualified doctor or physician before taking any suggested medicine."
)


def run_domain_react(domain: str, state: HealthCoachState) -> Dict[str, Any]:
    llm = get_chat_model()
    if llm is None:
        return _fallback_domain_result(domain, state)

    tools = _build_tools(state)
    allowed_tool_names = set(DOMAIN_TOOLSETS.get(domain, ()))
    scoped_tools = [t for t in tools if t.name in allowed_tool_names]

    system_prompt = (
        f"You are a helpful {domain.replace('_', ' ')} health advisor. "
        f"{DOMAIN_INSTRUCTIONS.get(domain, '')}\n\n"
        "When tools are available, use them to gather relevant user data before responding. "
        "Provide practical, non-diagnostic guidance that is safe and evidence-informed. "
        "Always advise consulting a qualified healthcare professional for medical concerns.\n\n"
        "Respond with a JSON object containing these fields:\n"
        "  recommendation: a short, actionable plan tailored to the user\n"
        "  rationale: brief explanation of why this advice fits the user's situation\n"
        "  safety_note: any important safety or escalation guidance (empty string if none)\n"
        "  confidence: one of low, medium, or high"
    )

    agent = create_react_agent(model=llm, tools=scoped_tools, prompt=system_prompt)
    payload = {
        "messages": [
            HumanMessage(
                content=(
                    f"{state['user_message']}\n\n"
                    f"User profile: {state.get('user_profile', {})}"
                )
            )
        ]
    }

    result = agent.invoke(payload)
    messages = result.get("messages", [])

    final_text = _extract_final_ai_text(messages)
    parsed = _parse_domain_json(final_text)
    tool_trace = _collect_tool_trace(messages)

    facts = {
        "recommendation": parsed["recommendation"],
        "rationale": parsed["rationale"],
        "safety_note": parsed["safety_note"],
        "confidence": parsed["confidence"],
    }

    return {
        "facts": facts,
        "tool_results": tool_trace,
        "agent_steps": [
            {
                "domain": domain,
                "message_count": len(messages),
                "used_tools": [item["tool"] for item in tool_trace],
            }
        ],
    }


def _build_tools(state: HealthCoachState):
    user_id = state["user_id"]
    query = state["user_message"]

    @tool("user_context", return_direct=False)
    def user_context_tool() -> Dict[str, Any]:
        "Get baseline profile context for the current user."
        return get_user_context(user_id)

    @tool("sleep_summary", return_direct=False)
    def sleep_summary_tool() -> Dict[str, Any]:
        "Get recent sleep and recovery summary for the current user."
        return get_sleep_summary(user_id)

    @tool("workout_summary", return_direct=False)
    def workout_summary_tool() -> Dict[str, Any]:
        "Get recent and planned workout summary for the current user."
        return get_workout_summary(user_id)

    @tool("wellness_docs", return_direct=False)
    def wellness_docs_tool() -> List[Dict[str, Any]]:
        "Search wellness guidance documents related to the user question."
        return search_wellness_documents(query)

    @tool("nutrition_docs", return_direct=False)
    def nutrition_docs_tool() -> List[Dict[str, Any]]:
        "Search nutrition guidance documents related to the user question."
        return search_nutrition_documents(query)

    return [
        user_context_tool,
        sleep_summary_tool,
        workout_summary_tool,
        wellness_docs_tool,
        nutrition_docs_tool,
    ]


def _extract_final_ai_text(messages: List[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            content = message.content
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
                return "\n".join([t for t in text_parts if t]).strip()
    return ""


def _parse_domain_json(text: str) -> Dict[str, str]:
    default = {
        "recommendation": "Use a lighter plan today and prioritize hydration, sleep, and consistency.",
        "rationale": "Based on current context, a conservative and sustainable plan is safer.",
        "safety_note": "If symptoms worsen or feel severe, seek qualified medical support.",
        "confidence": "medium",
    }

    if not text:
        return default

    clean = text.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        if len(parts) > 1:
            clean = parts[1]
        if clean.startswith("json"):
            clean = clean[4:]
        clean = clean.strip()

    try:
        parsed = json.loads(clean)
        recommendation = str(parsed.get("recommendation", default["recommendation"])).strip()
        rationale = str(parsed.get("rationale", default["rationale"])).strip()
        safety_note = str(parsed.get("safety_note", "")).strip()
        confidence = str(parsed.get("confidence", default["confidence"])).strip().lower()
        if confidence not in {"low", "medium", "high"}:
            confidence = "medium"
        return {
            "recommendation": recommendation or default["recommendation"],
            "rationale": rationale or default["rationale"],
            "safety_note": safety_note,
            "confidence": confidence,
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return default


def _collect_tool_trace(messages: List[Any]) -> List[Dict[str, Any]]:
    trace: List[Dict[str, Any]] = []
    for message in messages:
        if isinstance(message, ToolMessage):
            content = message.content
            if not isinstance(content, str):
                content = json.dumps(content)

            tool_name = message.name or ""
            is_consult_tool = tool_name.startswith("consult_") and tool_name.endswith("_advisor")

            # Preserve full advisor JSON payloads so evaluator grounding can parse recommendation/rationale/confidence.
            # Keep a cap for other tools to avoid oversized observations.
            observation = content if is_consult_tool else content[:2000]
            trace.append(
                {
                    "tool": tool_name,
                    "observation": observation,
                }
            )
    return trace


# Maps health domains to NPI taxonomy search terms
_DOMAIN_SPECIALTY: Dict[str, str] = {
    "wellness": "Internal Medicine",
    "fitness": "Physical Therapist",
    "dietitian": "Dietitian",
    "medicines": "Internal Medicine",
    "mental_health": "Psychiatry",
    "maternal_health": "Obstetrics",
    "women_health": "Gynecology",
}


_MEDICATION_HINTS: Tuple[str, ...] = (
    "medicine",
    "medicines",
    "medication",
    "medications",
    "tablet",
    "pill",
    "drug",
    "syrup",
    "antibiotic",
    "painkiller",
)


# Fallback taxonomy chains: if the LLM-supplied specialty returns 0 NPI results,
# try these broader terms in order before giving up.
_NPI_FALLBACK_TAXONOMIES: Dict[str, List[str]] = {
    "General Practitioner": ["Family Medicine", "Internal Medicine", "General Practice"],
    "General Practice":     ["Family Medicine", "Internal Medicine"],
    "Family Medicine":      ["Internal Medicine"],
    "Internal Medicine":    ["Family Medicine", "General Practice"],
    "Psychiatry":           ["Psychiatry & Neurology", "Mental Health"],
    "Obstetrics":           ["Obstetrics & Gynecology", "Gynecology"],
    "Gynecology":           ["Obstetrics & Gynecology"],
    "Dietitian":            ["Nutrition", "Dietetics"],
    "Physical Therapist":   ["Physical Therapy", "Orthopedic"],
    "Ophthalmology":        ["Ophthalmology"],
}


def _geocode_us_zip(zip_code: str) -> tuple[float, float] | None:
    """Geocode a US zip code to (lat, lon) using Nominatim for distance sorting."""
    params = urllib.parse.urlencode({
        "postalcode": zip_code,
        "country": "US",
        "format": "json",
        "limit": 1,
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "MyHealthCoach/1.0 (healthcoach-app)"})
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:  # nosec B310
            data = json.loads(resp.read().decode())
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    import math
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _npi_fetch(zip_code: str, taxonomy: str, limit: int) -> List[Dict[str, Any]]:
    """Single NPI Registry API call for one taxonomy term."""
    params = urllib.parse.urlencode({
        "version": "2.1",
        "enumeration_type": "NPI-1",
        "taxonomy_description": taxonomy,
        "postal_code": zip_code,
        "limit": limit,
    })
    url = f"https://npiregistry.cms.hhs.gov/api/?{params}"
    with urllib.request.urlopen(url, timeout=8) as resp:  # nosec B310
        return json.loads(resp.read().decode()).get("results", [])


def _lookup_doctors_npi(zip_code: str, specialty: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Query the free NPI Registry API for providers near a US zip code.
    Falls back to broader taxonomy terms if the requested specialty returns 0 results.
    Results are sorted nearest-first using Nominatim geocoding of the zip code.
    """
    # Build the list of taxonomy terms to try in order
    taxonomies_to_try = [specialty] + _NPI_FALLBACK_TAXONOMIES.get(specialty, [])

    raw_records: List[Any] = []
    used_taxonomy = specialty
    try:
        for tax in taxonomies_to_try:
            records = _npi_fetch(zip_code, tax, limit * 3)  # fetch extra for distance sort
            if records:
                raw_records = records
                used_taxonomy = tax
                break
    except Exception:
        return []

    if not raw_records:
        return []

    # Geocode the zip for distance sorting (best-effort; skip if unavailable)
    origin = _geocode_us_zip(zip_code)

    results = []
    for record in raw_records:
        basic = record.get("basic", {})
        addresses = record.get("addresses", [])
        practice = next(
            (a for a in addresses if a.get("address_purpose") == "LOCATION"),
            addresses[0] if addresses else {},
        )
        taxonomies = record.get("taxonomies", [])
        primary_taxonomy = next(
            (t.get("desc", used_taxonomy) for t in taxonomies if t.get("primary")),
            used_taxonomy,
        )
        results.append({
            "name": (
                f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip()
                or basic.get("organization_name", "Unknown")
            ),
            "specialty": primary_taxonomy,
            "address": (
                f"{practice.get('address_1', '')} {practice.get('city', '')} "
                f"{practice.get('state', '')} {practice.get('postal_code', '')}".strip()
            ),
            "phone": practice.get("telephone_number", "N/A"),
            "npi": record.get("number", ""),
            "_lat": practice.get("latitude"),
            "_lon": practice.get("longitude"),
        })

    # Sort nearest-first when origin coordinates are available
    if origin:
        olat, olon = origin
        def _dist(r: Dict[str, Any]) -> float:
            try:
                return _haversine_km(olat, olon, float(r["_lat"]), float(r["_lon"]))
            except (TypeError, ValueError):
                return 9999.0
        results.sort(key=_dist)

    # Strip internal lat/lon keys and return top N
    for r in results:
        r.pop("_lat", None)
        r.pop("_lon", None)
    return results[:limit]


def _geocode_india_pincode(pincode: str) -> tuple[float, float] | None:
    """Convert an Indian pincode to (lat, lon) using Nominatim."""
    params = urllib.parse.urlencode({
        "postalcode": pincode,
        "country": "India",
        "format": "json",
        "limit": 1,
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "MyHealthCoach/1.0 (healthcoach-app)"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:  # nosec B310
            data = json.loads(resp.read().decode())
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


def _lookup_doctors_osm(lat: float, lon: float, specialty: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Query Overpass API for clinics/doctors within 20 miles of a lat/lon point.
    Results are sorted nearest-first.
    """
    radius = 32186  # 20 miles in metres
    overpass_query = f"""
[out:json][timeout:15];
(
  node["amenity"="doctors"](around:{radius},{lat},{lon});
  node["amenity"="clinic"](around:{radius},{lat},{lon});
  node["amenity"="hospital"](around:{radius},{lat},{lon});
  way["amenity"="clinic"](around:{radius},{lat},{lon});
  way["amenity"="hospital"](around:{radius},{lat},{lon});
);
out center {limit * 5};
""".strip()
    encoded = urllib.parse.urlencode({"data": overpass_query}).encode()
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=encoded,
        headers={"User-Agent": "MyHealthCoach/1.0 (healthcoach-app)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
            data = json.loads(resp.read().decode())
        candidates = []
        seen: set = set()
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name") or tags.get("name:en") or tags.get("operator", "")
            if not name or name in seen:
                continue
            seen.add(name)
            elat = element.get("lat") or element.get("center", {}).get("lat")
            elon = element.get("lon") or element.get("center", {}).get("lon")
            addr_parts = [
                tags.get("addr:housenumber", ""),
                tags.get("addr:street", ""),
                tags.get("addr:city", ""),
                tags.get("addr:state", ""),
                tags.get("addr:postcode", ""),
            ]
            address = " ".join(p for p in addr_parts if p).strip() or f"({elat}, {elon})"
            dist_km = _haversine_km(lat, lon, float(elat), float(elon)) if elat and elon else 9999.0
            candidates.append({
                "name": name,
                "specialty": tags.get("healthcare:speciality") or specialty,
                "address": address,
                "phone": tags.get("phone") or tags.get("contact:phone", "N/A"),
                "source": "OpenStreetMap",
                "_dist_km": dist_km,
            })
        # Sort nearest-first and return top N
        candidates.sort(key=lambda r: r["_dist_km"])
        results = []
        for r in candidates[:limit]:
            r.pop("_dist_km", None)
            results.append(r)
        return results
    except Exception:
        return []


def _lookup_nearby_doctors(zip_code: str, specialty: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Route to NPI (US 5-digit) or OpenStreetMap Overpass (India 6-digit) based on zip length."""
    if len(zip_code) == 6 and zip_code.isdigit():
        # Indian pincode — use Nominatim + Overpass
        coords = _geocode_india_pincode(zip_code)
        if coords is None:
            return []
        lat, lon = coords
        return _lookup_doctors_osm(lat, lon, specialty, limit)
    else:
        # Assume US zip code — use NPI Registry
        return _lookup_doctors_npi(zip_code, specialty, limit)


def _build_domain_tools(state: HealthCoachState):
    """Wrap each domain's ReAct advisor as a LangChain tool for the supervisor agent."""

    @tool("consult_wellness_advisor")
    def consult_wellness(query: str) -> str:
        """Consult the wellness specialist for sleep quality, stress, fatigue, and recovery guidance."""
        domain_state = {**state, "user_message": query or state["user_message"]}
        result = run_domain_react("wellness", domain_state)
        return json.dumps(result["facts"])

    @tool("consult_fitness_advisor")
    def consult_fitness(query: str) -> str:
        """Consult the fitness specialist for workout planning, training intensity, and exercise safety."""
        domain_state = {**state, "user_message": query or state["user_message"]}
        result = run_domain_react("fitness", domain_state)
        return json.dumps(result["facts"])

    @tool("consult_dietitian_advisor")
    def consult_dietitian(query: str) -> str:
        """Consult the dietitian specialist for nutrition, meal planning, macros, and hydration."""
        domain_state = {**state, "user_message": query or state["user_message"]}
        result = run_domain_react("dietitian", domain_state)
        return json.dumps(result["facts"])

    @tool("consult_medicines_advisor")
    def consult_medicines(query: str) -> str:
        """Consult the medicines specialist for symptom-aware, non-prescriptive medication guidance with safety cautions."""
        domain_state = {**state, "user_message": query or state["user_message"]}
        result = run_domain_react("medicines", domain_state)
        facts = result["facts"]
        safety_note = str(facts.get("safety_note") or "").strip()
        if MEDICATION_DISCLAIMER.lower() not in safety_note.lower():
            facts["safety_note"] = f"{safety_note}\n{MEDICATION_DISCLAIMER}".strip()
        return json.dumps(facts)

    @tool("consult_mental_health_advisor")
    def consult_mental_health(query: str) -> str:
        """Consult the mental health specialist for anxiety, low mood, stress de-escalation, and emotional wellbeing."""
        domain_state = {**state, "user_message": query or state["user_message"]}
        result = run_domain_react("mental_health", domain_state)
        return json.dumps(result["facts"])

    @tool("consult_maternal_health_advisor")
    def consult_maternal_health(query: str) -> str:
        """Consult the maternal health specialist for prenatal and postpartum safe routines and escalation guidance."""
        domain_state = {**state, "user_message": query or state["user_message"]}
        result = run_domain_react("maternal_health", domain_state)
        return json.dumps(result["facts"])

    @tool("consult_women_health_advisor")
    def consult_women_health(query: str) -> str:
        """Consult the women's health specialist for menstrual cycle, PCOS, menopause, and hormone wellbeing."""
        domain_state = {**state, "user_message": query or state["user_message"]}
        result = run_domain_react("women_health", domain_state)
        return json.dumps(result["facts"])

    zip_code = str(state.get("user_profile", {}).get("zip_code") or "")

    @tool("find_nearby_doctors")
    def find_nearby_doctors(specialty: str) -> str:
        """Find up to 3 licensed doctors or specialists near the user's zip code. \
Call this when recommending the user see a healthcare professional. \
Pass the relevant medical specialty (e.g. Obstetrics, Psychiatry, Dietitian, Physical Therapist)."""
        if not zip_code:
            return json.dumps({"error": "No zip code provided by the user."})
        doctors = _lookup_nearby_doctors(zip_code, specialty)
        if not doctors:
            return json.dumps({"message": f"No results found for {specialty} near {zip_code}."})
        return json.dumps({"zip_code": zip_code, "specialty": specialty, "doctors": doctors})

    return [
        consult_wellness,
        consult_fitness,
        consult_dietitian,
        consult_medicines,
        consult_mental_health,
        consult_maternal_health,
        consult_women_health,
        find_nearby_doctors,
    ]


def run_supervisor_react(state: HealthCoachState) -> Dict[str, Any]:
    """Top-level ReAct supervisor. The LLM decides which domain specialists to consult
    and in what order, then synthesizes a unified health coaching response."""
    llm = get_chat_model()
    if llm is None:
        return _fallback_supervisor(state)

    domain_tools = _build_domain_tools(state)

    system_prompt = (
        "You are a comprehensive health coaching supervisor with access to specialist advisors. "
        "IMPORTANT: You MUST always call at least one specialist advisor tool before composing your final answer. "
        "Never answer from your own knowledge alone — always ground your response in tool observations. "
        "Based on the user's question, identify the relevant domains and call the matching specialist tools:\n"
        "  - Symptoms, medication, fever, infection, eye flu, body pain → consult_medicines_advisor\n"
        "  - Sleep, fatigue, stress, recovery, general wellness → consult_wellness_advisor\n"
        "  - Workouts, training, exercise → consult_fitness_advisor\n"
        "  - Diet, nutrition, meal plan, hydration → consult_dietitian_advisor\n"
        "  - Anxiety, depression, mental health, mood → consult_mental_health_advisor\n"
        "  - Pregnancy, prenatal, postpartum → consult_maternal_health_advisor\n"
        "  - PCOS, menopause, women's health → consult_women_health_advisor\n"
        "When multiple domains apply, call all relevant specialists and synthesize their advice. "
        "IMPORTANT FORMATTING RULE: When composing your final answer, every section heading MUST "
        "include the name of the specialist agent that provided that advice, in the format: "
        "'Section Title by <Agent Name>'. "
        "Use these exact agent names: Wellness Agent, Fitness Agent, Dietitian Agent, "
        "Medicines Agent, Mental Health Agent, Maternal Health Agent, Women Health Agent. "
        "Examples: 'Immediate Relief by Medicines Agent', 'Sleep & Recovery by Wellness Agent', "
        "'Exercise Plan by Fitness Agent', 'Nutrition Tips by Dietitian Agent'. "
        "If a section combines advice from multiple agents, list both: "
        "'Recovery Plan by Wellness Agent & Fitness Agent'. "
        "Keep advice non-diagnostic, practical, and safe. "
        "For medicine-related questions, you may suggest only high-level options and must include a disclaimer "
        "to consult a qualified doctor or physician before taking any medicine. "
        "When the advice involves seeing a healthcare professional, use the find_nearby_doctors tool "
        "to locate up to 3 relevant specialists near the user and include them in your response."
    )

    agent = create_react_agent(model=llm, tools=domain_tools, prompt=system_prompt)
    payload = {
        "messages": [
            HumanMessage(
                content=(
                    f"{state['user_message']}\n\n"
                    f"User profile: {state.get('user_profile', {})}"
                )
            )
        ]
    }

    result = agent.invoke(payload)
    messages = result.get("messages", [])

    final_text = _extract_final_ai_text(messages)
    tool_trace = _collect_tool_trace(messages)
    final_text = _apply_medication_disclaimer(
        final_text,
        user_message=state.get("user_message", ""),
        tool_trace=tool_trace,
    )

    # Reconstruct collected_facts from domain tool observations
    collected_facts: Dict[str, Any] = {}
    for item in tool_trace:
        tool_name = item["tool"]
        if tool_name == "find_nearby_doctors":
            try:
                collected_facts["nearby_doctors"] = json.loads(item["observation"])
            except (json.JSONDecodeError, TypeError):
                collected_facts["nearby_doctors"] = {"observation": item["observation"]}
        else:
            domain = tool_name.replace("consult_", "").replace("_advisor", "")
            try:
                facts = json.loads(item["observation"])
                collected_facts[domain] = facts
            except (json.JSONDecodeError, TypeError):
                collected_facts[domain] = {"observation": item["observation"]}

    return {
        "final_response": final_text,
        "collected_facts": collected_facts,
        "agent_steps": [
            {
                "supervisor": True,
                "message_count": len(messages),
                "domains_consulted": [item["tool"] for item in tool_trace],
            }
        ],
    }


def _fallback_supervisor(state: HealthCoachState) -> Dict[str, Any]:
    return {
        "final_response": "I recommend consulting a qualified healthcare professional for personalized guidance.",
        "collected_facts": {},
        "agent_steps": [],
    }


def _fallback_domain_result(domain: str, state: HealthCoachState) -> Dict[str, Any]:
    defaults = {
        "wellness": "Prioritize recovery and reduce training intensity today.",
        "fitness": "Use a moderate workout and scale intensity to recovery.",
        "dietitian": "Use a high-protein meal with complex carbs and fluids for steady energy.",
        "medicines": "For mild symptoms, consider only basic over-the-counter options after professional advice and avoid self-prescribing.",
        "mental_health": "Use a low-pressure plan with breathing, brief movement, and social support.",
        "maternal_health": "Follow prenatal-safe routines and confirm significant changes with your OB-GYN or midwife.",
        "women_health": "Track cycle symptoms and align movement and nutrition to symptom intensity.",
    }
    return {
        "facts": {
            "recommendation": defaults.get(domain, defaults["wellness"]),
            "rationale": "Fallback mode was used because model access was unavailable.",
            "safety_note": "Seek professional care for persistent or severe symptoms.",
            "confidence": "low",
        },
        "tool_results": [],
        "agent_steps": [{"domain": domain, "message_count": 0, "used_tools": []}],
    }


def _apply_medication_disclaimer(final_text: str, user_message: str, tool_trace: List[Dict[str, Any]]) -> str:
    if not final_text:
        return final_text

    used_medicine_tool = any(item.get("tool") == "consult_medicines_advisor" for item in tool_trace)
    lower_query = str(user_message or "").lower()
    hints_present = any(hint in lower_query for hint in _MEDICATION_HINTS)

    if not (used_medicine_tool or hints_present):
        return final_text

    if MEDICATION_DISCLAIMER.lower() in final_text.lower():
        return final_text

    return f"{final_text}\n\n{MEDICATION_DISCLAIMER}"
