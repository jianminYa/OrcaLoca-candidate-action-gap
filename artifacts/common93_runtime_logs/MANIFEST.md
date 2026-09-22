# Common93 原始运行日志

本目录保存 Common93 运行产生的原始运行日志和最终输出。日志按原始运行位置重新组织，但文件内容保持不变；`log_1`、`log_2` 是服务器上的补充/重试运行，未用于主统计。

## 目录说明

| 目录 | 内容 | 统计用途 |
|---|---|---|
| [`primary_runtime_logs/`](primary_runtime_logs/) | 主运行的 per-instance OrcaLoca 日志，包括 search agent、action history、search queue、CodeScorer、tracer 等 | 主实验原始证据 |
| [`final_outputs/`](final_outputs/) | 主运行的 per-instance `searcher_*.json` 和 `trace_analyzer_*.json` | 最终搜索/trace 汇总输出 |
| [`retry_runtime_logs/`](retry_runtime_logs/) | `log_1`、`log_2` 中与 Common93 instance 重合的补充运行日志 | 重试和运行过程核对，不并入主统计 |
| [`run_control/`](run_control/) | supervisor 运行记录 | 进度、批次、失败/重试审计 |
| [`key_logs/`](key_logs/) | 指向仓库内原始文件的 Git symbolic links | README 中快速访问关键案例 |

## 重要说明

- 主运行目录只收录 `common93_instance_ids.txt` 中的 93 个 instance；服务器上不属于 Common93 的额外目录没有复制。
- 这些是原始自由文本日志，可能包含 prompt、源码片段和搜索结果；它们不是新的实验结果，也没有重新调用 API。
- API key、token、`.env`、`proxy.txt` 和 Docker 数据没有复制到仓库。上传前对日志副本进行了敏感模式扫描。
- `key_logs/` 中的链接是仓库内相对路径的 Git symbolic links，不指向服务器外部路径。
- 结构化 Candidate-to-Action 统计仍以 [`../common93_candidate_action_gap/disambiguation_events.jsonl`](../common93_candidate_action_gap/disambiguation_events.jsonl) 为准；原始日志用于人工核验和后续 trace 分析。

完整文件校验值见 [`SHA256SUMS`](SHA256SUMS)。
