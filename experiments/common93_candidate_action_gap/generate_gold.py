"""Generate Common93 gold callable entities using OrcaLoca's patch parser."""

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

from Orcar.load_cache_dataset import load_filter_hf_dataset_explicit
from dataset.parse_golden_patch import parse_patch


def _model_dict(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


def _canonical_path(path: str) -> str:
    path = path.replace("\\", "/")
    for prefix in ("a/", "b/"):
        if path.startswith(prefix):
            path = path[2:]
    return path.lstrip("./")


def _entities_from_parsed_patch(parsed_patch: str) -> Dict[str, List[Dict[str, Any]]]:
    parsed = json.loads(parsed_patch)
    callable_entities: Dict[str, Dict[str, Any]] = {}
    non_callable_entities: Dict[str, Dict[str, Any]] = {}
    for diff_loc in parsed.get("diff_locs", []):
        file_path = _canonical_path(diff_loc["file"])
        chain = diff_loc.get("diff_nodes", [])
        function_nodes = [node for node in chain if node["node_type"] == "FunctionDef"]
        class_nodes = [node for node in chain if node["node_type"] == "ClassDef"]
        if function_nodes:
            function_node = function_nodes[-1]
            if class_nodes:
                class_name = class_nodes[-1]["node_name"]
                entity = f"{file_path}::{class_name}::{function_node['node_name']}"
                kind = "method"
            else:
                class_name = ""
                entity = f"{file_path}::{function_node['node_name']}"
                kind = "function"
            callable_entities.setdefault(
                entity,
                {
                    "entity": entity,
                    "kind": kind,
                    "file_path": file_path,
                    "class_name": class_name,
                    "function_name": function_node["node_name"],
                    "diff_node_chain": chain,
                },
            )
        elif class_nodes:
            class_name = class_nodes[-1]["node_name"]
            entity = f"{file_path}::{class_name}"
            non_callable_entities.setdefault(
                entity,
                {
                    "entity": entity,
                    "kind": "class",
                    "file_path": file_path,
                    "class_name": class_name,
                    "diff_node_chain": chain,
                },
            )
    return {
        "callable_entities": list(callable_entities.values()),
        "non_callable_entities": list(non_callable_entities.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dataset", default="SWE-bench_common")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = load_filter_hf_dataset_explicit(
        dataset=args.dataset, filter_instance=".*", split="test"
    )
    if args.dataset == "SWE-bench_common" and len(dataset) != 93:
        raise RuntimeError(f"Expected Common93, got {len(dataset)}")

    instance_ids = [row["instance_id"] for row in dataset]
    (output_dir / "common93_instance_ids.txt").write_text(
        "".join(f"{instance_id}\n" for instance_id in instance_ids),
        encoding="utf-8",
    )

    gold: Dict[str, Dict[str, Any]] = {}
    csv_rows: List[Dict[str, Any]] = []
    for index, row in enumerate(dataset):
        parsed_patch = parse_patch(
            patch=row["patch"],
            repo=row["repo"],
            base_commit=row["base_commit"],
            instance_id=row["instance_id"],
            base=args.repo_root,
        )
        entities = _entities_from_parsed_patch(parsed_patch)
        gold[row["instance_id"]] = {
            "instance_id": row["instance_id"],
            "repo": row["repo"],
            "base_commit": row["base_commit"],
            "callable_entities": entities["callable_entities"],
            "non_callable_entities": entities["non_callable_entities"],
            "parsed_patch": json.loads(parsed_patch),
        }
        csv_rows.append(
            {
                "instance_id": row["instance_id"],
                "repo": row["repo"],
                "base_commit": row["base_commit"],
                "parsed_patch": parsed_patch,
            }
        )
        print(f"gold {index + 1:03d}/{len(dataset):03d} {row['instance_id']}", flush=True)

    (output_dir / "gold_entities.json").write_text(
        json.dumps(gold, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (output_dir / "golden_stats.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["instance_id", "repo", "base_commit", "parsed_patch"],
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    callable_count = sum(
        len(item["callable_entities"]) for item in gold.values()
    )
    print(f"instances={len(dataset)}")
    print(f"callable_gold_entities={callable_count}")


if __name__ == "__main__":
    main()
