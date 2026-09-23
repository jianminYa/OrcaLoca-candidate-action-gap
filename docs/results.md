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

## File / Function Localization

这组指标来自 Common93 已保存的最终 `searcher_*.json`，不是重新运行得到的结果，也不是 Candidate-to-Action Gap 的 event-level 指标。按 OrcaLoca 原有 `upstream_orcaloca/artifact/parse_output.py` 的定义：

| 指标 | 结果 |
|---|---:|
| File Match | **87 / 93 = 93.55%** |
| Mean File Precision | **89.25%**（标准差 27.29%） |
| Function Match（原 parser 口径） | **79 / 93 = 84.95%** |
| Mean Function Precision（原 parser 口径） | **55.91%**（标准差 29.50%） |

93 个最终 `searcher_*.json` 全部存在且有效。Function Match 的严格含义是：一个 instance 的全部 patch-derived function entities 都必须出现在最终 `bug_locations`；不是命中任意一个函数就算成功。原 parser 的 93-instance 分母包含 1 个没有 function-level gold node 的 instance，因此另提供 function-evaluable 口径：排除 `django__django-10914` 后，Function Match 为 **78 / 92 = 84.78%**，至少命中一个 gold function 的 any-hit 为 **84 / 92 = 91.30%**，Mean Function Precision 为 **56.52%**。

完整定义、计算方式和逐 instance 结果见 [`docs/localization_metrics.md`](localization_metrics.md)、[`metrics.json`](../artifacts/common93_localization_metrics/metrics.json) 和 [`instance_metrics.jsonl`](../artifacts/common93_localization_metrics/instance_metrics.jsonl)。

## 分数模式

三个 Gap 事件的最佳 gold score 是 `72, 75, 75`，均不满足严格 `score > 75`；四个 non-Gap 事件的 gold score 是 `95, 95, 90, 95`，均通过 threshold。这个对比是小样本描述性结果，不是统计显著性或 scorer benchmark。

## 解释边界

结果证明当前实现中出现过“已召回 gold，但没有生成 exact precise action”的信息损失；不证明该信息损失一定造成 repair failure，也不代表所有 OrcaLoca search 的 42.86% 都会丢失 gold。
