#!/usr/bin/env python3
"""Check the installed CPLEX/CP Optimizer engines on bounded local models."""
import argparse
import datetime
import hashlib
import importlib.util
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys

REPO = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPO / "tmp/cplex-check.json")
    args = parser.parse_args()
    from docplex.cp.model import CpoModel
    from docplex.mp.model import Model
    import cplex
    cp_exe = os.environ.get("CPO_EXECUTABLE") or shutil.which("cpoptimizer")
    if not cp_exe:
        raise SystemExit("Source scripts/linux_env.sh before running this check.")
    report = {"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "python": sys.version, "cpoptimizer": cp_exe, "cpoptimizer_sha256": sha(cp_exe),
              "cplex_module_version": cplex.__version__,
              "cplex_pip_distribution_version": importlib.metadata.version("cplex"), "checks": {}, "errors": {}}
    cplex_lib = Path(cplex.__file__).parent / "_internal/libcplex2220.so"
    if cplex_lib.exists():
        report["cplex_library_sha256"] = sha(cplex_lib)

    def check_cp():
        model = CpoModel()
        variables = model.binary_var_list(1100)
        model.add(model.sum(variables) == 550)
        solution = model.solve(execfile=cp_exe, TimeLimit=10, Workers=1, LogVerbosity="Quiet")
        assert solution.is_solution(), solution.get_solve_status()
        assert sum(solution[var] for var in variables) == 550
        return {"variables": 1100, "validated_sum": 550,
                "status": str(solution.get_solve_status()), "solver_infos": dict(solution.get_solver_infos())}

    def check_mp():
        with Model(name="installation_1100_vars") as model:
            variables = model.binary_var_list(1100)
            model.add_constraint(model.sum(variables) == 550)
            model.minimize(model.sum(variables))
            model.parameters.threads = 1
            model.set_time_limit(10)
            result = model.solve(log_output=False)
            assert result is not None
            assert round(sum(result[var] for var in variables)) == 550
            return {"variables": 1100, "validated_sum": 550, "status": model.solve_details.status,
                    "engine_version": model.get_cplex().get_version()}

    def check_nrp():
        spec = importlib.util.spec_from_file_location("nrp_cp_runtime_check", REPO / "Compare_NRP_2010/CPLEX/CP/cp_model.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        nurse = module.NRP(40, 2)
        nurse.add_constraints()
        schedules = []
        last_status = None
        with nurse.model.start_search(execfile=cp_exe, TimeLimit=30, Workers=1,
                                      SearchType="Auto", LogVerbosity="Quiet") as search:
            for result in search:
                work = [result[var] for var in nurse.x]
                assert all(v in (0, 1) for v in work)
                assert all(4 <= sum(work[i:i + 7]) <= 5 for i in range(0, 34, 7))
                assert all(sum(work[i:i + 9]) <= 6 for i in range(32))
                assert all(sum(work[i:i + 30]) >= 20 for i in range(11))
                schedules.append(work)
                last_status = str(result.get_solve_status())
        assert len(schedules) == len(set(map(tuple, schedules))) == 3, len(schedules)
        return {"class": 2, "horizon": 40, "count": 3, "independently_validated": True,
                "schedules": schedules, "last_status": last_status, "search": "Auto, Workers=1 for this check only"}

    for name, function in (("CP_Optimizer_1100_variables", check_cp), ("CPLEX_MP_1100_variables", check_mp), ("NRP_2010_CII_H40", check_nrp)):
        try:
            report["checks"][name] = function()
            print(name, "PASS", flush=True)
        except Exception as exc:
            report["errors"][name] = f"{type(exc).__name__}: {exc}"
            print(name, "FAIL", report["errors"][name], flush=True)
    report["passed"] = not report["errors"]
    report["scope"] = "Runtime integration and bounded model checks, not formal performance results or a license entitlement audit."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
