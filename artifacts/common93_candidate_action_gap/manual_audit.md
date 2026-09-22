# Manual audit of the three Candidate-to-Action Gap cases

This audit cross-checks the automatic join against the parsed official gold
patch metadata and the target repository source at each instance's recorded
base commit. It does not modify any target repository or rerun an instance.

## Audit method

For each case I checked:

1. `gold_entities.json` and `golden_stats.csv` for the patch-derived file,
   class, function/method, diff-node chain, and base commit;
2. the source file at that exact base commit in the cached target repository;
3. the raw candidate, scorer score/rank, threshold decision, and selected
   action in `disambiguation_events.jsonl`;
4. final `searcher_*.json` and available `trace_analyzer_*.json` outputs,
   while keeping their final localization separate from action execution.

## Case 1: `matplotlib__matplotlib-23299`

- Query: `search_callable(query_name=rc_context)`
- Gold: `lib/matplotlib/__init__.py::rc_context`
- Gold patch evidence: `gold_entities.json` records a function node
  `rc_context`, lines 1058--1098, with patch lines 1060 and 1090.
- Base commit: `3eadeacc06c9f2ddcdac6ae39819faa9fbee9e39`.
- Source verification: at that commit, `rc_context` is the function beginning
  at line 1058; its `finally` block contains
  `dict.update(rcParams, orig)` at line 1098. The file and function identity
  exactly match the parsed gold entity.
- Raw candidates and scores:
  - `lib/matplotlib/__init__.py::rc_context`, rank 1, score 72 (gold);
  - `lib/matplotlib/pyplot.py::rc_context`, rank 2, score 20 (same name,
    different file; not gold).
- Threshold: 75. Since 72 is below 75, the gold does not enter
  `post_threshold_candidates`; no precise action is generated.
- Selected actions: none.
- Manual result: **confirmed threshold Gap**. This is not a same-name false
  match: the file path agrees with the patch-derived gold, while the other
  `rc_context` candidate is in a different file.
- Later evidence: no later disambiguation event or exact `rc_context` action
  is present in the diagnostic event stream. The final search output names
  `rc_context`, but that is a final localization output, not an execution
  record.

## Case 2: `sympy__sympy-13031`

- Query: `search_callable(query_name=row_join)`
- Gold for this event: `sympy/matrices/sparse.py::MutableSparseMatrix::row_join`.
  The same patch also contains `MutableSparseMatrix::col_join`, but the event
  query is specifically `row_join`.
- Gold patch evidence: `gold_entities.json` records
  `MutableSparseMatrix` lines 847--1299 and `row_join` lines 1159--1213;
  the parsed patch location is lines 1194--1195.
- Base commit: `2dfa7457f20ee187fbb09b5b6a1631da4458388`.
- Source verification: at that commit, `sparse.py` contains class
  `MutableSparseMatrix`, method `row_join`, and the corresponding
  `if not self:` at line 1194. The path, class, and method all agree with the
  parsed gold entity.
- Raw candidates and scores:
  - `sympy/holonomic/linearsolver.py::NewMatrix::row_join`, rank 1, score 85
    (non-gold and selected);
  - `sympy/matrices/sparse.py::MutableSparseMatrix::row_join`, rank 2, score
    75 (gold);
  - `sympy/matrices/common.py::MatrixShaping::row_join`, rank 3, score 70
    (non-gold).
- Threshold: 75. The gold has exactly score 75 and is excluded by the
  observed strict `score > 75` behavior.
- Selected action: only `NewMatrix::row_join` in
  `sympy/holonomic/linearsolver.py`; this is not the gold because both file
  and class differ.
- Manual result: **confirmed threshold Gap**, with no path/class ambiguity.
- Later evidence: subsequent diagnostic events are a class disambiguation for
  `MutableDenseMatrix` and a ranked `classof` event; neither is an exact
  `MutableSparseMatrix::row_join` action. The final search output does list
  the gold sparse `row_join`, but no execution record is available.

## Case 3: `sympy__sympy-13647`

- Gap query: `search_callable(query_name=entry)`, event 2.
- Gold: `sympy/matrices/common.py::MatrixShaping::entry` under the more
  precise parsed node chain
  `MatrixShaping -> _eval_col_insert -> entry`.
- Gold patch evidence: `gold_entities.json` records the nested `entry`
  function at lines 84--89, with the patch at line 89.
- Base commit: `67e3c956083d0128a621f65ee86a7dacd4f9f19f`.
- Source verification: at that commit, `common.py` contains
  `MatrixShaping._eval_col_insert` at lines 81--92 and its nested `entry` at
  lines 84--89. The exact source line is
  `return self[i, j - pos - other.cols]` at line 89, matching the patch-derived
  node chain.
- Raw candidate identities contain six repeated
  `common.py::MatrixShaping::entry` entries, plus same-name entries in other
  classes/files. The repeated canonical identity is a limitation of the
  existing file/class/function representation; the parsed patch node chain
  resolves the intended nested helper and prevents treating a different class
  as gold.
- Gold candidate scores/ranks: 75 at ranks 1, 2, 3, and 4; 70 at rank 6;
  60 at rank 7. These are all below the strict retention condition, including
  the four scores equal to the threshold.
- Non-gold comparison: `MatrixOperations::entry` ties at 75 at rank 5; it
  does not outrank the best gold occurrence. Other non-gold entries score 50
  or lower.
- Threshold: 75. No post-threshold candidates and no selected actions.
- Manual result: **confirmed threshold Gap**. The gold identity is supported
  by the official patch node chain and exact source location; it is not being
  matched solely by a same-name method in another class.
- Later evidence: no later diagnostic event follows event 2. The preceding
  event selected `MatrixShaping::_eval_col_insert`, but the exact nested
  `entry` gold action was not generated. The final search output reports the
  parent `_eval_col_insert`, while the trace analyzer separately reports
  `entry`; neither is a persisted tool-execution record for the gold helper.

## Audit conclusion

All three automatic Gap cases survive the manual source and patch check:

| instance | gold identity verified? | exact gold score | gold rank(s) | drop reason |
|---|---|---:|---|---|
| `matplotlib__matplotlib-23299` | Yes | 72 | 1 | threshold |
| `sympy__sympy-13031` | Yes | 75 | 2 | threshold, strict `>` |
| `sympy__sympy-13647` | Yes, with nested-helper caveat | 75/70/60 | 1,2,3,4,6,7 | threshold, strict `>` |

No case requires a top-k or action-construction explanation. The three cases
are three independent instances, so the pilot criterion of at least three
independent Gap cases is met. This remains a candidate-to-action finding and
does not establish downstream repair failure.
