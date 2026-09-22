# Detailed gold-available event review

This is an offline review of the seven ranked disambiguation events for which
the canonical gold entity was present in `raw_candidates`. No model/API call
was made and no OrcaLoca selection behavior was changed.

## Scope and interpretation

- Dataset: SWE-bench Common, 93 instances.
- Source: `disambiguation_events.jsonl`, `gold_entities.json`, and the
  per-instance `searcher_*.json` / `trace_analyzer_*.json` artifacts.
- Config observed in the run: `score_threshold=75`,
  `top_k_disambiguation=3`.
- The implementation retains candidates only when `score > 75`; therefore a
  score of exactly 75 is below the effective threshold for this run.
- “Gold selected” means an exact canonical entity match in
  `selected_actions`, including file path and class when present.

## Event-level summary

| instance | event | query | gold entity | gold score/rank | selected exact gold action? |
|---|---:|---|---|---|---|
| `matplotlib__matplotlib-23299` | 1 | `search_callable(query_name=rc_context)` | `lib/matplotlib/__init__.py::rc_context` | 72 / 1 | No |
| `scikit-learn__scikit-learn-14894` | 1 | `search_callable(query_name=_sparse_fit)` | `sklearn/svm/base.py::BaseLibSVM::_sparse_fit` | 95 / 1 | Yes |
| `sympy__sympy-12419` | 1 | `search_callable(query_name=_entry)` | `sympy/matrices/expressions/matexpr.py::Identity::_entry` | 95 / 1 | Yes |
| `sympy__sympy-13031` | 1 | `search_callable(query_name=row_join)` | `sympy/matrices/sparse.py::MutableSparseMatrix::row_join` | 75 / 2 | No |
| `sympy__sympy-13647` | 2 | `search_callable(query_name=entry)` | `sympy/matrices/common.py::MatrixShaping::entry` | 75 / 1,2,3,4; also 70 / 6 and 60 / 7 | No |
| `sympy__sympy-16792` | 1 | `search_callable(query_name=routine)` | `sympy/utilities/codegen.py::CodeGen::routine` | 90 / 1 | Yes |
| `sympy__sympy-24066` | 1 | `search_callable(query_name=_collect_factor_and_dimension)` | `sympy/physics/units/unitsystem.py::UnitSystem::_collect_factor_and_dimension` | 95 / 1 | Yes |

## 1. `matplotlib__matplotlib-23299`, event 1

Query: `search_callable`, `query_name=rc_context`  
Gold: `lib/matplotlib/__init__.py::rc_context`  
Threshold: 75; configured top-k: 3; effective top-k: 1  
Post-threshold candidates: none  
Selected actions: none

Raw candidates, with scorer ranking:

| rank | candidate | score | gold? | retained? |
|---:|---|---:|---|---|
| 1 | `lib/matplotlib/__init__.py::rc_context` | 72 | Yes | No, threshold |
| 2 | `lib/matplotlib/pyplot.py::rc_context` | 20 | No | No, threshold |

The gold entity is rank 1, but 72 is below 75. There is no higher-scored
non-gold candidate; the event is a pure threshold drop.

## 2. `scikit-learn__scikit-learn-14894`, event 1

Query: `search_callable`, `query_name=_sparse_fit`  
Gold: `sklearn/svm/base.py::BaseLibSVM::_sparse_fit`  
Threshold: 75; configured top-k: 3; effective top-k: 1  
Post-threshold candidates: the gold candidate only  
Selected action: `search_method_in_class(BaseLibSVM, _sparse_fit, sklearn/svm/base.py)`

| rank | candidate | score | gold? | retained? |
|---:|---|---:|---|---|
| 1 | `sklearn/svm/base.py::BaseLibSVM::_sparse_fit` | 95 | Yes | Yes |
| 2 | `sklearn/impute/_base.py::SimpleImputer::_sparse_fit` | 2 | No | No, top-k after threshold |
| 3 | `sklearn/preprocessing/data.py::QuantileTransformer::_sparse_fit` | 2 | No | No, top-k after threshold |

The gold passes the threshold and is selected. The two non-gold candidates
are much lower-scored.

## 3. `sympy__sympy-12419`, event 1

Query: `search_callable`, `query_name=_entry`  
Gold: `sympy/matrices/expressions/matexpr.py::Identity::_entry`  
Threshold: 75; configured top-k: 3; effective top-k: 1  
Post-threshold candidates: `Identity::_entry` and `DiagonalOf::_entry`  
Selected action: `search_method_in_class(Identity, _entry, sympy/matrices/expressions/matexpr.py)`

| rank | candidate | score | gold? | retained? |
|---:|---|---:|---|---|
| 1 | `sympy/matrices/expressions/matexpr.py::Identity::_entry` | 95 | Yes | Yes |
| 2 | `sympy/matrices/expressions/diagonal.py::DiagonalOf::_entry` | 85 | No | Yes, not selected by effective top-k |
| 3 | `sympy/matrices/expressions/matexpr.py::MatrixSymbol::_entry` | 50 | No | No, threshold |
| 4 | `sympy/matrices/expressions/matmul.py::MatMul::_entry` | 30 | No | No, threshold |
| 5 | `sympy/matrices/immutable.py::ImmutableDenseMatrix::_entry` | 25 | No | No, threshold |
| 6 | `sympy/matrices/expressions/matexpr.py::ZeroMatrix::_entry` | 25 | No | No, threshold |
| 7 | `sympy/matrices/expressions/hadamard.py::HadamardProduct::_entry` | 25 | No | No, threshold |
| 8 | `sympy/matrices/expressions/diagonal.py::DiagonalMatrix::_entry` | 25 | No | No, threshold |
| 9 | `sympy/matrices/expressions/funcmatrix.py::FunctionMatrix::_entry` | 25 | No | No, threshold |
| 10 | `sympy/matrices/expressions/transpose.py::Transpose::_entry` | 15 | No | No, threshold |
| 11 | `sympy/matrices/expressions/matexpr.py::MatrixExpr::_entry` | 15 | No | No, threshold |
| 12 | `sympy/matrices/expressions/adjoint.py::Adjoint::_entry` | 15 | No | No, threshold |
| 13 | `sympy/matrices/expressions/matpow.py::MatPow::_entry` | 5 | No | No, threshold |
| 14 | `sympy/matrices/expressions/slice.py::MatrixSlice::_entry` | 5 | No | No, threshold |
| 15 | `sympy/matrices/expressions/matadd.py::MatAdd::_entry` | 5 | No | No, threshold |
| 16 | `sympy/matrices/expressions/blockmatrix.py::BlockMatrix::_entry` | 5 | No | No, threshold |
| 17 | `sympy/matrices/expressions/fourier.py::DFT::_entry` | 2 | No | No, threshold |
| 18 | `sympy/matrices/expressions/fourier.py::IDFT::_entry` | 2 | No | No, threshold |

The gold is rank 1 and has a large score margin. This is a non-Gap control
event; the configured top-k is not itself the reason that the gold was
selected.

## 4. `sympy__sympy-13031`, event 1

Query: `search_callable`, `query_name=row_join`  
Gold: `sympy/matrices/sparse.py::MutableSparseMatrix::row_join`  
Threshold: 75; configured top-k: 3; effective top-k: 1  
Post-threshold candidates: `sympy/holonomic/linearsolver.py::NewMatrix::row_join`  
Selected action: `search_method_in_class(NewMatrix, row_join, sympy/holonomic/linearsolver.py)`

| rank | candidate | score | gold? | retained? |
|---:|---|---:|---|---|
| 1 | `sympy/holonomic/linearsolver.py::NewMatrix::row_join` | 85 | No | Yes, selected |
| 2 | `sympy/matrices/sparse.py::MutableSparseMatrix::row_join` | 75 | Yes | No, threshold |
| 3 | `sympy/matrices/common.py::MatrixShaping::row_join` | 70 | No | No, threshold |

The selected `NewMatrix::row_join` is not the gold: both the file and class
differ. The gold is exactly at 75 and is excluded by the strict threshold.

## 5. `sympy__sympy-13647`, event 2

Query: `search_callable`, `query_name=entry`  
Gold: `sympy/matrices/common.py::MatrixShaping::entry`  
Threshold: 75; configured top-k: 3; effective top-k: 1  
Post-threshold candidates: none  
Selected actions: none

Raw candidate identities, source order with duplicates preserved, are six
`MatrixShaping::entry`, six `MatrixSpecial::entry`, two
`MatrixOperations::entry`, two `MatrixArithmetic::entry`, six
`MatrixReductions::entry`, and two `MatrixDeterminant::entry` candidates.

Scored candidates:

| ranks | candidate | score | gold? | retained? |
|---|---|---:|---|---|
| 1, 2, 3, 4 | `sympy/matrices/common.py::MatrixShaping::entry` | 75 | Yes | No, threshold |
| 5 | `sympy/matrices/common.py::MatrixOperations::entry` | 75 | No | No, threshold |
| 6 | `sympy/matrices/common.py::MatrixShaping::entry` | 70 | Yes | No, threshold |
| 7 | `sympy/matrices/common.py::MatrixShaping::entry` | 60 | Yes | No, threshold |
| 8 | `sympy/matrices/common.py::MatrixOperations::entry` | 50 | No | No, threshold |
| 9, 10, 11, 12, 13, 14 | `sympy/matrices/common.py::MatrixSpecial::entry` | 25 | No | No, threshold |
| 15, 16 | `sympy/matrices/common.py::MatrixArithmetic::entry` | 2 | No | No, threshold |
| 17, 18, 19, 20, 21, 22 | `sympy/matrices/matrices.py::MatrixReductions::entry` | 2 | No | No, threshold |
| 23, 24 | `sympy/matrices/matrices.py::MatrixDeterminant::entry` | 0 | No | No, threshold |

The canonical gold identity occurs at ranks 1, 2, 3, 4, 6, and 7, with
scores 75, 75, 75, 75, 70, and 60. The best gold score is exactly the
threshold and is therefore dropped; the 70 and 60 occurrences are also
dropped. There is no higher-scored non-gold candidate: the rank-5
`MatrixOperations::entry` candidate ties at 75.

The duplicate canonical identities are a representation caveat. The parsed
gold patch identifies the target more precisely as the nested helper
`MatrixShaping::_eval_col_insert::entry`; the canonical string used by the
existing OrcaLoca dataset/parser does not include that parent helper.

## 6. `sympy__sympy-16792`, event 1

Query: `search_callable`, `query_name=routine`  
Gold: `sympy/utilities/codegen.py::CodeGen::routine`  
Threshold: 75; configured top-k: 3; effective top-k: 1  
Post-threshold candidates: `CodeGen::routine`  
Selected action: `search_method_in_class(CodeGen, routine, sympy/utilities/codegen.py)`

| rank | candidate | score | gold? | retained? |
|---:|---|---:|---|---|
| 1 | `sympy/utilities/codegen.py::CodeGen::routine` | 90 | Yes | Yes |
| 2 | `sympy/utilities/codegen.py::OctaveCodeGen::routine` | 50 | No | No, threshold |
| 3 | `sympy/utilities/codegen.py::RustCodeGen::routine` | 45 | No | No, threshold |
| 4 | `sympy/utilities/codegen.py::JuliaCodeGen::routine` | 40 | No | No, threshold |

The gold is rank 1 and selected with a 40-point margin over the next
candidate.

## 7. `sympy__sympy-24066`, event 1

Query: `search_callable`, `query_name=_collect_factor_and_dimension`  
Gold: `sympy/physics/units/unitsystem.py::UnitSystem::_collect_factor_and_dimension`  
Threshold: 75; configured top-k: 3; effective top-k: 1  
Post-threshold candidates: `UnitSystem::_collect_factor_and_dimension`  
Selected action: `search_method_in_class(UnitSystem, _collect_factor_and_dimension, sympy/physics/units/unitsystem.py)`

| rank | candidate | score | gold? | retained? |
|---:|---|---:|---|---|
| 1 | `sympy/physics/units/unitsystem.py::UnitSystem::_collect_factor_and_dimension` | 95 | Yes | Yes |
| 2 | `sympy/physics/units/quantities.py::Quantity::_collect_factor_and_dimension` | 10 | No | No, threshold |

The gold is rank 1 and selected. The non-gold same-name method is in a
different file and class and receives a much lower score.

## Score comparison

Using the best scorer score for the gold entity in each event:

- Gap events: 72, 75, 75; mean 74.0.
- Non-Gap gold-available events: 95, 95, 90, 95; mean 93.75.

All three Gap events have a best gold score at or below the strict threshold;
all four non-Gap events have a best gold score above it. This is descriptive
evidence for threshold-driven loss in this sample, not a causal or statistical
significance claim.
