from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from app.core.config import get_settings
from app.database import clear_demo_data, init_db
from app.rag.azure_search import AzureSearchStore
from app.seed import DOCUMENTS, SAMPLE_DIR, write_sample_files
from app.services.ingestion_service import _azure_blob_store, _azure_search_store, ingest_path
from app.services.retrieval_service import evidence_is_sufficient, retrieve, retrieve_local

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = BACKEND_ROOT / "evaluation" / "retrieval_cases.json"


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


def evaluate(
    cases_path: Path,
    top_k: int = 5,
    backend: str = "local",
) -> dict[str, Any]:
    if backend not in {"local", "azure_search"}:
        raise ValueError("backend must be 'local' or 'azure_search'.")

    original_environment = {
        name: os.environ.get(name)
        for name in ("RETRIEVAL_BACKEND", "AI_PROVIDER")
    }
    os.environ["RETRIEVAL_BACKEND"] = backend
    if backend == "azure_search":
        os.environ["AI_PROVIDER"] = "azure"
    get_settings.cache_clear()
    _azure_search_store.cache_clear()
    _azure_blob_store.cache_clear()

    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    try:
        if backend == "azure_search":
            benchmark_store = AzureSearchStore(settings=get_settings())
            benchmark_store.ensure_index()
            benchmark_store.clear_documents_for_evaluation()
        _seed_evaluation_corpus()

        positive_recalls: list[float] = []
        reciprocal_ranks: list[float] = []
        negative_outcomes: list[bool] = []
        retrieval_latencies_ms: list[float] = []
        case_results: list[dict[str, Any]] = []

        for case in cases:
            started = time.perf_counter()
            if backend == "azure_search":
                results = retrieve(case["question"], limit=top_k, user_role="plant_manager")
            else:
                results = retrieve_local(case["question"], limit=top_k, user_role="plant_manager")
            elapsed_ms = (time.perf_counter() - started) * 1000
            retrieval_latencies_ms.append(elapsed_ms)
            retrieved_files = [item["filename"] for item in results]
            relevant_files = set(case["relevant_files"])

            if relevant_files:
                retrieved_relevant = relevant_files & set(retrieved_files)
                recall = len(retrieved_relevant) / len(relevant_files)
                rank = next(
                    (index for index, filename in enumerate(retrieved_files, start=1) if filename in relevant_files),
                    None,
                )
                reciprocal_rank = 1.0 / rank if rank else 0.0
                positive_recalls.append(recall)
                reciprocal_ranks.append(reciprocal_rank)
                passed = bool(retrieved_relevant)
            else:
                recall = None
                reciprocal_rank = None
                passed = not evidence_is_sufficient(results)
                negative_outcomes.append(passed)

            case_results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "relevant_files": sorted(relevant_files),
                    "retrieved_files": retrieved_files,
                    "recall_at_k": round(recall, 4) if recall is not None else None,
                    "reciprocal_rank": round(reciprocal_rank, 4) if reciprocal_rank is not None else None,
                    "latency_ms": round(elapsed_ms, 2),
                    "passed": passed,
                }
            )

        p50 = _percentile(retrieval_latencies_ms, 0.50)
        p95 = _percentile(retrieval_latencies_ms, 0.95)
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "backend": backend,
            "top_k": top_k,
            "case_count": len(cases),
            "positive_case_count": len(positive_recalls),
            "negative_case_count": len(negative_outcomes),
            "mean_recall_at_k": round(mean(positive_recalls), 4) if positive_recalls else None,
            "mean_reciprocal_rank": round(mean(reciprocal_ranks), 4) if reciprocal_ranks else None,
            "negative_abstention_accuracy": round(mean(negative_outcomes), 4) if negative_outcomes else None,
            "retrieval_latency_ms_p50": round(p50, 2) if p50 is not None else None,
            "retrieval_latency_ms_p95": round(p95, 2) if p95 is not None else None,
            "passed_cases": sum(1 for item in case_results if item["passed"]),
            "cases": case_results,
        }
    finally:
        for name, value in original_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        get_settings.cache_clear()
        _azure_search_store.cache_clear()
        _azure_blob_store.cache_clear()


def _seed_evaluation_corpus() -> None:
    """Load only the labelled corpus so benchmark results do not depend on extra demo files."""
    init_db()
    clear_demo_data()
    write_sample_files()
    for filename in sorted(DOCUMENTS):
        ingest_path(SAMPLE_DIR / filename)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate ForgeMind AI retrieval on a labelled corpus.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--backend", choices=["local", "azure_search"], default="local")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = evaluate(args.cases, top_k=args.top_k, backend=args.backend)
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
