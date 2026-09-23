# 三个 Gap 案例：结合运行日志的具体分析

本页直接对照三类证据：

1. 结构化 disambiguation 诊断日志：记录 `raw_candidates → score → threshold → selected_actions`；
2. OrcaLoca `search_agent` / `action_history` 原始日志：确认模型收到的歧义候选以及后续 action history；
3. patch-derived gold 和 base commit 源码：确认哪个候选才是真正的 gold entity。

这里的“被过滤”特指对应 ranked disambiguation event 中没有生成 gold 的 precise action。后续 `action_history` 中偶尔出现的 action request 只说明 Agent 后来请求过该 action，不等同于可靠的工具执行成功回执。

## 总览

| Instance | Query | Gold candidate | Gold score / rank | Threshold 后保留 | Selected action | 结论 |
|---|---|---|---:|---|---|---|
| `matplotlib__matplotlib-23299` | `rc_context` | `lib/matplotlib/__init__.py::rc_context` | 72 / 1 | 无 | 无 | 全部候选低于 threshold |
| `sympy__sympy-13031` | `row_join` | `sympy/matrices/sparse.py::MutableSparseMatrix::row_join` | 75 / 2 | `NewMatrix::row_join` | 非 gold 的 `NewMatrix::row_join` | gold 未通过严格 threshold |
| `sympy__sympy-13647` | `entry` | `common.py::MatrixShaping::entry`（对应 nested helper） | 75 / 1--4、70 / 6、60 / 7 | 无 | 无 | 所有候选均未通过 threshold |

三条结构化事件分别位于 [`disambiguation_events.jsonl` 第 5 行](../artifacts/common93_candidate_action_gap/disambiguation_events.jsonl#L5)、[第 12 行](../artifacts/common93_candidate_action_gap/disambiguation_events.jsonl#L12) 和[第 16 行](../artifacts/common93_candidate_action_gap/disambiguation_events.jsonl#L16)。这些行是本页分数、排名和过滤结论的直接日志来源。

## 1. matplotlib：gold 排名第一，但 72 分仍被 threshold 丢弃

### Gold 是什么

官方 patch 的 changed node 是 `lib/matplotlib/__init__.py` 中的顶层函数 `rc_context`。对应 base commit 源码中的函数起始于约 1058 行，patch 涉及该函数内部逻辑，因此下面这个完整实体才是 gold：

```text
lib/matplotlib/__init__.py::rc_context
```

`lib/matplotlib/pyplot.py::rc_context` 只是同名函数，不是 gold；文件路径已经不同。

### 日志中的候选和过滤

`search_agent.log` 在 [L151 附近](../artifacts/common93_runtime_logs/primary_runtime_logs/matplotlib__matplotlib-23299/Orcar.search_agent.log#L151)记录了 `search_callable(query_name=rc_context)` 返回的两个位置：

| Rank | Raw candidate | Score | Threshold 75 | 结果 |
|---:|---|---:|---|---|
| 1 | `lib/matplotlib/__init__.py::rc_context`（gold） | 72 | 不通过 | 丢弃 |
| 2 | `lib/matplotlib/pyplot.py::rc_context`（同名、非 gold） | 20 | 不通过 | 丢弃 |

结构化事件的实际状态是：

```text
raw_candidates            = [__init__.py::rc_context, pyplot.py::rc_context]
post_threshold_candidates = []
selected_actions          = []
skip_reason               = all_candidates_below_threshold
score_threshold           = 75
top_k_disambiguation      = 3
effective_top_k           = 1
```

因此这里不是 top-k 把排名第一的 gold 截掉：gold 在 threshold 前已经是 rank 1，但 score 72 不满足当前实现的严格保留条件。由于两个候选都没有通过 threshold，后面没有任何 precise action 可供 top-k 选择。

### 原始 action history 说明

[`action_history.log`](../artifacts/common93_runtime_logs/primary_runtime_logs/matplotlib__matplotlib-23299/action_history.log) 记录了多次 `search_callable` 查询，包括后续带 `file_path=lib/matplotlib/__init__.py` 的请求（例如 [L98 附近](../artifacts/common93_runtime_logs/primary_runtime_logs/matplotlib__matplotlib-23299/action_history.log#L98)）。这说明 Agent 后续仍尝试围绕 `rc_context` 搜索，但不能把这些 history entry 反写成原 disambiguation event 的 `selected_actions`：该 event 的结构化字段明确是空列表。

最终输出见 [`searcher_matplotlib__matplotlib-23299.json`](../artifacts/common93_runtime_logs/final_outputs/matplotlib__matplotlib-23299/searcher_matplotlib__matplotlib-23299.json)。它包含 `rc_context` 的最终定位结果，但最终输出不是该 event 的 action execution receipt。

**案例结论：** gold 已经在 raw candidates 中且排名第一，但在 candidate → action 转换的 threshold 阶段消失，构成明确的 threshold Gap。

## 2. sympy-13031：非 gold 候选通过，gold 恰好 75 分被排除

### Gold 是什么

官方 patch 的目标节点是 `sympy/matrices/sparse.py` 中 `MutableSparseMatrix.row_join`，patch 行位于该方法内部。因此 gold 是：

```text
sympy/matrices/sparse.py::MutableSparseMatrix::row_join
```

### 日志中的候选和过滤

`search_agent.log` 在 [L119 附近](../artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13031/Orcar.search_agent.log#L119)记录了 `search_callable(query_name=row_join)` 的三个歧义位置：

| Rank | Raw candidate | Score | Threshold 75 | Threshold 后 | 是否生成 action |
|---:|---|---:|---|---|---|
| 1 | `sympy/holonomic/linearsolver.py::NewMatrix::row_join`（非 gold） | 85 | 通过 | 保留 | 是 |
| 2 | `sympy/matrices/sparse.py::MutableSparseMatrix::row_join`（gold） | 75 | 不通过 | 丢弃 | 否 |
| 3 | `sympy/matrices/common.py::MatrixShaping::row_join`（非 gold） | 70 | 不通过 | 丢弃 | 否 |

结构化事件的过滤结果是：

```text
post_threshold_candidates = [sympy/holonomic/linearsolver.py::NewMatrix::row_join]
selected_actions = [
  search_method_in_class(
    class_name=NewMatrix,
    method_name=row_join,
    file_path=sympy/holonomic/linearsolver.py
  )
]
```

所以系统确实生成了一个 action，但它指向 `NewMatrix::row_join`，文件和 class 都与 gold 不同。这个案例不能解释成“没有任何候选通过”；准确描述是：非 gold 候选以 85 分通过，gold 以 75 分被严格 threshold 排除。

这里 `top_k_disambiguation=3`，但由于当前实现的运行时逻辑，事件记录的 `effective_top_k=1`。这仍然不是本案例的主要 drop stage：gold 的 `passed_threshold=false`，在 top-k 之前已经被移除。

### 原始 action history 说明

[`action_history.log` 第 41 行附近](../artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13031/action_history.log#L41)确认了被选中的 action 是 `NewMatrix::row_join`。同一份 history 在后面还记录过 `MutableSparseMatrix::row_join` 的 action request（例如 [L118 附近](../artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13031/action_history.log#L118)），因此这个案例说明的是“初始 disambiguation event 的 candidate-to-action Gap”，不能进一步断言 gold 后续永远没有被再次请求。由于 `action_history` 不是带返回状态的执行 receipt，后续 request 也不能单独证明 action 已成功执行。

最终输出见 [`searcher_sympy__sympy-13031.json`](../artifacts/common93_runtime_logs/final_outputs/sympy__sympy-13031/searcher_sympy__sympy-13031.json)。

**案例结论：** gold 已被召回，但排名第一的非 gold 候选通过 threshold 并生成 action；gold 在 threshold 阶段消失。这是最直观的“错误候选替代 gold”案例。

## 3. sympy-13647：nested helper 的 gold identity 出现多次，全部被过滤

### Gold 是什么

官方 patch 的 node chain 是：

```text
MatrixShaping → _eval_col_insert → entry
```

源码中 `entry` 是 `_eval_col_insert` 内部的 nested helper，patch 对应 `sympy/matrices/common.py` 约 84--89 行。因此需要注意：结构化 candidate 的 canonical representation 只保留了 file/class/function 三层，日志中表现为：

```text
sympy/matrices/common.py::MatrixShaping::entry
```

这几个重复字符串都来自同一 `MatrixShaping` 类下的多个 `entry` 位置，不能仅凭字符串区分 nested helper；gold 身份由 patch node chain 和源码行共同确认，而不是因为“函数名相同”就直接认定。

### 日志中的候选和过滤

`search_agent.log` 在 [L147 附近](../artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13647/Orcar.search_agent.log#L147)记录了 `search_callable(query_name=entry)` 返回 **24 个**可能位置。结构化 scorer 日志的关键分组如下：

| Candidate group | Raw occurrence ranks | Scores | Threshold 75 后 |
|---|---:|---:|---|
| `common.py::MatrixShaping::entry`（gold-consistent nested helper） | 1--4、6、7 | 75、75、75、75、70、60 | 全部丢弃 |
| `common.py::MatrixOperations::entry` | 5、8 | 75、50 | 全部丢弃 |
| `common.py::MatrixSpecial::entry` | 9--14 | 25 | 全部丢弃 |
| `common.py::MatrixArithmetic::entry` | 15--16 | 2 | 全部丢弃 |
| `matrices.py` 下的其他 `entry` | 17--24 | 2 或 0 | 全部丢弃 |

实际结构化状态是：

```text
raw_candidates             = 24 个
post_threshold_candidates  = []
selected_actions           = []
skip_reason                = all_candidates_below_threshold
best gold-consistent score = 75
score_threshold            = 75
effective_top_k            = 1
```

四个 gold-consistent occurrence 的 score 都正好是 75，但当前实现记录为 `passed_threshold=false`；其余 gold-consistent occurrence 得分为 70 和 60。因此没有任何 gold occurrence 进入 threshold 后列表，top-k 没有机会参与选择。

### 原始 action history 说明

在该 query 之前，[`action_history.log` 第 72 行附近](../artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13647/action_history.log#L72)记录了 `MatrixShaping::_eval_col_insert` 的 action；这是前一个 disambiguation event 的结果，不是 `entry` event 的 selected action。随后 `search_agent.log` 才在 [L147 附近](../artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13647/Orcar.search_agent.log#L147)展示 24 个 `entry` 候选。该 `entry` event 的结构化 `selected_actions=[]`，没有生成 `search_method_in_class(... method_name=entry)` 的 precise action。

最终输出见 [`searcher_sympy__sympy-13647.json`](../artifacts/common93_runtime_logs/final_outputs/sympy__sympy-13647/searcher_sympy__sympy-13647.json)。最终定位里出现 parent `_eval_col_insert` 或 trace 中出现 `entry`，都不能替代该 Gap event 中缺失的 exact `entry` action。

**案例结论：** 这是一个 nested helper 和重复 canonical identity 共同出现的复杂案例；但无论采用哪个 gold-consistent occurrence，所有 score 都没有通过 threshold，因此仍然是 threshold Gap，而不是 top-k 或 action generation Gap。

## 共同结论与证据边界

三个案例的共同链路是：

```text
gold 出现在 raw_candidates
        ↓
CodeScorer 给出 score
        ↓
score <= 75（当前实现要求严格 > 75）
        ↓
gold 不在 post_threshold_candidates
        ↓
gold 不在该 event 的 selected_actions
```

因此三例都支持 Candidate-to-Action information loss，且 `gap_by_stage.threshold=3`、`top-k=0`、`action_generation=0`。这只是 event-level 观察，不能直接等价为最终 repair failure。

### 每个案例的原始日志入口

| Instance | Structured event | Search agent | Action history | Final output |
|---|---|---|---|---|
| matplotlib-23299 | [`disambiguation_events.jsonl#L5`](../artifacts/common93_candidate_action_gap/disambiguation_events.jsonl#L5) | [`Orcar.search_agent.log`](../artifacts/common93_runtime_logs/primary_runtime_logs/matplotlib__matplotlib-23299/Orcar.search_agent.log) | [`action_history.log`](../artifacts/common93_runtime_logs/primary_runtime_logs/matplotlib__matplotlib-23299/action_history.log) | [`searcher_*.json`](../artifacts/common93_runtime_logs/final_outputs/matplotlib__matplotlib-23299/searcher_matplotlib__matplotlib-23299.json) |
| sympy-13031 | [`disambiguation_events.jsonl#L12`](../artifacts/common93_candidate_action_gap/disambiguation_events.jsonl#L12) | [`Orcar.search_agent.log`](../artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13031/Orcar.search_agent.log) | [`action_history.log`](../artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13031/action_history.log) | [`searcher_*.json`](../artifacts/common93_runtime_logs/final_outputs/sympy__sympy-13031/searcher_sympy__sympy-13031.json) |
| sympy-13647 | [`disambiguation_events.jsonl#L16`](../artifacts/common93_candidate_action_gap/disambiguation_events.jsonl#L16) | [`Orcar.search_agent.log`](../artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13647/Orcar.search_agent.log) | [`action_history.log`](../artifacts/common93_runtime_logs/primary_runtime_logs/sympy__sympy-13647/action_history.log) | [`searcher_*.json`](../artifacts/common93_runtime_logs/final_outputs/sympy__sympy-13647/searcher_sympy__sympy-13647.json) |

其中结构化 event log 是分数与过滤状态的权威来源；原始 `search_agent` 和 `action_history` 用于还原 Agent 看到的歧义候选和 action history，不把自由文本日志误读成工具成功回执。
