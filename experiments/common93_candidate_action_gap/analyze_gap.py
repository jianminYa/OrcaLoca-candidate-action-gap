"""Offline Candidate-to-Action Gap analysis for Common93."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set


def _canonical(value: str) -> str:
    value = value.replace("\\", "/")
    for prefix in ("a/", "b/"):
        if value.startswith(prefix):
            value = value[2:]
    return value.lstrip("./")


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _gold_entities(gold_row: Dict[str, Any]) -> Set[str]:
    return {
        _canonical(item["entity"])
        for item in gold_row.get("callable_entities", [])
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    args = parser.parse_args()
    artifact_dir = Path(args.artifact_dir)
    events = _load_jsonl(artifact_dir / "disambiguation_events.jsonl")
    gold = json.loads((artifact_dir / "gold_entities.json").read_text(encoding="utf-8"))

    ranked_events = [
        event
        for event in events
        if event.get("event_type") == "ranked_callable_method"
        and event.get("ranking_applied") is True
    ]
    gold_available = []
    gaps = []
    gap_by_stage = Counter()
    instance_stats = defaultdict(lambda: {"ranked": 0, "gold_available": 0, "gaps": 0})

    for event in ranked_events:
        instance_id = event.get("instance_id", "")
        instance_stats[instance_id]["ranked"] += 1
        candidates = {_canonical(item) for item in event.get("raw_candidates", [])}
        available = _gold_entities(gold.get(instance_id, {})) & candidates
        if not available:
            continue
        gold_available.append({"event": event, "gold_in_raw_candidates": sorted(available)})
        instance_stats[instance_id]["gold_available"] += 1
        selected = {
            _canonical(item.get("canonical_entity", ""))
            for item in event.get("selected_actions", [])
        }
        retained = available & selected
        if retained:
            continue
        diagnostics = {
            item["candidate"]: item
            for item in event.get("candidate_diagnostics", [])
        }
        stages = [diagnostics[item].get("drop_stage") for item in available if item in diagnostics]
        stage = stages[0] if len(set(stages)) == 1 and stages else "action_generation"
        gap = {
            "instance_id": instance_id,
            "event_id": event.get("event_id"),
            "search_action": event.get("search_action"),
            "search_action_input": event.get("search_action_input"),
            "gold_in_raw_candidates": sorted(available),
            "selected_actions": event.get("selected_actions", []),
            "candidate_diagnostics": [
                item for item in event.get("candidate_diagnostics", [])
                if _canonical(item.get("candidate", "")) in available
            ],
            "drop_stage": stage,
        }
        gaps.append(gap)
        gap_by_stage[stage] += 1
        instance_stats[instance_id]["gaps"] += 1

    summary = {
        "dataset": "SWE-bench Common",
        "num_instances": len(gold),
        "ranked_disambiguation_events": len(ranked_events),
        "gold_available_events": len(gold_available),
        "gap_events": len(gaps),
        "candidate_to_action_gap_rate": (
            len(gaps) / len(gold_available) if gold_available else 0.0
        ),
        "gap_by_stage": {
            "threshold": gap_by_stage.get("threshold", 0),
            "top_k": gap_by_stage.get("top_k", 0),
            "action_generation": gap_by_stage.get("action_generation", 0),
        },
        "all_disambiguation_events": len(events),
        "unranked_file_events": sum(event.get("event_type") == "file_unranked" for event in events),
        "unranked_class_events": sum(event.get("event_type") == "class_unranked" for event in events),
        "instance_stats": dict(instance_stats),
    }
    (artifact_dir / "gap_events.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in gaps),
        encoding="utf-8",
    )
    (artifact_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (artifact_dir / "gold_available_events.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in gold_available),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
