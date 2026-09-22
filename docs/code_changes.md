# OrcaLoca 代码差异说明

## 版本关系

- 原始 OrcaLoca source commit：`37db289be2dc3b7432183fe08b3f06becce87c27`
- 实验 instrumentation commit：`e3e097898074470d636233db9c22b129bd959415`
- Common93 artifacts commit：`a82a0e14ae0f57324194836635299c72087f4eae`

可审阅的相对 patch 位于 [`patches/orcaloca_gap_logging.patch`](../patches/orcaloca_gap_logging.patch)。原始源码快照位于 [`upstream_orcaloca/`](../upstream_orcaloca/)。

## 观测性修改

核心修改在：

```text
upstream_orcaloca/Orcar/search_agent.py
SearchWorker._disambiguation_ranking
```

它在 threshold/top-k 之前记录：

- raw candidates；
- scorer score 和原始 rank；
- threshold 后 candidates；
- effective top-k；
- candidate drop stage；
- generated precise actions。

`upstream_orcaloca/Orcar/agent.py` 和 `upstream_orcaloca/Orcar/types.py` 只负责把 `instance_id` 传到诊断事件。

## 运行兼容 plumbing

当时服务器使用 OpenAI-compatible proxy 和不在旧 tiktoken/LlamaIndex metadata 中的 model ID，因此 instrumentation commit 还包含：

- `upstream_orcaloca/Orcar/gen_config.py`：注册兼容 model metadata，并读取外部 base URL；
- `upstream_orcaloca/Orcar/formatter.py`：未知 model ID 时使用本地 token accounting fallback。

这些修改只为让既定 provider/model 配置可运行，不改变 ranking selection semantics。

## 明确没有修改

本实验没有修改：

- `CodeScorer` 的评分逻辑或 scorer prompt；
- `score_threshold`；
- `top_k_disambiguation`；
- model、temperature 或实验 prompt；
- ASQ priority；
- disambiguation decomposition；
- search tool 集合；
- action selection 行为。

尤其保留了原实现中 `if len(sorted_results) <= top_k: top_k = 1` 的行为。本仓库测量的是该实现产生的现象，而不是修复后的算法。
