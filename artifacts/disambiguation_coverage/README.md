# Common93 Disambiguation Coverage Audit

这是一次纯离线审计，用来验证 OrcaLoca 的 instrumentation 是否记录了实际运行中所有多候选搜索。未重新运行 Common93，也未调用 LLM/API。

## 证据口径

- 执行证据来自选定运行尝试的 `Orcar.search_agent.log` 中实际返回给 agent 的 `Search content`，以及 `search_queue.log` 中实际发生但被去重的 `Duplicate search result`。
- 多候选独立判据是原始返回中的 `<Disambiguation>` 和 `Possible Location`，不是现有 `disambiguation_events.jsonl` 反推。
- `django__django-13033`、`matplotlib__matplotlib-23476`、`sympy__sympy-22714`、`sympy__sympy-23262` 的主日志没有可解析的实际 `Search content`，使用其成功补跑的 `retry_runtime_logs/log_1`；其他 retry 不并入，避免重复计算。

## 结果摘要

| 指标 | 数值 |
| --- | ---: |
| Common93 instances | 93 |
| 所有实际执行 search actions | 639 |
| 四类消歧相关 actions | 614 |
| 实际 multi-candidate events | 27 |
| 已记录 disambiguation events | 27 |
| matched events | 27 |
| missing events | 0 |
| logging coverage | 100.00% |

## 文件

- [`coverage_analysis.md`](coverage_analysis.md)：触发条件、逐类统计、漏斗和 RQ 结论。
- [`coverage_summary.json`](coverage_summary.json)：机器可读汇总。
- [`executed_search_actions.jsonl`](executed_search_actions.jsonl)：实际执行动作及日志证据位置。
- [`actual_disambiguation_events.jsonl`](actual_disambiguation_events.jsonl)：从 raw runtime result 独立恢复的多候选事件。
- [`missing_events.jsonl`](missing_events.jsonl)：raw multi-candidate 但结构化日志没有匹配的事件。
- [`unmatched_logged_events.jsonl`](unmatched_logged_events.jsonl)：结构化日志存在但 raw runtime 没有匹配的事件。

`candidate_count` 对 `<Disambiguation>` 结果表示 raw result 中的 `Possible Location` 数量；对普通返回只表示日志中可观察到的返回项数（0 或 1），不声称倒排索引内部不存在隐藏的其他项。

脚本：[`scripts/audit_disambiguation_coverage.py`](../../scripts/audit_disambiguation_coverage.py)。
