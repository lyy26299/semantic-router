# Jev diagnostic rerun — 2026-09-25

This directory contains the review metadata and a small failure sample for the local diagnostic rerun requested for issue #3970. The full JSONL output is distributed separately as a compressed artifact.

- Input: same 12,032-row MMLU-Pro fixture as the original comparison.
- Model: `jev-1.13.0`.
- Candidates and wording: same 14-label mapping and Choice instruction as the original run.
- Concurrency: 16.
- SDK retries: disabled.
- Full output artifact: `jev-mmlu-pro-capture-rerun-20260925.tar.gz`.
- Full output SHA-256: see `summary.json` and `artifact-sha256.txt`.
- GitHub artifact: https://github.com/lyy26299/semantic-router/raw/codex/jev-mmlu-pro-rerun/artifacts/jev-mmlu-pro-review-20260925.tar.gz
- This branch includes `jev-failures-sample.jsonl` (20 public failure records); the full failure review is in the external artifact.

The rerun retained the SDK-parsed response before contract validation. For every non-timeout response it stores `sdk_response.answers.domain.probabilities`, `returned_probabilities`, `probability_sum`, `sum_abs_error`, choice, confidence and usage. This is the complete response object available after SDK parsing; HTTP wire bytes are not captured.

## Rerun result

- 12,032 requests completed.
- 11,911 contract-valid rows.
- 121 probability-sum failures.
- 0 timeouts in this rerun.
- Every one of the 121 failures returned all 14 configured labels and summed to `0.99` (absolute error `0.01`), so the failure is directly inspectable rather than a missing vector.
- Valid-row accuracy: see `summary.json`.
- All-request correct rate: see `summary.json`.
- Coverage: see `summary.json`.

The external artifact contains `jev-failures-with-inputs-and-responses.jsonl`, which joins each public input with the complete SDK-parsed response and validation evidence. This branch includes a 20-record sample for review. See `failure-analysis.md` for the detailed failure analysis, including observed facts, category distribution, and the limits of causal interpretation.

The original 2 timeout failures were not reproduced in this run. They remain in the original output and should be reported separately; this rerun's failure count must not be merged with the original count without preserving run identity.

No credentials are present in this directory.
