from __future__ import annotations

from typing import Any, Dict, Iterable, List


def build_langsmith_feedback_payload(
    evaluation_report: Dict[str, Any],
    prefix: str = "myhealthcoach",
) -> List[Dict[str, Any]]:
    checks = evaluation_report.get("checks", [])
    payload: List[Dict[str, Any]] = []

    payload.append(
        {
            "key": f"{prefix}.overall_score",
            "score": float(evaluation_report.get("overall_score", 0.0)),
            "comment": f"Overall pass={evaluation_report.get('passed', False)}",
        }
    )

    for check in checks:
        payload.append(
            {
                "key": f"{prefix}.{check.get('key', 'unknown')}",
                "score": float(check.get("score", 0.0)),
                "comment": (
                    f"passed={check.get('passed', False)} "
                    f"threshold={check.get('pass_threshold', 0.0)} "
                    f"weight={check.get('weight', 0.0)}"
                ),
            }
        )

    return payload


def submit_feedback_for_run(
    run_id: str,
    feedback_payload: Iterable[Dict[str, Any]],
    project_name: str | None = None,
) -> int:
    """Submit mapped feedback entries to a single LangSmith run id.

    Requires LANGSMITH_API_KEY to be configured in environment.
    """
    from langsmith import Client

    _ = project_name
    client = Client()
    submitted = 0
    for entry in feedback_payload:
        client.create_feedback(
            run_id=run_id,
            key=str(entry.get("key", "")),
            score=float(entry.get("score", 0.0)),
            comment=str(entry.get("comment", "")),
        )
        submitted += 1
    return submitted


def submit_feedback_batch(
    case_rows: Iterable[Dict[str, Any]],
    run_id_by_case: Dict[str, str],
    project_name: str | None = None,
) -> Dict[str, Any]:
    """Submit feedback payload for all rows that have a corresponding run_id."""
    submitted_cases = 0
    submitted_feedback = 0
    skipped_cases = 0

    for row in case_rows:
        case_id = str(row.get("case_id", ""))
        run_id = run_id_by_case.get(case_id)
        if not run_id:
            skipped_cases += 1
            continue
        feedback_payload = row.get("langsmith_feedback", [])
        submitted_feedback += submit_feedback_for_run(
            run_id=run_id,
            feedback_payload=feedback_payload,
            project_name=project_name,
        )
        submitted_cases += 1

    return {
        "submitted_cases": submitted_cases,
        "submitted_feedback": submitted_feedback,
        "skipped_cases": skipped_cases,
    }
