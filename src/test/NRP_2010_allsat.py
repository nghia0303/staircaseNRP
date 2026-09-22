"""Run projected TabularAllSAT on the legacy amongNurse model.

This wrapper reuses NRP_2010.NRP for all constraints and encodings. Only the
projected DIMACS header and the external AllSAT invocation are new.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


SOURCE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE_ROOT))

from src.test.NRP_2010 import NRP  # noqa: E402


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def valid_schedule(bits: tuple[int, ...], class_id: int) -> bool:
    upper, upper_q = ((6, 8), (6, 9), (7, 9))[class_id - 1]
    lower, lower_q = ((22, 30), (20, 30), (22, 30))[class_id - 1]
    horizon = len(bits)
    return (
        all(4 <= sum(bits[start : start + 7]) <= 5 for start in range(0, horizon - 6, 7))
        and all(sum(bits[start : start + upper_q]) <= upper for start in range(horizon - upper_q + 1))
        and all(sum(bits[start : start + lower_q]) >= lower for start in range(horizon - lower_q + 1))
    )


def projected_model(line: str, horizon: int) -> tuple[int, ...]:
    literals = [int(value) for value in line.split()]
    if len(literals) != horizon or {abs(value) for value in literals} != set(range(1, horizon + 1)):
        raise ValueError(f"Incomplete/invalid projected model: {line[:160]}")
    return tuple(int(value > 0) for value in sorted(literals, key=abs))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=("ladder", "de"), default="ladder")
    parser.add_argument("--class-id", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--horizon", type=int, choices=(40, 50, 60, 70, 80), default=40)
    parser.add_argument("--solver-bin", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-s", type=int, default=300)
    parser.add_argument("--validate-models", action="store_true", help="Check every projected schedule and uniqueness (adds overhead)")
    args = parser.parse_args()

    if args.timeout_s <= 0:
        parser.error("--timeout-s must be positive")

    solver_bin = args.solver_bin.resolve()
    if not solver_bin.is_file():
        parser.error(f"TabularAllSAT binary not found: {solver_bin}")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    encoding_mode = "staircase" if args.method == "ladder" else "pblib_bdd"
    encoding_label = f"{encoding_mode}-binomial"
    prefix = f"{args.method}_C{args.class_id}_H{args.horizon}"
    cnf_path = output_dir / f"{prefix}.projected.cnf"
    stderr_path = output_dir / f"{prefix}.stderr.txt"
    report_path = output_dir / f"{prefix}.json"

    encoding_started = time.perf_counter()
    nrp = NRP(
        horizon=args.horizon,
        constraint=args.class_id,
        encoding_mode=encoding_mode,
        second_encoding_mode="binomial",
    )
    nrp.add_constraints()
    projection = nrp.variables.get_all_variables()
    if projection != list(range(1, args.horizon + 1)):
        raise RuntimeError("Unexpected day-variable mapping; projected DIMACS would be wrong")
    clauses = nrp.get_clauses()
    nvars = nrp.aux.get_last_used_var()
    with cnf_path.open("w", encoding="ascii", newline="\n") as stream:
        # TabularAllSAT's projected DIMACS extension: a fourth header field,
        # then c p show with exactly the projected variable IDs (no terminal 0).
        stream.write(f"p cnf {nvars} {len(clauses)} {len(projection)}\n")
        stream.write("c p show " + " ".join(map(str, projection)) + "\n")
        for clause in clauses:
            stream.write(" ".join(map(str, clause)) + " 0\n")
    encoding_wall_s = time.perf_counter() - encoding_started

    command = [
        "timeout", "--foreground", "--signal=TERM", "--kill-after=5s", f"{args.timeout_s}s",
        str(solver_bin), "-q", "--enum_total",
    ]
    command.append(str(cnf_path))

    line_count = 0
    reported_count = None
    waiting_for_count = False
    first_model_s = None
    seen = set() if args.validate_models else None
    solver_started = time.perf_counter()
    with stderr_path.open("w", encoding="utf-8") as stderr_stream:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=stderr_stream, text=True,
                              bufsize=1, start_new_session=True) as process:
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
                            first_model_s = time.perf_counter() - solver_started
                        if len(line.split()) != args.horizon:
                            raise RuntimeError(f"Non-total projected model: {line[:160]}")
                        if args.validate_models:
                            bits = projected_model(line, args.horizon)
                            if not valid_schedule(bits, args.class_id):
                                raise RuntimeError(f"Invalid C-{args.class_id} schedule: {line[:160]}")
                            if bits in seen:
                                raise RuntimeError(f"Duplicate projected schedule: {line[:160]}")
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
    solver_wall_s = time.perf_counter() - solver_started

    status = "complete" if return_code == 20 and reported_count is not None else "timeout" if return_code == 124 else "error"
    if status == "complete" and line_count != reported_count:
        status = "count_mismatch"
    report = {
        "status": status,
        "method": args.method,
        "class_id": args.class_id,
        "horizon": args.horizon,
        "encoding": encoding_label,
        "mode": "enumerate_total_projected",
        "validation": "all_models_and_uniqueness" if args.validate_models else "none",
        "n_vars": nvars,
        "n_clauses": len(clauses),
        "n_projected": len(projection),
        "cnf": str(cnf_path),
        "cnf_sha256": file_sha256(cnf_path),
        "solver_bin": str(solver_bin),
        "solver_sha256": file_sha256(solver_bin),
        "model_source_sha256": file_sha256(SOURCE_ROOT / "src" / "test" / "NRP_2010.py"),
        "window_encoder_source_sha256": file_sha256(SOURCE_ROOT / "src" / "encoding" /
                                                    ("staircase_encoding.py" if args.method == "ladder" else "pblib_encoding.py")),
        "cardinality_source_sha256": file_sha256(SOURCE_ROOT / "src" / "encoding" / "all.py"),
        "solver_exit_code": return_code,
        "solver_command": command,
        "reported_solutions": reported_count,
        "model_lines": line_count,
        "encoding_wall_s": round(encoding_wall_s, 6),
        "solver_wall_s_including_pipe": round(solver_wall_s, 6),
        "first_model_s": round(first_model_s, 6) if first_model_s is not None else None,
        "stderr_file": str(stderr_path),
        "python_version": sys.version.split()[0],
    }
    with report_path.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": status, "method": args.method, "C": args.class_id, "H": args.horizon,
                      "solutions": reported_count, "model_lines": report["model_lines"],
                      "solver_wall_s_including_pipe": report["solver_wall_s_including_pipe"],
                      "report": str(report_path)}), flush=True)
    return 0 if status == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
