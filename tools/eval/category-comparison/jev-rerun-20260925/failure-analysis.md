# Jev failure analysis

This analysis covers the 121 failures in the 2026-09-25 diagnostic rerun.

## Observed failure

Every failed response:

- returned all 14 configured labels;
- contained finite values in `[0, 1]`;
- had a probability sum of `0.99` (floating-point representation: `0.9900000000000001`);
- therefore exceeded the `label_distribution.v1` sum tolerance of `1e-3` by approximately `0.01`;
- still contained a selected label, confidence, usage and a complete SDK-parsed response object.

The runner retained these responses as contract-invalid. It did not renormalize them, fold `confidence` into the distribution, or count them as valid predictions.

## What this does and does not show

The data establishes a deterministic contract incompatibility in this run. It does not by itself establish whether the missing `0.01` is caused by model-side rounding, response serialization, SDK conversion, or another service-layer behavior. The wire-level HTTP body was not captured, so that cause remains unverified.

`confidence` is a separate Jev statistic. It was preserved for inspection and was not treated as a label probability or correctness guarantee.

## Where the failures occurred

By expected label, the largest groups were `other` (33), `business` (17), `psychology` (15), `math` (10), `chemistry` (9), `health` (9), and `philosophy` (9). This is descriptive only; it is not a per-class failure rate because the denominator is not the full class count in this file.

The selected labels among failed responses were most often `math` (19), `business` (15), `other` (15), `philosophy` (13), and `biology` (12). A failed contract response may still have selected the expected label, but it remains unusable under the contract until the distribution is valid.

The captured confidence values ranged from `0.26` to `0.93`. This spread reinforces that confidence must not be used to silently repair the distribution or to infer correctness.

## Comparison with the original run

The original run reported 120 probability-sum failures and 2 timeouts. The diagnostic rerun reported 121 probability-sum failures and 0 timeouts. The runs are kept separate; the counts must not be merged as if they were one execution.

The practical next diagnostic is a response capture at the HTTP transport boundary, if permitted, to determine whether the `0.99` sum is already present on the wire or introduced during SDK parsing. Regardless of root cause, the current response cannot satisfy `label_distribution.v1` without an explicit contract or provider-side fix.
