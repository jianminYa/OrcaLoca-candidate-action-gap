# Common93 结果

## 核心统计

```text
SWE-bench Common instances       = 93
ranked disambiguation events     = 22
gold-available events            = 7
gap events                       = 3
Candidate-to-Action Gap Rate     = 3 / 7 = 42.86%
```

注意：7 是“gold 已在 raw candidates 中”的事件数，所以它是主指标分母；22 是所有 ranked events，93 是 instance 数，二者都不是 Gap Rate 分母。

## 七个 gold-available events

| Instance | Query | Gold Entity | Gold Score / Rank | Selected | Gap | Drop Stage |
|---|---|---|---|---|---|---|
| `matplotlib__matplotlib-23299` | `rc_context` | `lib/matplotlib/__init__.py::rc_context` | 72 / 1 | No | Yes | threshold |
| `scikit-learn__scikit-learn-14894` | `_sparse_fit` | `sklearn/svm/base.py::BaseLibSVM::_sparse_fit` | 95 / 1 | Yes | No | - |
| `sympy__sympy-12419` | `_entry` | `sympy/matrices/expressions/matexpr.py::Identity::_entry` | 95 / 1 | Yes | No | - |
| `sympy__sympy-13031` | `row_join` | `sympy/matrices/sparse.py::MutableSparseMatrix::row_join` | 75 / 2 | No | Yes | threshold |
| `sympy__sympy-13647` | `entry` | `sympy/matrices/common.py::MatrixShaping::entry` | 75 / 1--4; 70 / 6; 60 / 7 | No | Yes | threshold |
| `sympy__sympy-16792` | `routine` | `sympy/utilities/codegen.py::CodeGen::routine` | 90 / 1 | Yes | No | - |
| `sympy__sympy-24066` | `_collect_factor_and_dimension` | `sympy/physics/units/unitsystem.py::UnitSystem::_collect_factor_and_dimension` | 95 / 1 | Yes | No | - |

详细 candidate-by-candidate 分数见 [`detailed_gold_available_events.md`](../artifacts/common93_candidate_action_gap/detailed_gold_available_events.md)。

## 分数模式

三个 Gap 事件的最佳 gold score 是 `72, 75, 75`，均不满足严格 `score > 75`；四个 non-Gap 事件的 gold score 是 `95, 95, 90, 95`，均通过 threshold。这个对比是小样本描述性结果，不是统计显著性或 scorer benchmark。

## 解释边界

结果证明当前实现中出现过“已召回 gold，但没有生成 exact precise action”的信息损失；不证明该信息损失一定造成 repair failure，也不代表所有 OrcaLoca search 的 42.86% 都会丢失 gold。
