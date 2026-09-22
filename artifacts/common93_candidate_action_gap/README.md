# Common93 Candidate-to-Action Gap

This artifact measures whether a callable/method that is present in the raw
disambiguation candidate set disappears before OrcaLoca creates a precise
inspection action. Gold entities are joined only after the run; they are never
read by the live agent.

The runtime diagnostic is enabled only with
`ORCAR_DISAMBIGUATION_DIAGNOSTIC_PATH` and records raw candidates, scorer
scores, threshold output, effective top-k, and generated actions. File/class
disambiguation is recorded separately and is excluded from the primary gap
rate.

The run uses the repository's existing `SWE-bench_common` loader, which is the
Lite/Verified intersection. The expected Common93 instance list is stored in
`common93_instance_ids.txt`.

The completed offline review is in:

- `detailed_gold_available_events.md`: all seven gold-available events and
  candidate/score/action details;
- `gap_case_audit.md`: source and parsed-patch verification of all three Gap
  cases;
- `downstream_trace_analysis.md`: later exact-action scan and the limits of
  the saved execution evidence;
- `updated_summary.md`: final RQ answers and descriptive score comparison.

The run artifacts do not persist the complete action history or every tool
execution payload. Accordingly, downstream analysis reports “no later exact
gold action observed in the saved diagnostic stream” rather than claiming
permanent loss or final repair failure.
