"""Validate original nurse schedules directly, without any SAT encoder."""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys


SHIFTS = ("D", "E", "N", "O")
EXPECTED_RULES = [
    (("D", "E", "N"), 28, 20, 28),
    (("O",), 14, 4, 14),
    (("N",), 14, 1, 4),
    (("E",), 14, 4, 8),
    (("N",), 2, 0, 1),
    (("E", "N"), 7, 2, 4),
    (("D", "E", "N"), 7, 0, 6),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def window_counts(schedule: str, counted, length: int):
    """Return (one-based first day, count), including the final full window."""
    prefix = [0]
    selected = set(counted)
    for shift in schedule:
        prefix.append(prefix[-1] + int(shift in selected))
    for start in range(len(schedule) - length + 1):
        yield start + 1, prefix[start + length] - prefix[start]


def validate_solution(instance: dict, solution: dict) -> dict:
    errors = []

    def error(message):
        if len(errors) < 40:
            errors.append(message)

    identifier = instance.get("instance_id")
    if instance.get("schema") != "sequence-nurse-instance-v1":
        error("Unknown instance schema")
    nurses, horizon = instance.get("nurses"), instance.get("days")
    if type(nurses) is not int or type(horizon) is not int or min(nurses, horizon) < 1:
        return {"instance_id": identifier, "valid": False, "errors": ["Invalid dimensions"]}
    if instance.get("shifts") != list(SHIFTS):
        error("Expected shift order D,E,N,O")
    if instance.get("assignment_semantics") != "exactly_one_shift_per_nurse_per_day":
        error("Unexpected assignment semantics")
    if instance.get("index_base") != 1 or instance.get("window_semantics") != "all_full_windows_no_wrap":
        error("Unexpected indexing or window semantics")
    if instance.get("coverage_semantics") != "minimum_per_day_per_working_shift":
        error("Unexpected coverage semantics")
    try:
        rules = [(tuple(r["shifts"]), r["window"], r["lower"], r["upper"])
                 for r in instance["sequence_constraints"]]
    except (KeyError, TypeError):
        rules = []
    if rules != EXPECTED_RULES:
        error("Sequence rules differ from the seven Bergman constraints")
    if solution.get("schema") != "nurse-roster-solution-v1":
        error("Unknown solution schema")
    if solution.get("instance_id") != identifier or solution.get("status") != "SAT":
        error("Wrong solution instance or status")
    schedules = solution.get("schedule")
    if not isinstance(schedules, list) or len(schedules) != nurses:
        return {"instance_id": identifier, "valid": False,
                "errors": errors + ["Expected exactly one schedule per nurse"]}
    for nurse, row in enumerate(schedules, 1):
        if not isinstance(row, str) or len(row) != horizon or not set(row) <= set(SHIFTS):
            error(f"Invalid schedule for nurse {nurse}: one D/E/N/O symbol per day required")
    if errors:
        return {"instance_id": identifier, "valid": False, "errors": errors}

    checked_windows = 0
    for nurse, row in enumerate(schedules, 1):
        for shifts, length, lower, upper in EXPECTED_RULES:
            for first_day, count in window_counts(row, shifts, length):
                checked_windows += 1
                if not lower <= count <= upper:
                    error(f"nurse={nurse} day={first_day} q={length} shifts={''.join(shifts)} "
                          f"count={count} outside [{lower},{upper}]")

    hard_off = instance.get("hard_day_off")
    phase_counts, off_counts = [], []
    forced_per_day = [0] * horizon
    if not isinstance(hard_off, list) or len(hard_off) != nurses:
        error("hard_day_off must contain one list per nurse")
    else:
        for nurse, days in enumerate(hard_off, 1):
            if (not isinstance(days, list)
                    or any(type(d) is not int or not 1 <= d <= horizon for d in days)
                    or days != sorted(set(days))):
                error(f"Invalid hard day-off list for nurse {nurse}")
                continue
            off_counts.append(len(days))
            phase_counts.append(len({(d - 1) % 14 for d in days}))
            for day in days:
                forced_per_day[day - 1] += 1
                if schedules[nurse - 1][day - 1] != "O":
                    error(f"hard_day_off violated: nurse={nurse} day={day}")

    coverage = [Counter(row[day] for row in schedules) for day in range(horizon)]
    demand = instance.get("demand")
    if not isinstance(demand, list) or len(demand) != horizon:
        error("Expected one demand row per day")
    else:
        for day, requested in enumerate(demand, 1):
            if (not isinstance(requested, dict) or set(requested) != {"D", "E", "N"}
                    or any(type(v) is not int or v < 0 for v in requested.values())):
                error(f"Invalid demand row at day {day}")
                continue
            for shift, needed in requested.items():
                if coverage[day - 1][shift] < needed:
                    error(f"demand violated: day={day} shift={shift} "
                          f"actual={coverage[day - 1][shift]} required={needed}")

    try:
        parameters = instance["generation"]
        slack = Fraction(parameters["demand_slack"])
        rate = Fraction(parameters["hard_off_rate"])
        if not 0 <= slack < 1 or not 0 <= rate <= 1:
            raise ValueError("Invalid rate")
        total = int((1 - slack) * Fraction(5 * nurses, 7))
        weights = parameters["shift_weights"]
        if len(weights) != 3 or any(type(w) is not int or w <= 0 for w in weights):
            raise ValueError("Invalid shift weights")
        quotas = [Fraction(total * w, sum(weights)) for w in weights]
        allocation = [q.numerator // q.denominator for q in quotas]
        ranking = sorted(range(3), key=lambda i: (-(quotas[i] - allocation[i]), i))
        for i in ranking[:total - sum(allocation)]:
            allocation[i] += 1
        expected_demand = dict(zip(SHIFTS[:3], allocation))
        if demand != [expected_demand] * horizon:
            error("Demand does not match capacity/slack/Hamilton allocation")
        off_fraction = rate * horizon
        expected_off = -(-off_fraction.numerator // off_fraction.denominator)
        if off_counts != [expected_off] * nurses:
            error("Hard-off counts do not match ceil(rate * H)")
        phase_limit = parameters["off_phase_count"]
        if type(phase_limit) is not int or not 1 <= phase_limit <= 4:
            raise ValueError("Invalid off phase count")
        expected_phases = min(phase_limit, expected_off)
        if phase_counts != [expected_phases] * nurses:
            error("Hard-off residue counts do not match configured phase count")
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        error("Invalid or missing generation parameters")

    work_counts = [nurses - row["O"] for row in coverage]
    return {
        "instance_id": identifier, "valid": not errors, "errors": errors,
        "nurses": nurses, "days": horizon, "checked_sequence_windows": checked_windows,
        "checked_coverage_cells": 3 * horizon,
        "checked_hard_off_cells": sum(off_counts),
        "hard_off_count_min": min(off_counts, default=0),
        "hard_off_count_max": max(off_counts, default=0),
        "hard_off_residues_min": min(phase_counts, default=0),
        "hard_off_residues_max": max(phase_counts, default=0),
        "max_forced_off_on_one_day": max(forced_per_day),
        "actual_work_total": sum(work_counts),
        "actual_work_daily_min": min(work_counts),
        "actual_work_daily_max": max(work_counts),
        "actual_coverage_min": {s: min(row[s] for row in coverage) for s in SHIFTS},
        "actual_coverage_max": {s: max(row[s] for row in coverage) for s in SHIFTS},
        "distinct_reference_schedules": len(set(schedules)),
    }


def contained_file(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError(f"Invalid dataset file path: {relative}")
    return target


def validate_dataset(root: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    results, integrity_errors, listed = [], [], []
    ids = set()
    if manifest.get("schema") != "sequence-nurse-manifest-v1":
        integrity_errors.append("Unknown manifest schema")
    entries = manifest.get("instances", [])
    if not isinstance(entries, list) or not entries:
        return {"schema": "sequence-nurse-validation-v1", "valid": False,
                "instances_checked": 0, "valid_instances": 0,
                "integrity_errors": ["Manifest must list at least one instance"], "instances": []}
    if manifest.get("instance_count") != len(entries):
        integrity_errors.append("Manifest instance_count differs from its entries")
    try:
        config = manifest["configuration"]
        expected_grid = Counter((n, h, s) for n in config["nurses"]
                                for h in config["days"] for s in config["seeds"])
        listed_grid = Counter((e["nurses"], e["days"], e["seed"]) for e in entries)
        if listed_grid != expected_grid:
            integrity_errors.append("Instance grid differs from manifest configuration")
    except (KeyError, TypeError):
        integrity_errors.append("Invalid or missing manifest configuration")
    for entry in entries:
        try:
            if entry["instance_id"] in ids:
                integrity_errors.append(f"Duplicate instance ID: {entry['instance_id']}")
            ids.add(entry["instance_id"])
            instance_path = contained_file(root, entry["instance_path"])
            witness_path = contained_file(root, entry["reference_solution_path"])
            listed.append(entry["instance_path"])
            if sha256(instance_path) != entry["instance_sha256"]:
                integrity_errors.append(f"Instance checksum mismatch: {entry['instance_id']}")
            if sha256(witness_path) != entry["reference_solution_sha256"]:
                integrity_errors.append(f"Reference checksum mismatch: {entry['instance_id']}")
            instance = json.loads(instance_path.read_text(encoding="utf-8"))
            solution = json.loads(witness_path.read_text(encoding="utf-8"))
            if instance["instance_id"] != entry["instance_id"]:
                integrity_errors.append(f"Manifest/instance ID mismatch: {entry['instance_id']}")
            if (instance["nurses"], instance["days"], instance["generation"]["seed"]) != (
                    entry["nurses"], entry["days"], entry["seed"]):
                integrity_errors.append(f"Manifest/instance dimensions or seed mismatch: {entry['instance_id']}")
            results.append(validate_solution(instance, solution))
        except (ValueError, KeyError, OSError, TypeError) as exc:
            integrity_errors.append(str(exc))
    actual = sorted(p.relative_to(root).as_posix() for p in (root / "instances").glob("*.json"))
    if actual != sorted(listed):
        integrity_errors.append("Instance file inventory differs from manifest")
    for relative, digest in manifest.get("tool_sha256", {}).items():
        try:
            if sha256(contained_file(root, relative)) != digest:
                integrity_errors.append(f"Tool checksum mismatch: {relative}")
        except (ValueError, OSError) as exc:
            integrity_errors.append(str(exc))
    return {
        "schema": "sequence-nurse-validation-v1",
        "valid": not integrity_errors and len(results) == len(entries)
                 and all(row["valid"] for row in results),
        "instances_checked": len(results),
        "valid_instances": sum(row["valid"] for row in results),
        "integrity_errors": integrity_errors,
        "evidence": "direct validation of original schedules; no solver status inferred",
        "instances": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dataset", type=Path)
    group.add_argument("--instance", type=Path)
    parser.add_argument("--solution", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.dataset:
        report = validate_dataset(args.dataset)
    else:
        if args.solution is None:
            parser.error("--instance requires --solution")
        report = validate_solution(
            json.loads(args.instance.read_text(encoding="utf-8")),
            json.loads(args.solution.read_text(encoding="utf-8")))
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k != "instances"}))
    else:
        print(text)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
