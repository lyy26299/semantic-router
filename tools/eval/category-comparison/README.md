# Category comparison baseline

This directory pins the existing Semantic Router category baseline for the
Jev/Kai comparison. The maintained configuration uses
`llm-semantic-router/Vela-1.0-Encoder-307M-Domain` at revision
`f6354f54adcf38770f635ad903be2b00577f6c11`. Its 14-class mapping is copied
from that immutable artifact into `category_mapping.json` so the pilot can be
reviewed and joined across all three arms.

The runner emits one JSON object per input and preserves the complete
`label_distribution.v1` probability distribution. It never renormalizes,
silently retries, or turns a failed model call into a prediction.

Create the local evaluation environment from the repository requirements:

```bash
uv venv --python 3.13 .venv-semantic-router-eval
uv pip install --python .venv-semantic-router-eval/bin/python \
  -r src/training/model_eval/requirements.txt
```

Validate the mapping without downloading model weights:

```bash
python3 tools/eval/category-comparison/run_baseline.py \
  --input tools/eval/category-comparison/fixtures/pilot.jsonl \
  --output /tmp/baseline.jsonl \
  --mapping-only
```

Run against a downloaded snapshot or let the runner fetch the pinned revision:

```bash
HF_XET_HIGH_PERFORMANCE=1 .venv-semantic-router-eval/bin/python \
  tools/eval/category-comparison/run_baseline.py \
  --input tools/eval/category-comparison/fixtures/pilot.jsonl \
  --output /tmp/baseline.jsonl \
  --device cpu \
  --warmup-runs 1
```

The six fixture rows are provisional pilot cases. Confirm their wording and
expected labels with the Jev and Kai owners before using them as comparison
results. The runner is evaluation-only; it does not change Router runtime
configuration or add a production backend.

## Recorded pilot result

The 2026-09-23 local CPU pilot produced 6 contract-valid distributions, 0
inference failures, and 4/6 correct predictions (66.7%). Wall-clock latency
was 15.10 ms at P50 and 18.41 ms at P95 for this six-case sequential run.
The environment was Python 3.13.15, PyTorch 2.14.0, Transformers 5.17.0,
and `huggingface-hub` 1.32.0 on a local macOS arm64 workstation. No paid
remote API was used; local compute cost was not measured.

The pilot includes one instruction-manipulation case, but it is English-only
and does not yet cover Chinese paraphrases, genuinely ambiguous or
out-of-scope requests, or controlled timeout, rate-limit, cancellation, and
invalid-response cases. Its wording and expected labels remain provisional.
The latency is local model inference latency, not an end-to-end remote-service
measurement. Use the same versioned fixture for the Jev arm before making an
adopt/defer/reject decision.
