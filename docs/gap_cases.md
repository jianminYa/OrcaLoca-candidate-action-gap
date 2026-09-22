# 三个 Gap 案例

三个案例均已对照 `gold_entities.json` 的 patch-derived entity、`golden_stats.csv` 的 base commit，以及目标仓库 base source 做人工核验。完整记录见 [`artifacts/.../manual_audit.md`](../artifacts/common93_candidate_action_gap/manual_audit.md)。

## 1. matplotlib-23299

- Query：`search_callable(rc_context)`。
- Gold：`lib/matplotlib/__init__.py::rc_context`。
- Raw candidates：`__init__.py::rc_context` score 72（gold，rank 1）；`pyplot.py::rc_context` score 20（同名但不同文件，非 gold）。
- Threshold：75；selected actions：none。
- 结论：gold 与官方 patch 函数及文件一致，72 未达到严格 threshold，构成 threshold Gap。
- 后续 exact gold action：当前诊断事件流未观察到；完整 action execution 日志未保存。
- Final localization：searcher 输出包含 `lib/matplotlib/__init__.py::rc_context`。

## 2. sympy-13031

- Query：`search_callable(row_join)`。
- Gold：`sympy/matrices/sparse.py::MutableSparseMatrix::row_join`。
- Raw candidates：`NewMatrix::row_join` score 85（rank 1，selected）；gold score 75（rank 2）；`MatrixShaping::row_join` score 70（rank 3）。
- Threshold：75；gold 正好等于 threshold，但当前实现使用严格 `score > 75`，所以没有 action。
- 结论：selected 的 `NewMatrix::row_join` 不是 gold，文件和 class 都不同；构成 threshold Gap。
- 后续 exact gold action：未观察到；后续事件为 `MutableDenseMatrix` class 和 `classof`，无法证明重新搜索了 sparse gold。
- Final localization：searcher 输出包含 `sympy/matrices/sparse.py::MutableSparseMatrix::row_join`，但这不是 action execution 证据。

## 3. sympy-13647

- Query：`search_callable(entry)`，event 2。
- Gold：patch node chain 精确指向 `sympy/matrices/common.py::MatrixShaping::_eval_col_insert::entry`。
- Raw candidates：`MatrixShaping::entry` 的重复 canonical candidate 得分为 75（ranks 1--4）、70（rank 6）、60（rank 7）；无 selected action。
- Threshold：75；所有 gold occurrence 都被过滤。
- 结论：源码和 patch 行 89 一致；现有 canonical string 不包含 nested helper parent，因此出现重复 identity，但没有把其他 class 的同名 `entry` 当作 gold。
- 后续 exact gold action：未观察到。
- Final localization：searcher 输出包含 parent `_eval_col_insert`，但不是 exact nested `entry`；trace analyzer 另记录了 `entry`。

## 共同结论

三个 Gap 都是 threshold stage，top-k 和 action generation 均为 0。后续恢复只能报告为“当前保存诊断流中未观察到”，不能升级为“永久丢失”。
