# Downstream trace analysis after the three Gap events

## What is observable

The preserved artifacts contain:

- the disambiguation event emitted inside `_disambiguation_ranking`, including
  `raw_candidates`, scores, threshold survivors, and `selected_actions`;
- one final `searcher_<instance>.json` per completed instance;
- some final `trace_analyzer_<instance>.json` files.

They do **not** contain a persisted full `action_history`, ordered tool-call
trace, or per-action execution result. The `selected_actions` field is written
when precise actions are constructed, before the later queue/tool execution
path. Therefore it is valid for candidate-to-action analysis, but it is not
by itself an execution receipt.

## Later exact-gold action scan

The diagnostic event stream was scanned in event order for an exact later
action matching each Gap gold entity, including file path and class.

| Gap instance | Gap event | later diagnostic events | later exact gold action observed? | classification from available trace |
|---|---:|---|---|---|
| `matplotlib__matplotlib-23299` | 1 | none | No | A: no later exact action observed |
| `sympy__sympy-13031` | 1 | class `MutableDenseMatrix`; ranked `classof` | No | A: no later exact action observed |
| `sympy__sympy-13647` | 2 | none after event 2 | No | A: no later exact action observed |

Observed counts:

- later exact-gold action observed: **0 / 3**;
- no later exact-gold action observed in the saved diagnostic stream: **3 / 3**;
- observed B cases (later recovered through another exact action): **0 / 3**.

This is not a claim that the gold was permanently lost. Non-disambiguation
tool calls and the complete action history were not persisted in this
experiment, so the stronger “never searched again” statement is unobservable
from the saved artifacts. The defensible statement is: **no later exact gold
action is present in the available diagnostic event stream**.

## Final localization outputs

Final `searcher_*.json` outputs were checked separately from the action trace:

| instance | exact gold in final `bug_locations`? | relevant final/trace evidence |
|---|---|---|
| `matplotlib__matplotlib-23299` | Yes | final searcher lists `lib/matplotlib/__init__.py::rc_context`; trace analyzer also lists `rc_context` as suspicious code |
| `sympy__sympy-13031` | Yes | final searcher lists `sympy/matrices/sparse.py::MutableSparseMatrix::row_join`; no trace-analyzer JSON was saved for this instance |
| `sympy__sympy-13647` | No, not as the exact nested `entry` entity | final searcher lists parent `MatrixShaping::_eval_col_insert`; trace analyzer lists both `_eval_col_insert` and `entry` as suspicious/traced code |

These final localization fields show what the final search response named;
they do not prove that the corresponding exact precise action was executed.
In particular, a final LLM conclusion can name a location even when the
instrumented disambiguation event did not generate that precise action.

## Action-to-Execution check

Four non-Gap gold-available events generated an exact gold action:

- `scikit-learn__scikit-learn-14894`, `BaseLibSVM::_sparse_fit`;
- `sympy__sympy-12419`, `Identity::_entry`;
- `sympy__sympy-16792`, `CodeGen::routine`;
- `sympy__sympy-24066`, `UnitSystem::_collect_factor_and_dimension`.

The saved artifacts do not record an ordered tool execution event or returned
tool payload for these actions. Consequently an Action-to-Execution Gap rate
cannot be computed responsibly from this run. The current evidence supports
only:

```text
selected exact gold action generated: 4 events
direct execution confirmation: not available
```

No repair/resolved result was run or analyzed here. In particular, none of
the results above should be interpreted as a claim about final repair success
or failure.
