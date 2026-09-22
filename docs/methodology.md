# 实验方法

## 研究对象

本实验只观测 OrcaLoca 的 callable/method disambiguation ranking。主链路是：

```text
raw_candidates → CodeScorer → score_threshold/top-k → selected_actions
```

`search_class` 和 `search_file_contents` 不经过 CodeScorer，因此只作为完整性事件记录，不放入主 Gap 分母。

## 数据集与 gold

`SWE-bench_common` 使用 OrcaLoca 原有 loader 构造为 SWE-bench Lite 与 SWE-bench Verified 的交集。本次运行验证为 93 个 instance。gold entity 来自官方 patch 的既有解析逻辑，canonical representation 至少包含文件路径和 entity identity：

```text
path/file.py::function
path/file.py::Class::method
```

Gold 只在 run 完成后离线 join，live Agent 不读取 patch gold。

## 事件定义

对每个 ranked event：

```text
G = 当前 instance 的 gold callable entities
C = raw_candidates
A = selected_actions 的 canonical entities
```

```text
Gold-Available Event: G ∩ C != ∅
Gap Event: (G ∩ C) != ∅ AND (G ∩ C) ∩ A == ∅
```

分母是 Gold-Available Event 数，不是 instance 数，也不是所有 disambiguation event 数。

## drop stage

- `threshold`：gold score 未通过当前严格的 `score > score_threshold` 条件；
- `top_k`：gold 通过 threshold，但不在保留的 top-k 中；
- `action_generation`：gold 已进入 selected ranking，但没有生成对应 action。

本次 Gap stage 计数为 threshold 3、top-k 0、action generation 0。这里的 3/0/0 是 Gap 原因的事件数量，不是配置值；实际运行配置为 `score_threshold=75`、`top_k_disambiguation=3`。

## 可复现入口

- 原始事件：`artifacts/common93_candidate_action_gap/disambiguation_events.jsonl`
- gold：`artifacts/common93_candidate_action_gap/gold_entities.json`
- 离线脚本：`scripts/analyze_gap.py`
- 参数：`artifacts/common93_candidate_action_gap/run_config.json`

本仓库没有把 API provider 的 secret 放进配置；重跑需要在仓库外注入 provider、base URL 和 API key。
