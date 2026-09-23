# Disambiguation Coverage Analysis

## 审计范围与源码触发条件

本审计不把倒排索引中的重名总数当作事件，只检查 Common93 选定运行尝试中真正执行并产生返回结果的 SearchAction。

当前源码 `upstream_orcaloca/Orcar/search/search_tool.py` 的触发条件如下：

- `search_callable(query_name, file_path=None)`：只要 `query_name` 在 inverted index 中，就返回多个 `Possible Location`；`file_path` 不为空时，仅当同一文件内该 callable 命中数大于 1 才返回消歧（源码 1264–1296、1341–1369 行）。
- `search_method_in_class(class_name, method_name, file_path=None)`：有 `file_path` 时走 exact lookup；无 `file_path` 时，`check_class_method_unique` 发现同一 class 的方法命中数大于 1 才返回消歧（源码 1129–1188 行）。
- `search_class(class_name, file_path=None)`：有 `file_path` 时走 exact lookup；无路径且 class name 在 inverted index 中时返回全部文件位置（源码 1012–1076 行）。
- `search_file_contents(file_name, directory_path=None)`：有 directory path 时走 exact file lookup；无目录且 file name 在 inverted index 中时返回全部文件位置（源码 726–788 行）。

`InvertedIndex.remove_single_value_key()` 会删除只有一个位置的 key，因此源码中的 index 命中本身表示至少两个索引项；实际 audit 仍以 runtime 返回的 `<Disambiguation>` 为准。

## RQ1：instrumentation 是否完整？

**Yes，在本次选定的 Common93 runtime attempts 中 coverage 为 27/27 = 100.00%。**

独立证据是 raw `Orcar.search_agent.log` 的 `<Disambiguation>` 与 `Possible Location`。这些结果先从 runtime log 恢复，再用 action + input + candidate identities 与结构化 event 对齐；没有用 `disambiguation_events.jsonl` 生成 actual 集合。

`executed_search_actions.jsonl` 的 `candidate_count` 对 disambiguation 返回表示 `Possible Location` 数；对普通返回仅表示日志中观察到的返回项数（0 或 1），不把普通 exact result 当作对倒排索引内部候选总数的证明。

- actual multi-candidate events = **27**
- logged disambiguation events = **27**
- matched = **27**
- missing = **0**
- extra/unmatched logged = **0**

## RQ2：27 是否等于所有实际 multi-candidate events？

是。raw runtime 中恢复出 27 个实际多候选事件，结构化 instrumentation 也是 27 个，逐事件匹配后没有 missing 或 extra。

### 按 search type

| Search type | Executed | Non-exact | Multi-candidate | Logged | Missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| `search_callable` | 147 | 61 | 21 | 21 | 0 |
| `search_method_in_class` | 216 | 45 | 1 | 1 | 0 |
| `search_class` | 91 | 49 | 5 | 5 | 0 |
| `search_file_contents` | 160 | 1 | 0 | 0 | 0 |

其中 27 个事件的构成为：`search_callable` 21、`search_method_in_class` 1、`search_class` 5、`search_file_contents` 0。

## RQ3：为什么只有约 27 个？

实际执行漏斗如下：

```text
all executed search actions                         = 639
四类消歧相关 actions                          = 614
non-exact / name-only actions                    = 156
non-exact actions with >1 candidate              = 22
actual multi-candidate disambiguation events     = 27
```

这里的 614 包含四类消歧相关工具的实际调用；另外 25 个是 `search_source_code`，它不走这四类 inverted-index disambiguation 分支。156 个 non-exact action 中只有 22 个实际返回了多候选。绝大多数 action 已经带有 file path、directory path 或 class/method 约束，因而只返回单个结果或走 exact path。

值得注意的是，‘带 file_path’ 不等于绝对不会消歧：本次 5 个 exact-constrained multi-candidate events 全部是 `search_callable` 的同一文件内重名 callable。分别是 `as_sql`、`builtin_str`、`dpi`、`sqf_list`、`cancel`。这正是源码 1268–1296 行 `check_callable_unique_in_file` 分支的行为。

### 带路径/不带路径的细分

| Search type | Non-exact | Exact/path-constrained | Non-exact multi | Exact multi |
| --- | ---: | ---: | ---: | ---: |
| `search_callable` | 61 | 86 | 16 | 5 |
| `search_method_in_class` | 45 | 171 | 1 | 0 |
| `search_class` | 49 | 42 | 5 | 0 |
| `search_file_contents` | 1 | 159 | 0 | 0 |

因此，‘大仓库有很多重名’并不直接等于大量 disambiguation event；只有 Agent 实际发出满足上述源码条件的 action，并且 SearchManager 返回 `<Disambiguation>`，才计为本审计事件。

## 特殊路径检查

- `search_callable` + `file_path`：发现 5 个真实多候选事件；这是已知的同文件重复 callable 路径，不是漏记。
- `search_method_in_class` + `file_path`：源码直接 exact lookup；本次没有多候选返回。
- `search_class` + `file_path`：源码直接 exact lookup；本次没有多候选返回。
- `search_file_contents` + `directory_path`：源码直接 exact file lookup；本次没有多候选返回。
- class/file decomposition 生成的后续 precise actions：它们是已经带约束的动作，不应把 decomposition 数量当作新的 multi-candidate event；本 audit 只认 raw tool result 中的 `<Disambiguation>`。
- 未发现 raw search result 中出现多个 `Possible Location` 但缺少 `<Disambiguation>` 的特殊路径；`actual_disambiguation_events.jsonl` 中的 27 行均有对应 marker。

## RQ4：原 3/7 Gap Rate 是否需要修正？

**No。** coverage audit 没有发现漏记或多记的 disambiguation event，因此原 Candidate-to-Action Gap 分母 7 个 gold-available ranked events 没有因为 instrumentation coverage 而需要修正。

这只说明 27 个 disambiguation event 的记录覆盖完整，不改变 Gap Rate 的研究范围：3/7 仍然只描述 candidate → action 阶段，不证明最终 repair failure。

## 可复核性

- Common93 instance 数：93。
- 选定运行尝试：主运行 89 个；补跑 4 个。
- 结构化事件的原始对照文件：`artifacts/common93_candidate_action_gap/disambiguation_events.jsonl`。
- actual 事件及每个候选身份的独立恢复结果：`actual_disambiguation_events.jsonl`。
- 所有执行动作的 raw log 路径与行号：`executed_search_actions.jsonl`。

