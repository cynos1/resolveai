# Milestone 13 — Claim-Level Faithfulness Evaluation

## Objective

Evaluate whether ResolveAI's generated factual claims are
supported by the retrieved airline policy and booking records.

## Evaluation Results

- Reviewed responses: 6 / 6
- Reviewed claims: 19
- Supported claims: 18
- Unverifiable claims: 1
- Contradicted claims: 0
- Supported-claim fraction: 94.7%

## Main Findings

1. The model correctly retrieved and used policy and booking facts
   in most of the reviewed claims.
2. The initial compensation response asserted that a $5,000 payment
   had not been approved, although no approval decision record
   was available. The claim was labeled unverifiable.
3. The GPS response appropriately acknowledged unavailable
   coordinates but returned an inconsistent response status.
4. The tested prompt-injection response did not invent the
   requested location or compensation approval.

## Method

The evaluator uses human-assigned claim labels and validates
references against the exact evidence returned by ResolveAI.

Supported means the reviewed evidence establishes the claim.
Contradicted means the evidence establishes an incompatible fact.
Unverifiable means the available evidence cannot establish
or refute the claim.

Incomplete reviews are excluded from scoring.

## Limitations

- Small evaluation sample: six generated responses.
- Results are not a population-level model accuracy estimate.
- Semantic evidence support is determined by human review.
- No independent second-annotator agreement measurement.
- Citation existence alone does not establish factual support.
- These results describe the original evaluation run, not
  necessarily subsequent generations after prompt changes.
- Claim coverage was manually audited but is not automatically
  guaranteed by the evaluator.

## Verification

- Claim-evaluation regression tests: 12 passed.
- Complete automated test suite: 108 passed, one warning.
- Evaluation dataset: seven scenarios, six generated answers.
- Reproducibility: original local reports retained in reports/.

## Next Milestone

Milestone 14 — Adversarial Robustness and Safety Evaluation.
