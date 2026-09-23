# 后续 Trace 分析

## 可用证据

本次保存了：

- `_disambiguation_ranking` 事件中的 raw candidates、score、threshold survivors、selected actions；
- 每个完成 instance 的最终 `searcher_*.json`；
- 部分 instance 的 `trace_analyzer_*.json`；
- Common93 主运行的原始 `Orcar.search_agent.log`、`action_history.log`、`search_queue.log`、`Orcar.code_scorer.log`、`orcar_total.log` 等日志，位于 [`artifacts/common93_runtime_logs/`](../artifacts/common93_runtime_logs/)。

原始日志中确实保存了 action history、搜索 Agent 输出、队列状态和许多 tool 返回内容；此前的报告把“没有整理进已提交 artifacts 的结构化 trace”误写成了“没有保存日志”。现在原始日志已经上传，但它们仍是自由文本，未统一关联到每一个 diagnostic event ID，也不总是提供标准化的 action execution receipt。因此 `selected action` 表示“action 已构造”，不能单独等同于“已执行并成功返回”。

## Gap 后 exact action 扫描

| Instance | Gap 后事件 | 后续 exact gold action | 结论 |
|---|---|---|---|
| `matplotlib__matplotlib-23299` | 无 | 未观察到 | saved diagnostic stream 中没有 recovery |
| `sympy__sympy-13031` | `MutableDenseMatrix` class、`classof` | 未观察到 | 不是 exact sparse `MutableSparseMatrix::row_join` |
| `sympy__sympy-13647` | 无 | 未观察到 | nested `entry` 没有后续 exact action |

统计为：later exact gold action observed `0/3`；observed later-recovered `0/3`；saved diagnostic stream 中没有 later exact action `3/3`。

这里的 `0/3` 严格指“结构化 diagnostic event stream 中没有 later exact gold action”。原始 `action_history.log` 是更宽的自由文本 history：例如 `sympy__sympy-13031` 在初始 `row_join` Gap 后面仍出现过 `MutableSparseMatrix::row_join` 的 action request。它说明该案例不能据此判断 gold 永久丢失，但由于没有标准化返回状态，不能把 request 当成成功执行 receipt。结合原始 `search_agent`、`action_history` 和 `search_queue` 日志，可以进行人工核验；但这不能证明 arbitrary non-disambiguation tool call 从未访问过 gold。当前最强可证结论仍是：**没有 later exact gold action 出现在保存的结构化诊断流中**。三例的逐日志分析见 [`docs/gap_cases.md`](gap_cases.md)，原始日志入口见 [`README.md`](../README.md) 的“完整运行日志与关键链接”部分。

## Final localization

- Matplotlib：final `bug_locations` 包含 exact `rc_context`；
- SymPy-13031：final `bug_locations` 包含 exact sparse `MutableSparseMatrix::row_join`；
- SymPy-13647：final `bug_locations` 只包含 parent `_eval_col_insert`，不包含 exact nested `entry`，但 trace analyzer 将 `entry` 作为 traced code 报告。

这些 final localization 字段来自最终 search response，不是标准化的执行 receipt，不能据此可靠计算 Action-to-Execution Gap。

## Action-to-Execution

四个 non-Gap gold-available events 生成了 exact gold action，但当前 artifacts 没有直接执行确认。因此只能记录：

```text
selected exact gold action generated = 4 events
direct execution confirmation       = unavailable
```

本次没有分析最终 repair/resolved，也没有声称 Gap 导致 repair failure。
