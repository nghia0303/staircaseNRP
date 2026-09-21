#!/usr/bin/env python3
"""Bounded native runtime smoke checks, not a benchmark/model certification."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPO / "tmp/native-solvers-check.json")
    args = parser.parse_args()
    prefix = Path(os.environ.get("NRP_NATIVE_HOME", Path.home() / ".local/opt/sequenceconstraint"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    logs = args.output.parent / (args.output.stem + "-logs")
    logs.mkdir(exist_ok=True)
    report = {"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "native runtime and bounded NRP-2010 count agreement; not full model audit",
              "installation": json.loads((prefix / "manifest.json").read_text()), "checks": {}}
    cases = []
    for one in (0, 1):
        cases.append((f"picat_CII_H40_one{one}", [str(prefix / "bin/picat"), str(REPO / "Compare_NRP_2010/Picat/sample.pi"), "2", "40", str(one)], 1 if one else 3))
        for mode in (0, 1, 2):
            options = ["-w64", f"-m{mode}", "-r5", "-i10", "-c2", "-h40"]
            options += ["-n0", "-na1", "-d2"] if mode == 0 else ["-n3", "-na1", "-d3"]
            options += ["-ca1", "-a1", "-e1", "-p0", "-t3", f"-maxP{int(mode > 0)}", f"-minP{int(mode > 0)}", "-wP0", "-j1", f"-so{one}"]
            cases.append((f"amongNurse_mode{mode}_CII_H40_one{one}", [str(prefix / "bin/amongNurse"), *options], 1 if one else 3))
    for mode in (0, 2):
        cases.append((f"sequenceNurse_mode{mode}_N1_H28", [str(prefix / "bin/sequenceNurse"), "-w64", f"-m{mode}", "-n1", "-d28"], 1))
    cases.append(("sequenceNurseNew_mode4_N1_H28", [str(prefix / "bin/sequenceNurseNew"), "-w64", "-m4", "-r5", "-i10", "-nurse1", "-day28", "-n3", "-na1", "-d3", "-ca1", "-a1", "-e1", "-p0", "-t3", "-maxP0", "-minP0", "-wP0", "-j0"], 1))
    for name, command, expected in cases:
        resource_log = logs / (name + ".runlim")
        output_log = logs / (name + ".log")
        wrapped = ["runlim", "--real-time-limit=30", "--space-limit=2048", "--output-file=" + str(resource_log), *command]
        with output_log.open("w") as out:
            completed = subprocess.run(wrapped, stdout=out, stderr=subprocess.STDOUT, timeout=40)
        stdout = output_log.read_text(errors="replace")
        resource = resource_log.read_text(errors="replace")
        counts = re.findall(r'"?solns"?\s*:\s*(\d+)', stdout)
        passed = completed.returncode == 0 and bool(counts) and all(int(n) == expected for n in counts) and bool(re.search(r"status:\s+ok", resource))
        witness_valid = None
        if name.startswith("sequenceNurseNew"):
            # Independent check of the printed witness, after the timed process.
            row = next((line for line in stdout.splitlines() if line.startswith("Nurse 0 :")), "")
            shifts = [int(value) for value in re.findall(r"x_\d+\((\d+)\)", row)]
            constraints = [(14, 4, 14, {0}), (28, 20, 28, {1, 2, 3}),
                           (14, 1, 4, {3}), (14, 4, 8, {2}), (2, 0, 1, {3}),
                           (7, 2, 4, {2, 3}), (7, 0, 6, {1, 2, 3})]
            witness_valid = len(shifts) == 28 and all(value in range(4) for value in shifts)
            witness_valid = witness_valid and all(lower <= sum(value in members for value in shifts[start:start + window]) <= upper
                for window, lower, upper, members in constraints for start in range(28 - window + 1))
            passed = passed and witness_valid
        report["checks"][name] = {"passed": passed, "command": command, "returncode": completed.returncode,
                                  "expected_count": expected, "observed_counts": counts,
                                  "independent_witness_valid": witness_valid,
                                  "stdout": stdout, "runlim": resource,
                                  "output_log": str(output_log.resolve()), "resource_log": str(resource_log.resolve())}
        print(name, "PASS" if passed else "FAIL", flush=True)
    report["passed"] = all(check["passed"] for check in report["checks"].values())
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(args.output)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
