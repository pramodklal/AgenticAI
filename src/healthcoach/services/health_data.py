from __future__ import annotations

from typing import Any, Dict, List

from healthcoach.services.clients import get_nutrition_search_client, get_wellness_search_client


def get_user_context(user_id: str) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "age_band": "30-39",
        "injury_flags": [],
        "goals": ["energy", "consistency"],
    }


def get_sleep_summary(user_id: str) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "sleep_hours": 4.5,
        "sleep_quality": "poor",
        "recovery_signal": "low",
    }


def get_workout_summary(user_id: str) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "last_workout": "lower body strength",
        "planned_workout": "heavy squats",
        "recommended_alternative": "30-minute walk and mobility",
    }


def search_wellness_documents(query: str) -> List[Dict[str, Any]]:
    client = get_wellness_search_client()
    if client is None:
        return [
            {
                "title": "Sleep recovery basics",
                "snippet": "Low sleep duration increases fatigue and reduces training quality.",
            }
        ]

    results = client.search(search_text=query, top=3)
    return [
        {
            "title": item.get("title", "Wellness document"),
            "snippet": item.get("content", ""),
        }
        for item in results
    ]


def search_nutrition_documents(query: str) -> List[Dict[str, Any]]:
    client = get_nutrition_search_client()
    if client is None:
        return [
            {
                "title": "Energy-support meal",
                "snippet": "Choose lean protein, oats or rice, fruit, and hydration for steady energy.",
            }
        ]

    results = client.search(search_text=query, top=3)
    return [
        {
            "title": item.get("title", "Nutrition document"),
            "snippet": item.get("content", ""),
        }
        for item in results
    ]
