# OrcaLoca Candidate-to-Action Gap 实验

本仓库是一个围绕 OrcaLoca **Candidate-to-Action information loss** 的独立实验与分析仓库，不是 OrcaLoca 原项目的再次发布。

## 简明结论

我们研究 OrcaLoca 在 disambiguation 阶段已经召回 gold entity 后，是否会因为 `CodeScorer`、threshold 或 top-k 筛选，导致没有生成对应的 precise search action。

在 SWE-bench Common 的本次运行中观察到：

- 93 个实例全部完成；
- 22 个 ranked disambiguation events；
- 7 个事件的 `raw_candidates` 已包含 gold entity；
- 其中 3 个没有生成对应的 precise action；
- Candidate-to-Action Gap Rate = `3 / 7 = 42.86%`；
- 3 个 Gap 全部发生在 threshold 阶段，未观察到 top-k 或 action generation 阶段的 Gap。

这证明当前实现中确实存在 candidate-to-action information loss，但不能据此声称它一定导致最终 repair failure。

## 1. 研究背景

OrcaLoca 会先使用搜索工具召回可能的函数、方法或类。当一个查询对应多个函数/方法时，系统会进入 disambiguation ranking：对候选进行 `CodeScorer` 打分，再通过 threshold 和 top-k 生成更精确的检查动作。

本仓库只研究这条转换链上的信息是否丢失：

```text
raw candidate → scorer score → threshold/top-k → selected precise action
```

## 2. 研究问题

核心问题是：

> 当 gold function/method 已经进入 raw disambiguation candidates 时，OrcaLoca 是否会在 `_disambiguation_ranking` 中将它过滤掉，从而不生成对应的 precise search action？

本实验把 Gap Event 定义为：

```text
gold ∈ raw_candidates
AND
gold ∉ selected_actions
```

主指标为：

```text
Candidate-to-Action Gap Rate
= # Gap Events / # Gold-Available Disambiguation Events
```

分母不是 93，也不是全部 disambiguation events，而是 gold 已经出现在 ranked raw candidates 中的事件数。

## 3. OrcaLoca 中的 Disambiguation 流程

```mermaid
flowchart TD
    A[Search Action] --> B[Inverted Index]
    B --> C[Raw Disambiguation Candidates]
    C --> D[CodeScorer]
    D --> E[Threshold / Top-K]
    E --> F[Selected Precise Actions]
    F --> G[ASQ]
    G --> H[Executed Search]

    C -->|Gold exists here| X[Gold Candidate]
    X -->|Dropped| Y[Candidate-to-Action Gap]
```

本次观测重点是图中的 `C → D → E → F`，不是重新设计 OrcaLoca 的搜索或评分方法。

## 4. Candidate-to-Action Gap 定义

对每个 ranked callable/method event，离线构造：

- `G`：当前 instance 的 patch-derived gold callable entities；
- `C`：事件中的 `raw_candidates`；
- `A`：事件中 `selected_actions` 对应的 canonical entities。

当 `G ∩ C` 非空时，该事件是 gold-available；当 `(G ∩ C) ∩ A` 为空时，该事件是 Gap Event。`search_class` 和 `search_file_contents` 事件单独记录，但不进入主 Gap 分母，因为它们不经过 CodeScorer ranking。

## 5. 数据集

使用 OrcaLoca 原有的 `SWE-bench_common` 加载逻辑，即：

```text
SWE-bench Common = SWE-bench Lite ∩ SWE-bench Verified
```

本次验证 `len(dataset) == 93`，完整 instance 列表保存在 [`common93_instance_ids.txt`](artifacts/common93_candidate_action_gap/common93_instance_ids.txt)。

## 6. 实验设计

- 不修改 `CodeScorer`、prompt、model、temperature、priority 或 ASQ；
- 不修改 `score_threshold=75` 或 `top_k_disambiguation=3`；
- 只在 `_disambiguation_ranking` 记录剪枝前候选、score、threshold 后候选和生成 action；
- gold 只在运行结束后通过 patch-derived artifacts 离线 join，live agent 不读取 gold；
- Common93 运行完成后再进行离线统计和源码人工核验；
- 当前仓库不保存 API key、token、`.env` 或 Docker 数据。

完整运行参数见 [`run_config.json`](artifacts/common93_candidate_action_gap/run_config.json)，方法说明见 [`docs/methodology.md`](docs/methodology.md)。

## 7. 实验结果

| Instance | Query | Gold Entity | Gold Score | Threshold | Selected | Gap | Drop Stage |
|---|---|---|---:|---:|---|---|---|
| `matplotlib__matplotlib-23299` | `rc_context` | `lib/matplotlib/__init__.py::rc_context` | 72 | 75 | No | Yes | threshold |
| `scikit-learn__scikit-learn-14894` | `_sparse_fit` | `sklearn/svm/base.py::BaseLibSVM::_sparse_fit` | 95 | 75 | Yes | No | - |
| `sympy__sympy-12419` | `_entry` | `sympy/matrices/expressions/matexpr.py::Identity::_entry` | 95 | 75 | Yes | No | - |
| `sympy__sympy-13031` | `row_join` | `sympy/matrices/sparse.py::MutableSparseMatrix::row_join` | 75 | 75 | No | Yes | threshold |
| `sympy__sympy-13647` | `entry` | `sympy/matrices/common.py::MatrixShaping::entry` | 75/70/60 | 75 | No | Yes | threshold |
| `sympy__sympy-16792` | `routine` | `sympy/utilities/codegen.py::CodeGen::routine` | 90 | 75 | Yes | No | - |
| `sympy__sympy-24066` | `_collect_factor_and_dimension` | `sympy/physics/units/unitsystem.py::UnitSystem::_collect_factor_and_dimension` | 95 | 75 | Yes | No | - |

汇总：

```text
ranked disambiguation events = 22
gold-available events         = 7
gap events                    = 3
Gap Rate                      = 3 / 7 = 42.86%

Gap stage counts:
  threshold                   = 3
  top-k                       = 0
  action generation           = 0
```

注意：上面三个数字是 Gap 原因的计数，不是运行配置。实际运行配置仍为 `score_threshold=75`、`top_k_disambiguation=3`。

### 指标含义与统计单位

| 指标 | 数值 | 统计单位 | 含义 |
|---|---:|---|---|
| `num_instances` | 93 | instance | Common93 中完成运行的 SWE-bench 问题实例数；不是 Gap Rate 的分母 |
| `all_disambiguation_events` | 27 | event | 搜索索引返回多个可能位置、因此进入一次 disambiguation 处理的次数 |
| `ranked_disambiguation_events` | 22 | event | 上述事件中属于 callable/method、实际经过 CodeScorer + threshold/top-k 的次数 |
| `gold_available_events` | 7 | event | ranked event 的 `raw_candidates` 中至少包含一个精确 gold entity 的次数 |
| `gap_events` | 3 | event | gold 在 `raw_candidates` 中，但没有对应 `selected_action` 的次数 |
| `candidate_to_action_gap_rate` | 42.86% | event / event | `3 / 7`；表示 gold-available ranked events 中发生 Gap 的比例 |
| `gap_by_stage.threshold` | 3 | event | 3 个 Gap 中有 3 个在 threshold 阶段丢失；不是 `score_threshold` 参数值 |
| `gap_by_stage.top_k` | 0 | event | 没有 Gap 是“通过 threshold 但未进入 top-3”造成的；不是 `top_k_disambiguation=0` |
| `gap_by_stage.action_generation` | 0 | event | 没有 Gap 是“已被选中但构造 precise action 失败”造成的 |

这里的 `event` 不是模型调用、候选数量或 instance。它表示一次具体的歧义决策点：某个搜索 action 查询索引后返回多个匹配位置，OrcaLoca 随后调用 `_disambiguation_ranking()`。同一个 instance 可以有多个 event；一次返回 24 个候选的位置仍然只算 1 个 event。

本次运行中，18/93 个 instance 至少出现过一次 disambiguation，16/93 个 instance 出现过 ranked callable/method disambiguation；其余 instance 可能仍然执行了搜索，只是没有进入多位置消歧分支。

机器可读结果在 [`summary.json`](artifacts/common93_candidate_action_gap/summary.json)，详细候选和 score 在 [`detailed_gold_available_events.md`](artifacts/common93_candidate_action_gap/detailed_gold_available_events.md)，汇总解释在 [`docs/results.md`](docs/results.md)。

## 8. Gap 案例分析

三件 Gap 均通过 patch-derived gold metadata 和对应 base commit 的源码人工核验：

1. `matplotlib__matplotlib-23299`：`rc_context` score 72，rank 1，低于 75；
2. `sympy__sympy-13031`：`MutableSparseMatrix::row_join` score 75，rank 2；非 gold 的 `NewMatrix::row_join` score 85 被选中；
3. `sympy__sympy-13647`：嵌套的 `MatrixShaping::_eval_col_insert::entry` 出现多个 canonical candidate，最佳 score 75，因严格 threshold 被过滤。

完整人工审计见 [`manual_audit.md`](artifacts/common93_candidate_action_gap/manual_audit.md) 和 [`docs/gap_cases.md`](docs/gap_cases.md)。

## 9. 后续 Trace 分析

服务器上的原始搜索日志已经随本仓库上传。3 个 Gap 的 `search_agent`、`action_history`、`search_queue` 和 `CodeScorer` 日志可从下一节的关键链接访问。需要区分两类证据：

- `disambiguation_events.jsonl` 是结构化的 candidate → action 诊断流，用于主指标；
- 原始日志记录完整的搜索 Agent 输出、队列变化和 action history，但它们是自由文本，尚未被统一规范成带 event ID 的执行 receipt。

结合已保存的 diagnostic event stream，3 个 Gap 都没有后续 exact gold action：

```text
later exact gold action observed = 0 / 3
no later exact gold action in saved diagnostic stream = 3 / 3
observed later-recovered cases = 0 / 3
```

因此可以检查原始搜索过程，但仍不能仅凭日志自动证明每个 action 都获得了成功执行回执。当前最强可证结论是：结构化诊断流中没有 later exact gold action；Action-to-Execution Gap 仍不能从现有产物可靠计算。详见 [`docs/trace_analysis.md`](docs/trace_analysis.md)。

## 10. 完整运行日志与关键链接

Common93 主运行的 93 个 instance 日志已经上传到 [`artifacts/common93_runtime_logs/`](artifacts/common93_runtime_logs/)。其中包含 1,674 个主运行日志文件、183 个最终输出文件，以及 162 个补充/重试日志文件，总大小约 54 MiB。目录和 SHA-256 校验值见 [`MANIFEST.md`](artifacts/common93_runtime_logs/MANIFEST.md) 和 [`SHA256SUMS`](artifacts/common93_runtime_logs/SHA256SUMS)。

`key_logs/` 中保留了仓库内的相对 Git symbolic links；但为避免 GitHub 页面只显示软链接目标字符串，下面 README 表格直接链接到已经实际上传的日志文件，而不是只链接到软链接名称：

| Gap case | Search Agent | Action history | Search queue | CodeScorer |
|---|---|---|---|---|
| `matplotlib__matplotlib-23299` | [`search_agent`](artifacts/common93_runtime_logs/primary_runtime_logs/matplotlib__matplotlib-23299/Orcar.search_agent.log) | [`action_history`](artifacts/common93_runtime_logs/primary_runtime_logs/matplotlib__matplotlib-23299/action_history.log) | [`search_queue`](artifacts/common93_runtime_logs/primary_runtime_logs/matplotlib__matplotlib-23299/search_queue.log) | [`code_scorer`](artifacts/common93_runtime_logs/primary_runtime_logs/matplotlib__matplotlib-23299/Orcar.code_scorer.log) |
| `sympy__sympy-13031` | [`search_agent`](artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13031/Orcar.search_agent.log) | [`action_history`](artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13031/action_history.log) | [`search_queue`](artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13031/search_queue.log) | [`code_scorer`](artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13031/Orcar.code_scorer.log) |
| `sympy__sympy-13647` | [`search_agent`](artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13647/Orcar.search_agent.log) | [`action_history`](artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13647/action_history.log) | [`search_queue`](artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13647/search_queue.log) | [`code_scorer`](artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13647/Orcar.code_scorer.log) |

主诊断流和结果的快捷链接：[`disambiguation_events.jsonl`](artifacts/common93_candidate_action_gap/disambiguation_events.jsonl)、[`summary.json`](artifacts/common93_candidate_action_gap/summary.json)。

## 11. 仓库结构

```text
.
├── README.md
├── docs/
│   ├── methodology.md
│   ├── results.md
│   ├── gap_cases.md
│   ├── trace_analysis.md
│   └── code_changes.md
├── artifacts/common93_candidate_action_gap/
│   ├── summary.json
│   ├── summary.md
│   ├── disambiguation_events.jsonl
│   ├── gold_available_events.jsonl
│   ├── gap_events.jsonl
│   ├── gold_entities.json
│   ├── common93_instance_ids.txt
│   ├── run_config.json
│   └── manual_audit.md
├── artifacts/common93_runtime_logs/
│   ├── primary_runtime_logs/
│   ├── final_outputs/
│   ├── retry_runtime_logs/
│   ├── key_logs/
│   ├── run_control/
│   ├── MANIFEST.md
│   └── SHA256SUMS
├── scripts/
│   ├── analyze_gap.py
│   └── build_gold_entities.py
├── patches/
│   └── orcaloca_gap_logging.patch
└── upstream_orcaloca/
    ├── README.md
    └── Orcar/, dataset/, evaluation/, tests/, ...
```

原 OrcaLoca 源码保留在 `upstream_orcaloca/`，作为可追溯的 upstream snapshot；仓库首页和主要文档不再以它为主体。

## 12. 如何复现

### 12.1 只做离线分析

不需要 API：

```bash
python3 scripts/analyze_gap.py \
  --artifact-dir artifacts/common93_candidate_action_gap
```

### 12.2 重新构造 gold entities

这不是本次已完成实验的一部分。需要外部数据集缓存和目标仓库 checkout；运行前将 upstream snapshot 加入 Python path：

```bash
PYTHONPATH=upstream_orcaloca python3 scripts/build_gold_entities.py \
  --dataset SWE-bench_common \
  --repo-root /path/to/repositories \
  --output-dir /path/to/artifacts
```

### 12.3 重新运行 Agent

当前仓库不提供 secret。若未来需要重跑，应在仓库外配置 OpenAI-compatible provider、model、base URL 和 API key，并使用 `run_config.json` 中记录的非 secret 参数；不要将凭据写入仓库或日志。

## 13. 与原始 OrcaLoca 的关系

原始项目快照在 [`upstream_orcaloca/`](upstream_orcaloca/)，原始 README 保存在 [`upstream_orcaloca/ORIGINAL_README.md`](upstream_orcaloca/ORIGINAL_README.md)。本实验以 OrcaLoca 的原始 ranking 行为为对象，仅增加观测日志和必要的运行兼容 plumbing。

差异说明和可审阅 patch 见 [`docs/code_changes.md`](docs/code_changes.md) 与 [`patches/orcaloca_gap_logging.patch`](patches/orcaloca_gap_logging.patch)。

## 14. 当前结论与限制

当前结论是：在 Common93 本次运行中，共有 7 个 gold 已进入 ranked disambiguation raw candidates 的事件，其中 3 个没有转化为对应 precise action；3 个均由 threshold 过滤造成。

不能将 `42.86%` 表述为 OrcaLoca 所有搜索都会丢失 gold 的比例。当前分母只有 7 个 gold-available events，样本事件数较少；仍需更大样本或 intervention 实验判断普遍性和 downstream 因果影响。

本实验没有验证：

```text
action → execution → final localization → repair patch → resolved
```

因此不能声称 Candidate-to-Action Gap 已经导致最终 repair failure。
