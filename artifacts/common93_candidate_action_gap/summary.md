# OrcaLoca Common93 Candidate-to-Action Gap: updated summary

## Experiment status

- Dataset: SWE-bench Common (`SWE-bench_Lite ∩ SWE-bench_Verified`)
- Instances: **93 / 93 completed**
- Ranked callable/method disambiguation events: **22**
- Gold-available ranked events: **7**
- Gap events: **3**
- Candidate-to-Action Gap Rate: **3 / 7 = 42.86%**
- All disambiguation events: **27**
- Unranked class events: **5**
- Unranked file events: **0**

Run configuration was unchanged during analysis: model `ep-64pmfvfo`,
temperature 0.1, `score_threshold=75`, `top_k_disambiguation=3`, original
prompt/search/scoring logic, and the recorded decomposition/priority settings
in `run_config.json`. No API key or token is stored here.

## RQ1

**Does OrcaLoca drop already-retrieved gold entities during disambiguation
candidate-to-action conversion?**

**Answer: Yes, in this sample.** Seven ranked disambiguation events contained a
gold entity in `raw_candidates`; three of those events generated no matching
gold precise action. The measured Candidate-to-Action Gap Rate is **42.86%**.

The three instances are:

1. `matplotlib__matplotlib-23299`: query `rc_context`; gold score **72**;
   threshold 75; no higher-scored candidate; no later exact action observed.
2. `sympy__sympy-13031`: query `row_join`; gold score **75**, rank **2**;
   `NewMatrix::row_join` scored **85** and was selected instead; no later
   exact `MutableSparseMatrix::row_join` action observed.
3. `sympy__sympy-13647`: query `entry`; gold occurrences scored **75** at
   ranks 1--4, **70** at rank 6, and **60** at rank 7; no action was generated;
   no later exact nested `MatrixShaping::_eval_col_insert::entry` action was
   observed.

## RQ2

**At which step are these Gaps produced?**

All three are produced by the scorer threshold stage:

| drop stage | count |
|---|---:|
| threshold | 3 |
| top-k | 0 |
| action generation | 0 |

The observed implementation uses a strict `score > 75` retention condition,
so the two gold scores equal to 75 are dropped as well. The stage counts are
Gap-cause counts, not configuration values: the run used
`score_threshold=75` and `top_k_disambiguation=3`. No Gap case requires a
top-k or action-construction explanation.

## RQ3

**After threshold filtering, is the gold permanently lost?**

The saved diagnostic stream shows:

- later exact gold action observed: **0 / 3**;
- Gap cases with no later exact gold action in the available stream: **3 / 3**;
- observed later-recovered cases: **0 / 3**.

This experiment did not persist the complete action history or every tool
execution. Therefore “never searched again” cannot be proven for arbitrary
non-disambiguation tool calls. The precise conclusion is that no later exact
gold action appears in the saved disambiguation/action diagnostics.

Final localization outputs are separate: the final searcher output contains
the exact gold for the matplotlib and SymPy-13031 cases, while the SymPy-13647
final output names the parent `_eval_col_insert` rather than the nested `entry`.
Those outputs are not execution receipts.

## RQ4

**Does this prove final repair failure?**

**No.** The experiment proves only candidate-to-action information loss in
these events. It did not run complete repair/resolved evaluation, and it does
not establish a causal effect on downstream repair success.

## Score pattern across the seven gold-available events

Best gold scorer scores by event:

- Gap events: **72, 75, 75**; descriptive mean **74.0**.
- Non-Gap events: **95, 95, 90, 95**; descriptive mean **93.75**.

All Gap gold scores are at or below the threshold, while all four non-Gap gold
scores are above it. In the SymPy-13031 case a non-gold `NewMatrix::row_join`
scored 85, clearly above the gold 75. In the other two Gap cases, no non-gold
candidate scored above the best gold occurrence (the SymPy-13647
`MatrixOperations::entry` candidate tied at 75). This is a small descriptive
sample, not a scorer-quality benchmark or significance test.

## Manual validation

All three Gap entities were checked against the official patch-derived gold
metadata and source at the recorded base commit:

- Matplotlib: exact `lib/matplotlib/__init__.py::rc_context` function;
- SymPy-13031: exact `sympy/matrices/sparse.py::MutableSparseMatrix::row_join`
  method;
- SymPy-13647: exact nested helper
  `sympy/matrices/common.py::MatrixShaping::_eval_col_insert::entry`.

The third case has a known canonicalization caveat: the existing entity string
omits the parent nested function, so repeated `MatrixShaping::entry` candidates
are collapsed at the canonical identity level. The parsed patch node chain and
source line check disambiguate the intended gold location; no different-class
same-name entity was used as the gold.

## Pilot judgment

There are **three independent Gap instances**, so the result meets the pilot
criterion for continuing to investigate downstream impact. This is a research
priority signal only, not a statistical significance claim.

## Reproducibility artifacts

- `common93_instance_ids.txt`
- `run_config.json`
- `disambiguation_events.jsonl`
- `gold_entities.json`
- `gold_available_events.jsonl`
- `gap_events.jsonl`
- `summary.json`
- `detailed_gold_available_events.md`
- `gap_case_audit.md`
- `downstream_trace_analysis.md`

No new experiment run was performed for this update.
