#!/usr/bin/env python3
"""Compare projected AllSAT backends on the legacy Ladder amongNurse CNF.

This adapter intentionally reuses the legacy model and encoding while the new
experiment runner is developed under ``experiments/``. It supports the two
historical PySAT enumeration loops, CaDiCaL 1.9.5 with projected blocking, and
the pinned TabularAllSAT executable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Callable, Iterable


LEGACY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(LEGACY_ROOT))

import pysat  # noqa: E402
from pysat.solvers import Solver  # noqa: E402
from src.test.NRP_2010 import NRP  # noqa: E402


METHODS = {
    "g421-legacy-enum-models": ("g421", "legacy_enum_models"),
    "g421-projected": ("g421", "projected_blocking"),
    "cadical195-projected": ("cadical195", "projected_blocking"),
    "tabularallsat": ("TabularAllSAT", "projected_tabularallsat"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, data: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
    temporary.replace(path)


def schedule_block(model: list[int], projection: list[int]) -> list[int]:
    """Block exactly the current assignment of the projected variables."""
    return [-var if model[var - 1] > 0 else var for var in projection]


def legacy_schedule_block(
    model: list[int],
    horizon: int,
    get_variable: Callable[[int], int],
) -> list[int]:
    """Reproduce the per-day projected-clause loop in the old source."""
    blocking_clause = []
    for day in range(1, horizon + 1):
        if model[get_variable(day) - 1] > 0:
            blocking_clause.append(-get_variable(day))
        else:
            blocking_clause.append(get_variable(day))
    return blocking_clause


def schedule_bits(model: list[int], projection: list[int]) -> tuple[int, ...]:
    return tuple(1 if model[var - 1] > 0 else 0 for var in projection)


def valid_schedule(bits: tuple[int, ...], class_id: int) -> bool:
    upper_bound, upper_width = ((6, 8), (6, 9), (7, 9))[class_id - 1]
    lower_bound, lower_width = ((22, 30), (20, 30), (22, 30))[class_id - 1]
    for start in range(len(bits) - upper_width + 1):
        if sum(bits[start : start + upper_width]) > upper_bound:
            return False
    for start in range(len(bits) - lower_width + 1):
        if sum(bits[start : start + lower_width]) < lower_bound:
            return False
    for start in range(0, len(bits) - 6, 7):
        if not 4 <= sum(bits[start : start + 7]) <= 5:
            return False
    return True


def validate_projected_model(
    model: list[int],
    projection: list[int],
    class_id: int,
    seen: set[tuple[int, ...]],
) -> None:
    bits = schedule_bits(model, projection)
    if not valid_schedule(bits, class_id):
        raise RuntimeError("solver returned an invalid projected schedule")
    if bits in seen:
        raise RuntimeError("solver returned a duplicate projected schedule")
    seen.add(bits)


def pysat_stats(solver: Solver) -> dict:
    try:
        return solver.accum_stats() or {}
    except (AttributeError, NotImplementedError):
        return {}


def enumerate_with_pysat(
    clauses: list[list[int]],
    projection: list[int],
    class_id: int,
    solver_name: str,
    enumeration_mode: str,
    validate_models: bool,
    legacy_get_variable: Callable[[int], int],
) -> dict:
    count = 0
    first_model_s = None
    seen: set[tuple[int, ...]] | None = set() if validate_models else None
    started = time.perf_counter()

    with Solver(name=solver_name, bootstrap_with=clauses) as solver:
        if enumeration_mode == "legacy_enum_models":
            # Exact legacy behaviour: PySAT enum_models() adds a full-model
            # blocking clause before each yield, while the old loop also adds
            # the stronger schedule-only blocking clause after receiving it.
            for model in solver.enum_models():
                # The legacy source overwrote this timestamp for every model.
                # Keep the per-model clock call while retaining the real first
                # model time as a diagnostic field.
                legacy_model_timestamp = time.perf_counter()
                if first_model_s is None:
                    first_model_s = legacy_model_timestamp - started
                if seen is not None:
                    validate_projected_model(model, projection, class_id, seen)
                solver.add_clause(legacy_schedule_block(model, len(projection), legacy_get_variable))
                count += 1
            full_model_blocks = count
        elif enumeration_mode == "projected_blocking":
            while solver.solve():
                if first_model_s is None:
                    first_model_s = time.perf_counter() - started
                model = solver.get_model()
                if model is None:
                    raise RuntimeError("SAT solver returned SAT without a model")
                if seen is not None:
                    validate_projected_model(model, projection, class_id, seen)
                solver.add_clause(schedule_block(model, projection))
                count += 1
            full_model_blocks = 0
        else:
            raise ValueError(f"unsupported PySAT enumeration mode: {enumeration_mode}")

        stats = pysat_stats(solver)

    return {
        "reported_solutions": count,
        "model_lines": None,
        "first_model_s": round(first_model_s, 6) if first_model_s is not None else None,
        "solver_wall_s": round(time.perf_counter() - started, 6),
        "projected_blocking_clauses": count,
        "full_model_blocking_clauses": full_model_blocks,
        "solver_stats": stats,
        "solver_exit_code": 0,
        "enumeration_complete": True,
        "validation": "all_models_and_uniqueness" if validate_models else "none",
    }


def write_projected_cnf(
    path: Path,
    clauses: Iterable[Iterable[int]],
    nvars: int,
    projection: list[int],
) -> None:
    clause_list = clauses if isinstance(clauses, list) else list(clauses)
    with path.open("w", encoding="ascii", newline="\n") as stream:
        stream.write(f"p cnf {nvars} {len(clause_list)} {len(projection)}\n")
        stream.write("c p show " + " ".join(map(str, projection)) + "\n")
        for clause in clause_list:
            stream.write(" ".join(map(str, clause)) + " 0\n")


def projected_model_from_line(line: str, horizon: int) -> tuple[int, ...]:
    literals = [int(token) for token in line.split()]
    if len(literals) != horizon:
        raise RuntimeError(f"TabularAllSAT returned {len(literals)} projected literals, expected {horizon}")
    variables = [abs(literal) for literal in literals]
    if sorted(variables) != list(range(1, horizon + 1)):
        raise RuntimeError("TabularAllSAT returned an invalid projection")
    assignment = {abs(literal): literal > 0 for literal in literals}
    return tuple(int(assignment[var]) for var in range(1, horizon + 1))


def enumerate_with_tabularallsat(
    solver_bin: Path,
    cnf_path: Path,
    stderr_path: Path,
    horizon: int,
    class_id: int,
    timeout_s: int,
    validate_models: bool,
) -> dict:
    command = [
        "timeout",
        "--foreground",
        "--signal=TERM",
        "--kill-after=5s",
        f"{timeout_s}s",
        str(solver_bin),
        "-q",
        "--enum_total",
        str(cnf_path),
    ]
    line_count = 0
    reported_count = None
    waiting_for_count = False
    first_model_s = None
    seen: set[tuple[int, ...]] | None = set() if validate_models else None
    started = time.perf_counter()

    with stderr_path.open("w", encoding="utf-8", newline="\n") as stderr_stream:
        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=stderr_stream,
            text=True,
            bufsize=1,
            start_new_session=True,
        ) as process:
            assert process.stdout is not None
            try:
                for raw_line in process.stdout:
                    line = raw_line.strip()
                    if waiting_for_count:
                        reported_count = int(line)
                        waiting_for_count = False
                    elif line == "s MODEL COUNT":
                        waiting_for_count = True
                    elif not line:
                        continue
                    else:
                        if first_model_s is None:
                            first_model_s = time.perf_counter() - started
                        tokens = line.split()
                        if len(tokens) != horizon:
                            raise RuntimeError(
                                f"TabularAllSAT returned {len(tokens)} projected literals, expected {horizon}"
                            )
                        if seen is not None:
                            bits = projected_model_from_line(line, horizon)
                            if not valid_schedule(bits, class_id):
                                raise RuntimeError("TabularAllSAT returned an invalid schedule")
                            if bits in seen:
                                raise RuntimeError("TabularAllSAT returned a duplicate schedule")
                            seen.add(bits)
                        line_count += 1
                return_code = process.wait()
            except BaseException:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                raise

    complete = return_code == 20 and reported_count is not None and reported_count == line_count
    return {
        "reported_solutions": reported_count,
        "model_lines": line_count,
        "first_model_s": round(first_model_s, 6) if first_model_s is not None else None,
        "solver_wall_s": round(time.perf_counter() - started, 6),
        "projected_blocking_clauses": 0,
        "full_model_blocking_clauses": 0,
        "solver_stats": {},
        "solver_exit_code": return_code,
        "solver_command": command,
        "enumeration_complete": complete,
        "validation": "all_models_and_uniqueness" if validate_models else "none",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=tuple(METHODS), required=True)
    parser.add_argument("--class-id", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--horizon", type=int, choices=(40, 50, 60, 70, 80), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--solver-bin", type=Path)
    parser.add_argument("--timeout-s", type=int, default=300)
    parser.add_argument("--validate-models", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout_s <= 0:
        raise SystemExit("--timeout-s must be positive")
    if args.method == "tabularallsat" and args.solver_bin is None:
        raise SystemExit("--solver-bin is required for tabularallsat")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"ladder_{args.method.replace('-', '_')}_C{args.class_id}_H{args.horizon}"
    report_path = output_dir / f"{prefix}.json"
    cnf_path = output_dir / f"{prefix}.projected.cnf"
    stderr_path = output_dir / f"{prefix}.solver.stderr.txt"

    total_started = time.perf_counter()
    encoding_started = time.perf_counter()
    nrp = NRP(
        horizon=args.horizon,
        constraint=args.class_id,
        encoding_mode="staircase",
        second_encoding_mode="binomial",
    )
    nrp.add_constraints()
    clauses = nrp.get_clauses()
    projection = nrp.variables.get_all_variables()
    nvars = nrp.aux.get_last_used_var()
    if projection != list(range(1, args.horizon + 1)):
        raise RuntimeError("unexpected schedule-variable mapping")
    max_literal = max((abs(lit) for clause in clauses for lit in clause), default=0)
    if nvars != max_literal:
        raise RuntimeError(f"CNF variable mismatch: allocator={nvars}, max_literal={max_literal}")
    encoding_wall_s = time.perf_counter() - encoding_started

    solver_name, enumeration_mode = METHODS[args.method]
    cnf_write_wall_s = 0.0
    solver_bin = None
    if args.method == "tabularallsat":
        solver_bin = args.solver_bin.resolve()
        if not solver_bin.is_file():
            raise SystemExit(f"TabularAllSAT binary not found: {solver_bin}")
        write_started = time.perf_counter()
        write_projected_cnf(cnf_path, clauses, nvars, projection)
        cnf_write_wall_s = time.perf_counter() - write_started
        result = enumerate_with_tabularallsat(
            solver_bin=solver_bin,
            cnf_path=cnf_path,
            stderr_path=stderr_path,
            horizon=args.horizon,
            class_id=args.class_id,
            timeout_s=args.timeout_s,
            validate_models=args.validate_models,
        )
    else:
        result = enumerate_with_pysat(
            clauses=clauses,
            projection=projection,
            class_id=args.class_id,
            solver_name=solver_name,
            enumeration_mode=enumeration_mode,
            validate_models=args.validate_models,
            legacy_get_variable=nrp.variables.get_variable,
        )

    status = "complete" if result["enumeration_complete"] else "timeout" if result["solver_exit_code"] == 124 else "error"
    report = {
        "format_version": 1,
        "status": status,
        "benchmark": "amongNurse",
        "method": args.method,
        "class_id": args.class_id,
        "horizon": args.horizon,
        "encoding": "staircase-binomial",
        "solver": solver_name,
        "enumeration_mode": enumeration_mode,
        "projection": "schedule_variables_1_to_horizon",
        "n_vars": nvars,
        "n_clauses_initial": len(clauses),
        "n_projected": len(projection),
        "encoding_wall_s": round(encoding_wall_s, 6),
        "cnf_write_wall_s": round(cnf_write_wall_s, 6),
        "total_internal_wall_s": round(time.perf_counter() - total_started, 6),
        "python_version": sys.version.split()[0],
        "python_sat_version": pysat.__version__,
        "model_source": str(LEGACY_ROOT / "src" / "test" / "NRP_2010.py"),
        "model_source_sha256": sha256_file(LEGACY_ROOT / "src" / "test" / "NRP_2010.py"),
        "ladder_source_sha256": sha256_file(LEGACY_ROOT / "src" / "encoding" / "staircase_encoding.py"),
        **result,
    }
    if solver_bin is not None:
        report.update(
            {
                "solver_bin": str(solver_bin),
                "solver_sha256": sha256_file(solver_bin),
                "cnf": str(cnf_path),
                "cnf_sha256": sha256_file(cnf_path),
                "solver_stderr": str(stderr_path),
            }
        )
    write_json_atomic(report_path, report)
    print(
        json.dumps(
            {
                "status": status,
                "method": args.method,
                "C": args.class_id,
                "H": args.horizon,
                "solutions": result["reported_solutions"],
                "solver_wall_s": result["solver_wall_s"],
                "report": str(report_path),
            }
        ),
        flush=True,
    )
    return 0 if status == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
