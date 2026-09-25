#!/usr/bin/env python3
"""Run the Jev Choice classifier over JSONL cases with bounded concurrency."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_MAPPING = HERE / "category_mapping.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    p.add_argument("--model", default="jev-1.13.0")
    p.add_argument("--concurrency", type=int, default=16)
    p.add_argument("--max-cases", type=int, default=None)
    return p.parse_args()


def load_cases(path: Path, mapping: dict[str, int]) -> list[dict[str, Any]]:
    rows = []
    seen: set[str] = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        case_id, text, expected = str(row.get("case_id", "")), row.get("text"), row.get("expected_label")
        if not case_id or case_id in seen or not isinstance(text, str) or not text.strip():
            raise ValueError(f"{path}:{line_no}: invalid case")
        if expected is not None and expected not in mapping:
            raise ValueError(f"{path}:{line_no}: unknown expected label {expected!r}")
        rows.append({"case_id": case_id, "text": text, "expected_label": expected})
        seen.add(case_id)
    return rows


async def main_async(args: argparse.Namespace) -> None:
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY is required for the Jev run")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be positive")
    payload = json.loads(args.mapping.read_text(encoding="utf-8"))
    mapping = {str(k): int(v) for k, v in payload["category_to_idx"].items()}
    if sorted(mapping.values()) != list(range(len(mapping))):
        raise ValueError("mapping IDs must be contiguous")
    cases = load_cases(args.input, mapping)
    if args.max_cases is not None:
        cases = cases[: args.max_cases]

    from typesafe_sdk import AsyncTypeSafeClient, Choice, RetryPolicy

    criteria = {label: None for label, _ in sorted(mapping.items(), key=lambda item: item[1])}
    question = Choice(instructions="Which domain best describes the user's request?", criteria=criteria)
    retry = RetryPolicy(max_retries=0)
    sem = asyncio.Semaphore(args.concurrency)

    async with AsyncTypeSafeClient(model=args.model, retry=retry) as client:
        async def evaluate(case: dict[str, Any]) -> dict[str, Any]:
            result: dict[str, Any] = {
                "case_id": case["case_id"],
                "expected_label": case.get("expected_label"),
                "model_requested": args.model,
                "mapping_sha256": hashlib.sha256(args.mapping.read_bytes()).hexdigest(),
                "contract": "label_distribution.v1",
                "attempts": 1,
                "run_kind": "new diagnostic rerun; not original run",
                "error": None,
            }
            async with sem:
                started = time.perf_counter()
                response = None
                try:
                    response = await client.system_one(case["text"], {"domain": question})
                    result["sdk_response"] = response.model_dump(mode="json")
                    result["response_capture_kind"] = "SDK-parsed response, not HTTP wire bytes"
                    latency_ms = (time.perf_counter() - started) * 1000
                    answer = response.answers["domain"]
                    result["returned_probabilities"] = dict(answer.probabilities)
                    result["probability_sum"] = sum(float(v) for v in answer.probabilities.values())
                    result["sum_abs_error"] = abs(result["probability_sum"] - 1.0)
                    probabilities = {label: float(v) for label, v in answer.probabilities.items()}
                    if set(probabilities) != set(mapping):
                        raise ValueError("Jev returned a label set different from the mapping")
                    if not all(math.isfinite(v) and 0 <= v <= 1 for v in probabilities.values()):
                        raise ValueError("Jev returned an invalid probability")
                    if abs(sum(probabilities.values()) - 1.0) > 1e-3:
                        raise ValueError("Jev probabilities do not sum to 1")
                    result.update(
                        model=response.model,
                        prediction=answer.choice,
                        probabilities=probabilities,
                        confidence=float(answer.confidence),
                        usage=response.usage.model_dump() if response.usage else None,
                        contract_valid=True,
                        latency_wall_ms=latency_ms,
                    )
                    if case.get("expected_label") is not None:
                        result["correct"] = answer.choice == case["expected_label"]
                except Exception as exc:
                    result.update(prediction=None, probabilities=None, contract_valid=False)
                    result["error"] = f"{type(exc).__name__}: {exc}"
                    if response is not None:
                        result["response_capture_kind"] = "SDK-parsed response available before validation failure"
                finally:
                    result["latency_attempt_ms"] = (time.perf_counter() - started) * 1000
            return result

        tasks = [asyncio.create_task(evaluate(case)) for case in cases]
        completed = 0
        for task in asyncio.as_completed(tasks):
            await task
            completed += 1
            if completed % 100 == 0:
                print(f"completed {completed}/{len(cases)}", flush=True)
        results = await asyncio.gather(*tasks)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        for result in results:
            output.write(json.dumps(result, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
