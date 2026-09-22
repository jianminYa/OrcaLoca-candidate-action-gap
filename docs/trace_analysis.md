# 后续 Trace 分析

## 可用证据

本次保存了：

- `_disambiguation_ranking` 事件中的 raw candidates、score、threshold survivors、selected actions；
- 每个完成 instance 的最终 `searcher_*.json`；
- 部分 instance 的 `trace_analyzer_*.json`。

没有保存完整的 `action_history`、按时间排序的所有 tool call、每个 tool 的返回 payload 或 action execution receipt。因此 selected action 表示“action 已构造”，不表示“已执行并返回”。

## Gap 后 exact action 扫描

| Instance | Gap 后事件 | 后续 exact gold action | 结论 |
|---|---|---|---|
| `matplotlib__matplotlib-23299` | 无 | 未观察到 | saved diagnostic stream 中没有 recovery |
| `sympy__sympy-13031` | `MutableDenseMatrix` class、`classof` | 未观察到 | 不是 exact sparse `MutableSparseMatrix::row_join` |
| `sympy__sympy-13647` | 无 | 未观察到 | nested `entry` 没有后续 exact action |

统计为：later exact gold action observed `0/3`；observed later-recovered `0/3`；saved diagnostic stream 中没有 later exact action `3/3`。

这不能证明 arbitrary non-disambiguation tool call 从未访问过 gold。当前最强可证结论是：**没有 later exact gold action 出现在保存的诊断流中**。

## Final localization

- Matplotlib：final `bug_locations` 包含 exact `rc_context`；
- SymPy-13031：final `bug_locations` 包含 exact sparse `MutableSparseMatrix::row_join`；
- SymPy-13647：final `bug_locations` 只包含 parent `_eval_col_insert`，不包含 exact nested `entry`，但 trace analyzer 将 `entry` 作为 traced code 报告。

这些 final localization 字段来自最终 search response，不是执行日志，不能据此计算 Action-to-Execution Gap。

## Action-to-Execution

四个 non-Gap gold-available events 生成了 exact gold action，但当前 artifacts 没有直接执行确认。因此只能记录：

```text
selected exact gold action generated = 4 events
direct execution confirmation       = unavailable
```

本次没有分析最终 repair/resolved，也没有声称 Gap 导致 repair failure。
