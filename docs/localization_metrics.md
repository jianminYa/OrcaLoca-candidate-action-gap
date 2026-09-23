# Common93 File / Function Localization 指标

## 结论

这组指标是对已经保存的 93 个 `searcher_*.json` 做的离线统计，没有重新调用模型。预测定位来自每个输出中的 `bug_locations`，gold 来自 [`gold_entities.json`](../artifacts/common93_candidate_action_gap/gold_entities.json) 中的 `parsed_patch.diff_locs`。

按 OrcaLoca 原有 [`upstream_orcaloca/artifact/parse_output.py`](../upstream_orcaloca/artifact/parse_output.py) 的定义：

| 指标 | 结果 |
|---|---:|
| File Match | **87 / 93 = 93.55%** |
| Mean File Precision | **89.25%**（标准差 27.29%） |
| Function Match（原 parser，93 个 instance） | **79 / 93 = 84.95%** |
| Mean Function Precision（原 parser） | **55.91%**（标准差 29.50%） |

所有 93 个 instance 都存在且成功解析了最终 `searcher_*.json`，因此这次没有因缺失或无效输出而剔除样本：

```text
valid outputs = 93
missing       = 0
invalid       = 0
```

## 指标定义

### File Match

一个 instance 的 gold file 集合记为 `G_file`，`bug_locations` 中预测出的文件集合记为 `P_file`。File Match 要求：

```text
G_file ⊆ P_file
```

因此 87/93 表示 93 个 instance 中，有 87 个把该 patch 涉及的全部 gold 文件包含在最终 `bug_locations` 中。当前每个 instance 的 patch 都只有一个 gold file，所以本次 File Match 与 file any-hit 数值相同；这不是一般情况下的必然关系。

### Mean File Precision

逐 instance 计算：

```text
|G_file ∩ P_file| / |P_file|
```

再对 93 个 instance 求平均。它衡量最终列出的文件中有多少是 gold 文件。它与 File Match 不同：一个 instance 可以包含 gold 文件，但同时列出多个无关文件，因此命中但 precision 较低。

### Function Match

gold function set 由 `parsed_patch.diff_locs.diff_nodes` 按 OrcaLoca 原 parser 生成，方法实体使用 `file.py:Class.method` 表示。`bug_locations` 中的 class/method 也转换为相同形式。Function Match 要求：

```text
G_function ⊆ P_function
```

所以 79/93 是“该 instance 的全部 patch-derived function entities 都被最终定位结果覆盖”的比例，不是只要命中一个函数就算成功。

原 parser 的 93-instance 口径包含 1 个没有 function-level gold node 的 instance（`django__django-10914`）。按照原实现，空 gold function set 会使 subset 判断成立，但它的函数 precision 仍可能为 0；因此同时报告下面更容易解释的 function-evaluable 口径。

## Function-evaluable 子集

排除 `django__django-10914` 后，92 个 instance 有至少一个 function-level gold entity：

| 指标 | 结果 |
|---|---:|
| Function Match（92 个可评估 instance） | **78 / 92 = 84.78%** |
| Function any-hit（至少命中一个 gold function） | **84 / 92 = 91.30%** |
| Mean Function Precision（92 个可评估 instance） | **56.52%**（标准差 29.07%） |
| Mean Function Recall（92 个可评估 instance） | **88.68%** |

这里的 any-hit 和 recall 只是补充诊断，不替代 OrcaLoca 原 parser 的 Function Match。Function Match 更严格，因为一个 patch 可能涉及多个 function/method，必须全部覆盖才算 match。

## 与 Candidate-to-Action Gap 的关系

这不是 Candidate-to-Action Gap 主指标。两者统计层级不同：

```text
Candidate-to-Action Gap：ranked disambiguation event
  3 / 7 = 42.86%

File / Function Localization：Common93 instance 的最终 bug_locations
  file match     = 87 / 93 = 93.55%
  function match = 79 / 93 = 84.95%（原 parser 口径）
```

因此不能把 `42.86%` 与 `93.55%` 或 `84.95%` 直接相减，也不能据此断言 Gap 必然导致最终 repair failure。前者回答“gold candidate 是否在 candidate → action 阶段消失”，后者回答“最终保存的 `bug_locations` 是否覆盖 patch-derived gold 定位”。本次没有把最终 repair/resolved 作为指标。

## 可复现文件

- 计算脚本：[`scripts/compute_localization_metrics.py`](../scripts/compute_localization_metrics.py)
- 汇总 JSON：[`metrics.json`](../artifacts/common93_localization_metrics/metrics.json)
- 逐 instance 明细：[`instance_metrics.jsonl`](../artifacts/common93_localization_metrics/instance_metrics.jsonl)
- 最终预测原始日志目录：[`artifacts/common93_runtime_logs/final_outputs/`](../artifacts/common93_runtime_logs/final_outputs/)

离线重算命令：

```bash
python3 scripts/compute_localization_metrics.py \
  --gold-dir artifacts/common93_candidate_action_gap \
  --runtime-dir artifacts/common93_runtime_logs \
  --output-dir artifacts/common93_localization_metrics
```
