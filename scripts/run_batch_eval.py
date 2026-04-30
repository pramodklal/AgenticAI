from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from healthcoach.evaluation import evaluate_agentic_run
from healthcoach.evaluation.langsmith_feedback import (
    build_langsmith_feedback_payload,
    submit_feedback_batch,
)
from healthcoach.graph.state import create_initial_state
from healthcoach.graph.workflow import build_graph


PROMPTS: List[str] = [
    "I slept only 4 hours and feel exhausted. How should I train today?",
    "Give me a beginner 3-day workout split for fat loss.",
    "I need a high-protein vegetarian day meal plan.",
    "I feel anxious before sleep and wake up at 3 AM.",
    "I am 10 weeks pregnant and want safe exercises.",
    "My periods are irregular and workouts feel harder before day 1.",
    "Can you suggest a recovery day routine after leg day soreness?",
    "I want to gain muscle but I have low appetite.",
    "What can I do for stress eating in the evenings?",
    "I am postpartum and need safe activity progression.",
    "Please find an OB-GYN near my pincode 400001.",
    "Find a psychiatrist near zip code 10001.",
    "I have chest pain during workouts. What should I do?",
    "Create a balanced maintenance nutrition plan for office days.",
    "How should I adjust training during menopause symptoms?",
    "I am overwhelmed and not motivated to exercise at all.",
    "Can you combine sleep, workout, and nutrition advice for my week?",
    "I need a low-impact plan because my knees hurt after running.",
    "Find a dietitian near zip 08816.",
    "Give me one-week practical wellness plan with checkpoints.",
]


def _build_profile() -> Dict[str, Any]:
    return {
        "gender": "Other",
        "age": 30,
        "weight_kg": 70.0,
        "zip_code": "400001",
        "fitness_goal": "maintenance",
        "dietary_preference": "balanced",
    }


def run_batch(user_id: str, conversation_prefix: str) -> List[Dict[str, Any]]:
    graph = build_graph()
    rows: List[Dict[str, Any]] = []

    for idx, prompt in enumerate(PROMPTS, start=1):
        state = create_initial_state(
            conversation_id=f"{conversation_prefix}-{idx:03d}",
            user_id=user_id,
            user_message=prompt,
            profile=_build_profile(),
        )
        started = perf_counter()
        final_state = graph.invoke(state)
        elapsed_ms = int((perf_counter() - started) * 1000)

        answer = final_state.get("final_response", "")
        collected_facts = final_state.get("collected_facts", {})
        report = evaluate_agentic_run(prompt, answer, collected_facts, elapsed_ms)
        feedback_payload = build_langsmith_feedback_payload(report, prefix="myhealthcoach")

        rows.append(
            {
                "case_id": f"case-{idx:03d}",
                "prompt": prompt,
                "latency_ms": elapsed_ms,
                "overall_score": report["overall_score"],
                "passed": report["passed"],
                "expected_domains": report["expected_domains"],
                "observed_domains": report["observed_domains"],
                "answer": answer,
                "checks": report["checks"],
                "langsmith_feedback": feedback_payload,
            }
        )

    return rows


def _write_outputs(rows: List[Dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    report_json = output_dir / "batch_eval_report.json"
    report_csv = output_dir / "batch_eval_summary.csv"
    feedback_jsonl = output_dir / "langsmith_feedback_mapping.jsonl"

    with report_json.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    with report_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["case_id", "latency_ms", "overall_score", "passed", "prompt"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "case_id": row["case_id"],
                    "latency_ms": row["latency_ms"],
                    "overall_score": row["overall_score"],
                    "passed": row["passed"],
                    "prompt": row["prompt"],
                }
            )

    with feedback_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            payload = {
                "case_id": row["case_id"],
                "input": {"question": row["prompt"]},
                "feedback": row["langsmith_feedback"],
            }
            f.write(json.dumps(payload) + "\n")


def _print_summary(rows: List[Dict[str, Any]]) -> None:
    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    avg_score = round(sum(float(row["overall_score"]) for row in rows) / max(1, total), 3)
    avg_latency = round(sum(int(row["latency_ms"]) for row in rows) / max(1, total), 1)
    print(f"Total cases: {total}")
    print(f"Passed cases: {passed}/{total}")
    print(f"Average score: {avg_score}")
    print(f"Average latency (ms): {avg_latency}")


def _load_run_id_mapping(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Run id mapping file not found: {path}")

    mapping: Dict[str, str] = {}
    suffix = path.suffix.lower()

    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            # Accept {"case-001": "<run_id>", ...}
            for case_id, run_id in data.items():
                mapping[str(case_id)] = str(run_id)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("case_id") and item.get("run_id"):
                    mapping[str(item["case_id"])] = str(item["run_id"])
    elif suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                if isinstance(item, dict) and item.get("case_id") and item.get("run_id"):
                    mapping[str(item["case_id"])] = str(item["run_id"])
    elif suffix == ".csv":
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                case_id = row.get("case_id")
                run_id = row.get("run_id")
                if case_id and run_id:
                    mapping[str(case_id)] = str(run_id)
    else:
        raise ValueError("Run id mapping file must be .json, .jsonl, or .csv")

    return mapping


def _extract_run_id(item: Dict[str, Any]) -> str:
    candidate_keys = ("run_id", "runId", "id")
    for key in candidate_keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    run_obj = item.get("run")
    if isinstance(run_obj, dict):
        run_id = run_obj.get("id") or run_obj.get("run_id")
        if isinstance(run_id, str) and run_id.strip():
            return run_id.strip()

    return ""


def _extract_case_id(item: Dict[str, Any]) -> str:
    for key in ("case_id", "caseId", "example_id", "exampleId"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_prompt_text(item: Dict[str, Any]) -> str:
    for key in ("prompt", "question", "input", "inputs"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            nested = value.get("question") or value.get("prompt") or value.get("input")
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return ""


def _load_experiment_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Experiment export file not found: {path}")

    suffix = path.suffix.lower()
    rows: List[Dict[str, Any]] = []

    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            rows = [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            records = data.get("rows") or data.get("runs") or data.get("data")
            if isinstance(records, list):
                rows = [item for item in records if isinstance(item, dict)]
    elif suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                if isinstance(item, dict):
                    rows.append(item)
    elif suffix == ".csv":
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows.extend(dict(row) for row in reader)
    else:
        raise ValueError("Experiment export file must be .json, .jsonl, or .csv")

    return rows


def _derive_run_id_mapping_from_experiment_export(
    experiment_export_path: Path,
    case_rows: List[Dict[str, Any]],
) -> Dict[str, str]:
    experiment_rows = _load_experiment_rows(experiment_export_path)
    prompt_to_case: Dict[str, str] = {
        str(row.get("prompt", "")).strip(): str(row.get("case_id", "")).strip() for row in case_rows
    }

    mapping: Dict[str, str] = {}
    for item in experiment_rows:
        run_id = _extract_run_id(item)
        if not run_id:
            continue

        case_id = _extract_case_id(item)
        if case_id and case_id.startswith("case-"):
            mapping.setdefault(case_id, run_id)
            continue

        prompt = _extract_prompt_text(item)
        derived_case_id = prompt_to_case.get(prompt)
        if derived_case_id:
            mapping.setdefault(derived_case_id, run_id)

    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 20-prompt batch evaluation for MyHealthCoach.")
    parser.add_argument("--user-id", default="eval-user", help="User id used for all evaluation runs")
    parser.add_argument(
        "--conversation-prefix",
        default="batch-eval",
        help="Conversation id prefix used to generate per-case ids",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "artifacts" / "eval"),
        help="Directory where evaluation outputs are written",
    )
    parser.add_argument(
        "--submit-to-langsmith",
        action="store_true",
        help="Submit mapped feedback entries directly to LangSmith run IDs",
    )
    parser.add_argument(
        "--run-ids-file",
        default="",
        help="Path to case_id->run_id mapping (.json, .jsonl, or .csv)",
    )
    parser.add_argument(
        "--experiment-export-file",
        default="",
        help="Path to LangSmith experiment export (.json, .jsonl, or .csv) to auto-derive case_id->run_id",
    )
    parser.add_argument(
        "--langsmith-project",
        default="myhealthcoach",
        help="Project label used in submission summary",
    )
    args = parser.parse_args()

    rows = run_batch(user_id=args.user_id, conversation_prefix=args.conversation_prefix)
    output_dir = Path(args.output_dir)
    _write_outputs(rows, output_dir)
    _print_summary(rows)
    print(f"Wrote outputs to: {output_dir}")

    if args.submit_to_langsmith:
        run_id_by_case: Dict[str, str] = {}
        if args.run_ids_file:
            mapping_path = Path(args.run_ids_file)
            run_id_by_case = _load_run_id_mapping(mapping_path)
        elif args.experiment_export_file:
            export_path = Path(args.experiment_export_file)
            run_id_by_case = _derive_run_id_mapping_from_experiment_export(export_path, rows)
            derived_mapping_path = output_dir / "derived_run_ids.json"
            with derived_mapping_path.open("w", encoding="utf-8") as f:
                json.dump(run_id_by_case, f, indent=2)
            print(f"Derived run-id mapping written to: {derived_mapping_path}")
        else:
            raise ValueError(
                "Provide either --run-ids-file or --experiment-export-file when --submit-to-langsmith is set"
            )

        submission = submit_feedback_batch(
            case_rows=rows,
            run_id_by_case=run_id_by_case,
            project_name=args.langsmith_project,
        )
        print(
            "Submitted feedback to LangSmith: "
            f"cases={submission['submitted_cases']} "
            f"feedback={submission['submitted_feedback']} "
            f"skipped={submission['skipped_cases']}"
        )


if __name__ == "__main__":
    main()
