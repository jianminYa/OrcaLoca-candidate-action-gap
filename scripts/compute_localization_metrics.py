"""Compute OrcaLoca file/function localization metrics offline.

This intentionally mirrors ``upstream_orcaloca/artifact/parse_output.py``:

* File Match means every patch-derived gold file is present in ``bug_locations``.
* Function Match means every patch-derived gold function entity is present in
  the normalized predicted function set.
* Mean precision is computed per instance as gold/predicted intersection over
  predicted entities, with an empty prediction receiving precision 1.0, as in
  the upstream parser.

No model or API call is made by this script.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


def canonical_file(value: Any) -> str:
    """Normalize repository-relative paths for gold/prediction comparison."""

    path = str(value or "").replace("\\", "/")
    while path.startswith("/"):
        path = path[1:]
    return path


def load_ids(path: Path) -> List[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def gold_sets(row: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
    """Build the same file/function sets used by upstream parse_output.py."""

    files: Set[str] = set()
    functions: Set[str] = set()
    parsed_patch = row.get("parsed_patch") or {}
    for diff_loc in parsed_patch.get("diff_locs", []):
        file_path = canonical_file(diff_loc.get("file"))
        if file_path:
            files.add(file_path)

        diff_nodes = diff_loc.get("diff_nodes", [])
        if not diff_nodes:
            continue

        function_name = file_path + ":" + str(diff_nodes[0].get("node_name", ""))
        if (
            len(diff_nodes) > 1
            and diff_nodes[0].get("node_type") == "ClassDef"
            and diff_nodes[1].get("node_type") == "FunctionDef"
        ):
            function_name += "." + str(diff_nodes[1].get("node_name", ""))
        elif len(diff_nodes) > 1 and diff_nodes[0].get("node_type") != "FunctionDef":
            # Preserve the upstream parser's handling of an unsupported
            # multi-level diff location.
            continue
        functions.add(function_name)
    return files, functions


def predicted_sets(output: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
    """Convert searcher bug_locations into upstream-compatible sets."""

    files: Set[str] = set()
    functions: Set[str] = set()
    for location in output.get("bug_locations", []) or []:
        if not isinstance(location, dict):
            continue
        file_path = canonical_file(location.get("file_path"))
        class_name = str(location.get("class_name") or "")
        method_name = str(location.get("method_name") or "")
        if file_path:
            files.add(file_path)

        if not class_name and not method_name:
            continue
        if not class_name:
            functions.add(file_path + ":" + method_name)
        elif not method_name:
            functions.add(file_path + ":" + class_name)
        else:
            functions.add(file_path + ":" + class_name)
            functions.add(file_path + ":" + class_name + "." + method_name)
    return files, functions


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def population_std(values: Iterable[float]) -> float:
    values = list(values)
    if not values:
        return 0.0
    average = mean(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / len(values))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-dir", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    ids = load_ids(args.gold_dir / "common93_instance_ids.txt")
    gold: Dict[str, Dict[str, Any]] = json.loads(
        (args.gold_dir / "gold_entities.json").read_text(encoding="utf-8")
    )

    details: List[Dict[str, Any]] = []
    file_precisions: List[float] = []
    function_precisions: List[float] = []
    function_precisions_evaluable: List[float] = []
    file_matches = 0
    file_any_hits = 0
    function_matches = 0
    function_matches_evaluable = 0
    function_any_hits_evaluable = 0
    function_evaluable_instances = 0
    missing_outputs: List[str] = []
    invalid_outputs: List[str] = []

    for instance_id in ids:
        gold_files, gold_functions = gold_sets(gold[instance_id])
        output_path = (
            args.runtime_dir
            / "final_outputs"
            / instance_id
            / f"searcher_{instance_id}.json"
        )
        status = "valid"
        predicted_files: Set[str] = set()
        predicted_functions: Set[str] = set()
        if not output_path.is_file():
            status = "missing"
            missing_outputs.append(instance_id)
        else:
            try:
                output = json.loads(output_path.read_text(encoding="utf-8"))
                if not isinstance(output, dict) or "bug_locations" not in output:
                    raise ValueError("missing bug_locations")
                predicted_files, predicted_functions = predicted_sets(output)
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                status = "invalid"
                invalid_outputs.append(instance_id)

        file_intersection = gold_files & predicted_files
        function_intersection = gold_functions & predicted_functions
        file_precision = len(file_intersection) / len(predicted_files) if predicted_files else 1.0
        function_precision = (
            len(function_intersection) / len(predicted_functions)
            if predicted_functions
            else 1.0
        )

        if status == "valid":
            if gold_files.issubset(predicted_files):
                file_matches += 1
            if file_intersection:
                file_any_hits += 1
            if gold_functions.issubset(predicted_functions):
                function_matches += 1
            if gold_functions:
                function_evaluable_instances += 1
                if gold_functions.issubset(predicted_functions):
                    function_matches_evaluable += 1
                if function_intersection:
                    function_any_hits_evaluable += 1
            file_precisions.append(file_precision)
            function_precisions.append(function_precision)
            if gold_functions:
                function_precisions_evaluable.append(function_precision)

        details.append(
            {
                "instance_id": instance_id,
                "status": status,
                "gold_files": sorted(gold_files),
                "predicted_files": sorted(predicted_files),
                "gold_functions": sorted(gold_functions),
                "predicted_functions": sorted(predicted_functions),
                "file_full_match": bool(status == "valid" and gold_files.issubset(predicted_files)),
                "file_any_hit": bool(status == "valid" and file_intersection),
                "function_full_match": bool(
                    status == "valid" and gold_functions.issubset(predicted_functions)
                ),
                "function_any_hit": bool(status == "valid" and function_intersection),
                "file_precision": file_precision if status == "valid" else None,
                "function_precision": function_precision if status == "valid" else None,
            }
        )

    valid_count = len(ids) - len(missing_outputs) - len(invalid_outputs)
    metrics = {
        "dataset": "SWE-bench Common",
        "num_instances": len(ids),
        "source": {
            "gold": "artifacts/common93_candidate_action_gap/gold_entities.json",
            "predictions": "artifacts/common93_runtime_logs/final_outputs/*/searcher_*.json",
            "definition": "upstream_orcaloca/artifact/parse_output.py",
        },
        "output_status": {
            "valid": valid_count,
            "missing": len(missing_outputs),
            "invalid": len(invalid_outputs),
            "missing_instance_ids": missing_outputs,
            "invalid_instance_ids": invalid_outputs,
        },
        "file_localization": {
            "match": file_matches,
            "match_denominator": valid_count,
            "match_rate": file_matches / valid_count if valid_count else 0.0,
            "any_hit": file_any_hits,
            "any_hit_rate": file_any_hits / valid_count if valid_count else 0.0,
            "mean_precision": mean(file_precisions),
            "std_precision": population_std(file_precisions),
        },
        "function_localization": {
            "match_upstream_all_instances": function_matches,
            "match_upstream_rate_all_instances": function_matches / valid_count if valid_count else 0.0,
            "mean_precision_upstream_all_instances": mean(function_precisions),
            "std_precision_upstream_all_instances": population_std(function_precisions),
            "evaluable_instances": function_evaluable_instances,
            "match_evaluable": function_matches_evaluable,
            "match_rate_evaluable": (
                function_matches_evaluable / function_evaluable_instances
                if function_evaluable_instances
                else 0.0
            ),
            "any_hit_evaluable": function_any_hits_evaluable,
            "any_hit_rate_evaluable": (
                function_any_hits_evaluable / function_evaluable_instances
                if function_evaluable_instances
                else 0.0
            ),
            "mean_precision_evaluable": mean(function_precisions_evaluable),
            "std_precision_evaluable": population_std(function_precisions_evaluable),
            "non_evaluable_instances": [
                row["instance_id"] for row in details if not row["gold_functions"]
            ],
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (args.output_dir / "instance_metrics.jsonl").open("w", encoding="utf-8") as handle:
        for row in details:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
