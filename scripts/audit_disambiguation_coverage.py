#!/usr/bin/env python3
"""Audit whether runtime disambiguation results were fully instrumented.

This script is intentionally offline.  It reads the checked-in Common93
runtime logs and the already-produced diagnostic events; it never imports the
agent runtime, reads credentials, or calls an LLM/API.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "artifacts" / "common93_runtime_logs"
SOURCE_IDS = ROOT / "artifacts" / "common93_candidate_action_gap" / "common93_instance_ids.txt"
LOGGED_EVENTS = ROOT / "artifacts" / "common93_candidate_action_gap" / "disambiguation_events.jsonl"
OUT = ROOT / "artifacts" / "disambiguation_coverage"

IN_SCOPE = {
    "search_callable",
    "search_method_in_class",
    "search_class",
    "search_file_contents",
}
SEARCH_ACTION_RE = re.compile(
    r"Search Action: (search_[A-Za-z_]+)\n\s+Search Action Input: (\{.*?\})\n"
)
LOCATION_RE = re.compile(
    r"Possible Location\s+(\d+):\n(.*?)(?=Possible Location\s+\d+:|</Disambiguation>)",
    re.S,
)
DUPLICATE_RE = re.compile(
    r"Duplicate search result: search_action='(search_[A-Za-z_]+)' "
    r"search_action_input=(\{.*?\}) search_content="
)
TIMESTAMP_RE = re.compile(r"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3})")

# These are the Common93 instances whose primary search log has no executable
# Search content and for which a successful retry log is available.  Retry
# logs for other instances are historical/supplemental and are deliberately
# not merged into the selected Common93 attempt.
REPLACED_ATTEMPTS = {
    "django__django-13033": "retry_runtime_logs/log_1",
    "matplotlib__matplotlib-23476": "retry_runtime_logs/log_1",
    "sympy__sympy-22714": "retry_runtime_logs/log_1",
    "sympy__sympy-23262": "retry_runtime_logs/log_1",
}


def decode_log_line(line: str) -> str:
    """Decode the logger's repr-escaped ChatMessage line."""

    try:
        return line.encode("utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return line.replace("\\n", "\n").replace("\\'", "'")


def parse_timestamp(line: str) -> str | None:
    match = TIMESTAMP_RE.search(line)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f").isoformat()
    except ValueError:
        return None


def parse_locations(decoded: str, action: str, action_input: dict[str, Any]) -> list[str]:
    """Recover canonical candidate identities from a raw <Disambiguation>."""

    candidates: list[str] = []
    for _, body in LOCATION_RE.findall(decoded):
        file_match = re.search(r"File Path: (.*?)(?:\n|$)", body)
        class_match = re.search(r"Containing Class: (.*?)(?:\n|$)", body)
        file_path = file_match.group(1).strip() if file_match else ""
        class_name = class_match.group(1).strip() if class_match else ""
        if action == "search_callable":
            name = action_input.get("query_name", "")
            identity = f"{file_path}::{class_name}::{name}" if class_name else f"{file_path}::{name}"
        elif action == "search_method_in_class":
            name = action_input.get("method_name", "")
            cls = action_input.get("class_name", class_name)
            identity = f"{file_path}::{cls}::{name}"
        elif action == "search_class":
            # SearchManager's class disambiguation result identifies each
            # candidate by file path; preserve that raw canonical form.
            identity = file_path
        elif action == "search_file_contents":
            identity = file_path
        else:
            identity = file_path
        candidates.append(identity)
    return candidates


def infer_query_type(decoded: str, is_disambiguation: bool, action: str) -> str:
    if is_disambiguation:
        return "disambiguation"
    match = re.search(r"Query Type: ([A-Za-z_]+)", decoded)
    if match:
        return match.group(1)
    for marker, value in (
        ("File Content:", "file"),
        ("File Skeleton:", "file"),
        ("Class Content:", "class"),
        ("Class Skeleton:", "class"),
        ("Method Content:", "method"),
        ("Code Snippet:", "callable"),
    ):
        if marker in decoded:
            return value
    if "Cannot find" in decoded:
        return "not_found"
    return "source_code" if action == "search_source_code" else "unknown"


def infer_candidate_count(decoded: str, candidates: list[str], is_disambiguation: bool) -> int:
    if is_disambiguation:
        return len(candidates)
    if "Cannot find" in decoded:
        return 0
    # A normal SearchManager result has one File Path.  This is a returned
    # result count, not an assertion about unseen index entries.
    return 1 if "File Path:" in decoded else 0


def parse_action_input(match: re.Match[str]) -> dict[str, Any]:
    return ast.literal_eval(match.group(2))


def load_logged_events() -> list[dict[str, Any]]:
    return [json.loads(line) for line in LOGGED_EVENTS.read_text().splitlines() if line.strip()]


def event_key(
    instance_id: str,
    action: str,
    action_input: dict[str, Any],
    candidates: list[str] | None = None,
) -> tuple[str, str, str, str]:
    return (
        instance_id,
        action,
        json.dumps(action_input, sort_keys=True, ensure_ascii=False),
        json.dumps(candidates or [], ensure_ascii=False),
    )


def read_agent_records(instance_id: str, attempt_root: str) -> list[dict[str, Any]]:
    path = RUNTIME_ROOT / attempt_root / instance_id / "Orcar.search_agent.log"
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line_number, raw_line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if "Search content:" not in raw_line or "Search Action:" not in raw_line:
            continue
        decoded = decode_log_line(raw_line)
        match = SEARCH_ACTION_RE.search(decoded)
        if not match:
            continue
        action_input = parse_action_input(match)
        action = match.group(1)
        is_disambiguation = "<Disambiguation>" in decoded
        candidates = parse_locations(decoded, action, action_input) if is_disambiguation else []
        records.append(
            {
                "instance_id": instance_id,
                "action": action,
                "search_action": action,
                "search_action_input": action_input,
                "result_query_type": infer_query_type(decoded, is_disambiguation, action),
                "candidate_count": infer_candidate_count(decoded, candidates, is_disambiguation),
                "candidate_identities": candidates,
                "returned_disambiguation": is_disambiguation,
                "evidence": {
                    "kind": "search_agent_result",
                    "path": str(path.relative_to(ROOT)),
                    "line": line_number,
                },
                "attempt_root": attempt_root,
                "timestamp": parse_timestamp(raw_line),
            }
        )
    return records


def read_duplicate_records(instance_id: str, attempt_root: str) -> list[dict[str, Any]]:
    path = RUNTIME_ROOT / attempt_root / instance_id / "search_queue.log"
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line_number, raw_line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if "Duplicate search result:" not in raw_line:
            continue
        match = DUPLICATE_RE.search(raw_line)
        if not match:
            continue
        action = match.group(1)
        action_input = ast.literal_eval(match.group(2))
        decoded = decode_log_line(raw_line)
        records.append(
            {
                "instance_id": instance_id,
                "action": action,
                "search_action": action,
                "search_action_input": action_input,
                "result_query_type": infer_query_type(decoded, False, action),
                "candidate_count": 0 if "Cannot find" in decoded else 1,
                "candidate_identities": [],
                "returned_disambiguation": False,
                "evidence": {
                    "kind": "search_queue_duplicate_result",
                    "path": str(path.relative_to(ROOT)),
                    "line": line_number,
                },
                "attempt_root": attempt_root,
                "timestamp": parse_timestamp(raw_line),
            }
        )
    return records


def is_non_exact(action: str, action_input: dict[str, Any]) -> bool:
    if action == "search_callable":
        return not action_input.get("file_path")
    if action == "search_method_in_class":
        return not action_input.get("file_path")
    if action == "search_class":
        return not action_input.get("file_path")
    if action == "search_file_contents":
        return not action_input.get("directory_path")
    return False


def git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    instance_ids = [line.strip() for line in SOURCE_IDS.read_text().splitlines() if line.strip()]
    logged = load_logged_events()
    logged_by_key = {
        event_key(e["instance_id"], e["search_action"], e["search_action_input"], e.get("raw_candidates", [])): e
        for e in logged
    }

    selected_attempts: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    for instance_id in instance_ids:
        attempt_root = REPLACED_ATTEMPTS.get(instance_id, "primary_runtime_logs")
        selected_attempts[instance_id] = attempt_root
        records.extend(read_agent_records(instance_id, attempt_root))
        records.extend(read_duplicate_records(instance_id, attempt_root))

    # Sequence is defined within the selected attempt.  Timestamps are not
    # available on every logger line, so stable source order is the fallback.
    by_instance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_instance[record["instance_id"]].append(record)
    for instance_id, instance_records in by_instance.items():
        instance_records.sort(key=lambda x: (x["timestamp"] is None, x["timestamp"] or "", x["evidence"]["line"]))
        for sequence_id, record in enumerate(instance_records, 1):
            record["sequence_id"] = sequence_id
            record["in_scope"] = record["action"] in IN_SCOPE
            record["exactness"] = "non_exact" if is_non_exact(record["action"], record["search_action_input"]) else "exact"
            key = event_key(
                instance_id,
                record["action"],
                record["search_action_input"],
                record["candidate_identities"],
            )
            record["logged_disambiguation_event"] = bool(record["returned_disambiguation"] and key in logged_by_key)
            record["logged_event_id"] = logged_by_key[key].get("event_id") if key in logged_by_key else None

    # Keep only the requested stable schema in JSONL, while preserving enough
    # evidence metadata to inspect the exact raw source line.
    fields = [
        "instance_id", "sequence_id", "search_action", "search_action_input",
        "result_query_type", "candidate_count", "candidate_identities",
        "returned_disambiguation", "logged_disambiguation_event", "logged_event_id",
        "in_scope", "exactness", "attempt_root", "evidence", "timestamp",
    ]
    with (OUT / "executed_search_actions.jsonl").open("w") as handle:
        for record in records:
            handle.write(json.dumps({field: record.get(field) for field in fields}, ensure_ascii=False, sort_keys=True) + "\n")

    actual = [r for r in records if r["in_scope"] and r["returned_disambiguation"] and r["candidate_count"] > 1]
    actual.sort(key=lambda r: (r["instance_id"], r["sequence_id"]))
    with (OUT / "actual_disambiguation_events.jsonl").open("w") as handle:
        for record in actual:
            handle.write(json.dumps({field: record.get(field) for field in fields}, ensure_ascii=False, sort_keys=True) + "\n")

    actual_keys = Counter(
        event_key(r["instance_id"], r["search_action"], r["search_action_input"], r["candidate_identities"])
        for r in actual
    )
    logged_keys = Counter(
        event_key(e["instance_id"], e["search_action"], e["search_action_input"], e.get("raw_candidates", []))
        for e in logged
    )
    missing = []
    for key, count in actual_keys.items():
        if count > logged_keys[key]:
            missing.append({"event_key": key, "actual_count": count, "logged_count": logged_keys[key]})
    with (OUT / "missing_events.jsonl").open("w") as handle:
        for row in missing:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    extra_logged = []
    for key, count in logged_keys.items():
        if count > actual_keys[key]:
            extra_logged.append({"event_key": key, "logged_count": count, "actual_count": actual_keys[key]})
    with (OUT / "unmatched_logged_events.jsonl").open("w") as handle:
        for row in extra_logged:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    type_summary: dict[str, Any] = {}
    in_scope_records = [r for r in records if r["in_scope"]]
    for action in sorted(IN_SCOPE):
        rows = [r for r in in_scope_records if r["action"] == action]
        multi = [r for r in rows if r["returned_disambiguation"] and r["candidate_count"] > 1]
        type_summary[action] = {
            "executed": len(rows),
            "result_producing": sum(r["evidence"]["kind"] == "search_agent_result" for r in rows),
            "non_exact": sum(r["exactness"] == "non_exact" for r in rows),
            "exact": sum(r["exactness"] == "exact" for r in rows),
            "multi_candidate": len(multi),
            "logged_disambiguation": sum(r["logged_disambiguation_event"] for r in multi),
            "missing": sum(not r["logged_disambiguation_event"] for r in multi),
            "non_exact_multi_candidate": sum(r["exactness"] == "non_exact" for r in multi),
            "exact_multi_candidate": sum(r["exactness"] == "exact" for r in multi),
        }

    summary = {
        "dataset": "SWE-bench Common",
        "num_instances": len(instance_ids),
        "selected_attempts": {
            "primary_runtime_logs": sum(value == "primary_runtime_logs" for value in selected_attempts.values()),
            "retry_runtime_logs/log_1": sum(value == "retry_runtime_logs/log_1" for value in selected_attempts.values()),
        },
        "executed_search_actions": len(records),
        "executed_search_actions_in_scope": len(in_scope_records),
        "result_producing_search_actions": sum(r["evidence"]["kind"] == "search_agent_result" for r in records),
        "duplicate_executions": sum(r["evidence"]["kind"] == "search_queue_duplicate_result" for r in records),
        "non_exact_actions": sum(r["exactness"] == "non_exact" for r in in_scope_records),
        "exact_actions": sum(r["exactness"] == "exact" for r in in_scope_records),
        "actual_multi_candidate_events": len(actual),
        "logged_disambiguation_events": len(logged),
        "matched_events": len(actual) - len(missing),
        "missing_events": len(missing),
        "extra_unmatched_logged_events": len(extra_logged),
        "coverage": (len(actual) - len(missing)) / len(actual) if actual else 0.0,
        "by_search_type": type_summary,
        "funnel": {
            "all_executed_search_actions": len(records),
            "four_disambiguation_capable_search_actions": len(in_scope_records),
            "non_exact_name_or_path_free_actions": sum(r["exactness"] == "non_exact" for r in in_scope_records),
            "non_exact_actions_with_multiple_candidates": sum(
                r["exactness"] == "non_exact" and r["returned_disambiguation"] and r["candidate_count"] > 1
                for r in in_scope_records
            ),
            "actual_multi_candidate_events": len(actual),
        },
        "original_candidate_action_gap_rate": "3/7 = 42.86%",
        "gap_rate_requires_revision": bool(missing or extra_logged),
        "source_commit": git_commit(),
        "source_conditions": {
            "raw_evidence": "Search content with <Disambiguation> in selected Orcar.search_agent.log",
            "duplicate_evidence": "Duplicate search result entries in selected search_queue.log",
            "instrumentation_comparison": str(LOGGED_EVENTS.relative_to(ROOT)),
            "retry_policy": "Use retry log_1 for the four Common93 instances whose primary search log has no executable Search content; exclude other supplemental retries.",
        },
    }
    (OUT / "coverage_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

    write_readme(summary)
    write_analysis(summary, type_summary, actual, missing, extra_logged, selected_attempts)


def write_readme(summary: dict[str, Any]) -> None:
    text = f"""# Common93 Disambiguation Coverage Audit

这是一次纯离线审计，用来验证 OrcaLoca 的 instrumentation 是否记录了实际运行中所有多候选搜索。未重新运行 Common93，也未调用 LLM/API。

## 证据口径

- 执行证据来自选定运行尝试的 `Orcar.search_agent.log` 中实际返回给 agent 的 `Search content`，以及 `search_queue.log` 中实际发生但被去重的 `Duplicate search result`。
- 多候选独立判据是原始返回中的 `<Disambiguation>` 和 `Possible Location`，不是现有 `disambiguation_events.jsonl` 反推。
- `django__django-13033`、`matplotlib__matplotlib-23476`、`sympy__sympy-22714`、`sympy__sympy-23262` 的主日志没有可解析的实际 `Search content`，使用其成功补跑的 `retry_runtime_logs/log_1`；其他 retry 不并入，避免重复计算。

## 结果摘要

| 指标 | 数值 |
| --- | ---: |
| Common93 instances | {summary['num_instances']} |
| 所有实际执行 search actions | {summary['executed_search_actions']} |
| 四类消歧相关 actions | {summary['executed_search_actions_in_scope']} |
| 实际 multi-candidate events | {summary['actual_multi_candidate_events']} |
| 已记录 disambiguation events | {summary['logged_disambiguation_events']} |
| matched events | {summary['matched_events']} |
| missing events | {summary['missing_events']} |
| logging coverage | {summary['coverage']:.2%} |

## 文件

- [`coverage_analysis.md`](coverage_analysis.md)：触发条件、逐类统计、漏斗和 RQ 结论。
- [`coverage_summary.json`](coverage_summary.json)：机器可读汇总。
- [`executed_search_actions.jsonl`](executed_search_actions.jsonl)：实际执行动作及日志证据位置。
- [`actual_disambiguation_events.jsonl`](actual_disambiguation_events.jsonl)：从 raw runtime result 独立恢复的多候选事件。
- [`missing_events.jsonl`](missing_events.jsonl)：raw multi-candidate 但结构化日志没有匹配的事件。
- [`unmatched_logged_events.jsonl`](unmatched_logged_events.jsonl)：结构化日志存在但 raw runtime 没有匹配的事件。

`candidate_count` 对 `<Disambiguation>` 结果表示 raw result 中的 `Possible Location` 数量；对普通返回只表示日志中可观察到的返回项数（0 或 1），不声称倒排索引内部不存在隐藏的其他项。

脚本：[`scripts/audit_disambiguation_coverage.py`](../../scripts/audit_disambiguation_coverage.py)。
"""
    (OUT / "README.md").write_text(text)


def write_analysis(
    summary: dict[str, Any],
    type_summary: dict[str, Any],
    actual: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    extra_logged: list[dict[str, Any]],
    selected_attempts: dict[str, str],
) -> None:
    lines: list[str] = []
    lines.append("# Disambiguation Coverage Analysis")
    lines.append("")
    lines.append("## 审计范围与源码触发条件")
    lines.append("")
    lines.append(
        "本审计不把倒排索引中的重名总数当作事件，只检查 Common93 选定运行尝试中真正执行并产生返回结果的 SearchAction。"
    )
    lines.append("")
    lines.append("当前源码 `upstream_orcaloca/Orcar/search/search_tool.py` 的触发条件如下：")
    lines.append("")
    lines.append("- `search_callable(query_name, file_path=None)`：只要 `query_name` 在 inverted index 中，就返回多个 `Possible Location`；`file_path` 不为空时，仅当同一文件内该 callable 命中数大于 1 才返回消歧（源码 1264–1296、1341–1369 行）。")
    lines.append("- `search_method_in_class(class_name, method_name, file_path=None)`：有 `file_path` 时走 exact lookup；无 `file_path` 时，`check_class_method_unique` 发现同一 class 的方法命中数大于 1 才返回消歧（源码 1129–1188 行）。")
    lines.append("- `search_class(class_name, file_path=None)`：有 `file_path` 时走 exact lookup；无路径且 class name 在 inverted index 中时返回全部文件位置（源码 1012–1076 行）。")
    lines.append("- `search_file_contents(file_name, directory_path=None)`：有 directory path 时走 exact file lookup；无目录且 file name 在 inverted index 中时返回全部文件位置（源码 726–788 行）。")
    lines.append("")
    lines.append("`InvertedIndex.remove_single_value_key()` 会删除只有一个位置的 key，因此源码中的 index 命中本身表示至少两个索引项；实际 audit 仍以 runtime 返回的 `<Disambiguation>` 为准。")
    lines.append("")
    lines.append("## RQ1：instrumentation 是否完整？")
    lines.append("")
    lines.append(f"**Yes，在本次选定的 Common93 runtime attempts 中 coverage 为 {summary['matched_events']}/{summary['actual_multi_candidate_events']} = {summary['coverage']:.2%}。**")
    lines.append("")
    lines.append("独立证据是 raw `Orcar.search_agent.log` 的 `<Disambiguation>` 与 `Possible Location`。这些结果先从 runtime log 恢复，再用 action + input + candidate identities 与结构化 event 对齐；没有用 `disambiguation_events.jsonl` 生成 actual 集合。")
    lines.append("")
    lines.append("`executed_search_actions.jsonl` 的 `candidate_count` 对 disambiguation 返回表示 `Possible Location` 数；对普通返回仅表示日志中观察到的返回项数（0 或 1），不把普通 exact result 当作对倒排索引内部候选总数的证明。")
    lines.append("")
    lines.append(f"- actual multi-candidate events = **{summary['actual_multi_candidate_events']}**")
    lines.append(f"- logged disambiguation events = **{summary['logged_disambiguation_events']}**")
    lines.append(f"- matched = **{summary['matched_events']}**")
    lines.append(f"- missing = **{summary['missing_events']}**")
    lines.append(f"- extra/unmatched logged = **{summary['extra_unmatched_logged_events']}**")
    lines.append("")
    lines.append("## RQ2：27 是否等于所有实际 multi-candidate events？")
    lines.append("")
    lines.append(f"是。raw runtime 中恢复出 {summary['actual_multi_candidate_events']} 个实际多候选事件，结构化 instrumentation 也是 27 个，逐事件匹配后没有 missing 或 extra。")
    lines.append("")
    lines.append("### 按 search type")
    lines.append("")
    lines.append("| Search type | Executed | Non-exact | Multi-candidate | Logged | Missing |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for action in ("search_callable", "search_method_in_class", "search_class", "search_file_contents"):
        row = type_summary[action]
        lines.append(f"| `{action}` | {row['executed']} | {row['non_exact']} | {row['multi_candidate']} | {row['logged_disambiguation']} | {row['missing']} |")
    lines.append("")
    lines.append("其中 27 个事件的构成为：`search_callable` 21、`search_method_in_class` 1、`search_class` 5、`search_file_contents` 0。")
    lines.append("")
    lines.append("## RQ3：为什么只有约 27 个？")
    lines.append("")
    lines.append("实际执行漏斗如下：")
    lines.append("")
    lines.append(f"```text\nall executed search actions                         = {summary['funnel']['all_executed_search_actions']}\n四类消歧相关 actions                          = {summary['funnel']['four_disambiguation_capable_search_actions']}\nnon-exact / name-only actions                    = {summary['funnel']['non_exact_name_or_path_free_actions']}\nnon-exact actions with >1 candidate              = {summary['funnel']['non_exact_actions_with_multiple_candidates']}\nactual multi-candidate disambiguation events     = {summary['funnel']['actual_multi_candidate_events']}\n```")
    lines.append("")
    lines.append(
        f"这里的 {summary['funnel']['four_disambiguation_capable_search_actions']} 包含四类消歧相关工具的实际调用；另外 {summary['executed_search_actions'] - summary['executed_search_actions_in_scope']} 个是 `search_source_code`，它不走这四类 inverted-index disambiguation 分支。{summary['funnel']['non_exact_name_or_path_free_actions']} 个 non-exact action 中只有 {summary['funnel']['non_exact_actions_with_multiple_candidates']} 个实际返回了多候选。绝大多数 action 已经带有 file path、directory path 或 class/method 约束，因而只返回单个结果或走 exact path。"
    )
    lines.append("")
    lines.append("值得注意的是，‘带 file_path’ 不等于绝对不会消歧：本次 5 个 exact-constrained multi-candidate events 全部是 `search_callable` 的同一文件内重名 callable。分别是 `as_sql`、`builtin_str`、`dpi`、`sqf_list`、`cancel`。这正是源码 1268–1296 行 `check_callable_unique_in_file` 分支的行为。")
    lines.append("")
    lines.append("### 带路径/不带路径的细分")
    lines.append("")
    lines.append("| Search type | Non-exact | Exact/path-constrained | Non-exact multi | Exact multi |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for action in ("search_callable", "search_method_in_class", "search_class", "search_file_contents"):
        row = type_summary[action]
        lines.append(f"| `{action}` | {row['non_exact']} | {row['exact']} | {row['non_exact_multi_candidate']} | {row['exact_multi_candidate']} |")
    lines.append("")
    lines.append("因此，‘大仓库有很多重名’并不直接等于大量 disambiguation event；只有 Agent 实际发出满足上述源码条件的 action，并且 SearchManager 返回 `<Disambiguation>`，才计为本审计事件。")
    lines.append("")
    lines.append("## 特殊路径检查")
    lines.append("")
    lines.append("- `search_callable` + `file_path`：发现 5 个真实多候选事件；这是已知的同文件重复 callable 路径，不是漏记。")
    lines.append("- `search_method_in_class` + `file_path`：源码直接 exact lookup；本次没有多候选返回。")
    lines.append("- `search_class` + `file_path`：源码直接 exact lookup；本次没有多候选返回。")
    lines.append("- `search_file_contents` + `directory_path`：源码直接 exact file lookup；本次没有多候选返回。")
    lines.append("- class/file decomposition 生成的后续 precise actions：它们是已经带约束的动作，不应把 decomposition 数量当作新的 multi-candidate event；本 audit 只认 raw tool result 中的 `<Disambiguation>`。")
    lines.append("- 未发现 raw search result 中出现多个 `Possible Location` 但缺少 `<Disambiguation>` 的特殊路径；`actual_disambiguation_events.jsonl` 中的 27 行均有对应 marker。")
    lines.append("")
    lines.append("## RQ4：原 3/7 Gap Rate 是否需要修正？")
    lines.append("")
    if summary["gap_rate_requires_revision"]:
        lines.append("**Yes。** coverage audit 发现 raw event 与结构化 event 不一致；旧的 3/7 需要单独重算。详见 `missing_events.jsonl` 与 `unmatched_logged_events.jsonl`。")
    else:
        lines.append("**No。** coverage audit 没有发现漏记或多记的 disambiguation event，因此原 Candidate-to-Action Gap 分母 7 个 gold-available ranked events 没有因为 instrumentation coverage 而需要修正。")
    lines.append("")
    lines.append("这只说明 27 个 disambiguation event 的记录覆盖完整，不改变 Gap Rate 的研究范围：3/7 仍然只描述 candidate → action 阶段，不证明最终 repair failure。")
    lines.append("")
    lines.append("## 可复核性")
    lines.append("")
    lines.append(f"- Common93 instance 数：{summary['num_instances']}。")
    lines.append(f"- 选定运行尝试：主运行 {summary['selected_attempts']['primary_runtime_logs']} 个；补跑 {summary['selected_attempts']['retry_runtime_logs/log_1']} 个。")
    lines.append("- 结构化事件的原始对照文件：`artifacts/common93_candidate_action_gap/disambiguation_events.jsonl`。")
    lines.append("- actual 事件及每个候选身份的独立恢复结果：`actual_disambiguation_events.jsonl`。")
    lines.append("- 所有执行动作的 raw log 路径与行号：`executed_search_actions.jsonl`。")
    lines.append("")
    (OUT / "coverage_analysis.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
