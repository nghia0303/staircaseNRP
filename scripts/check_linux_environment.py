"""Bounded environment checks; no dataset generation or benchmark batch."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import importlib
import io
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def check_sat_and_nurse():
    from pysat.pb import PBEnc, EncType
    from pysat.solvers import Solver
    from src.test.NRP_2010 import NRP

    formula = PBEnc.atmost(lits=[1, 2, 3], bound=1, encoding=EncType.bdd)
    with Solver(name="g421", bootstrap_with=formula.clauses) as solver:
        assert solver.solve(assumptions=[1, -2, -3])
        assert not solver.solve(assumptions=[1, 2])
    counts = {}
    for encoding in ("staircase", "pblib_bdd"):
        nurse = NRP(40, 2, encoding, "binomial", "g421")
        nurse.add_constraints()
        with Solver(name="g421", bootstrap_with=nurse.get_clauses()) as solver:
            assert solver.solve()
            model = solver.get_model()
            values = {abs(lit): lit > 0 for lit in model}
            work = [int(values[v]) for v in nurse.variables.get_all_variables()]
            for first in range(0, 40 - 6, 7):
                assert 4 <= sum(work[first:first + 7]) <= 5
            for first in range(40 - 9 + 1):
                assert sum(work[first:first + 9]) <= 6
            for first in range(40 - 30 + 1):
                assert sum(work[first:first + 30]) >= 20
        # Exercise the existing enumeration code without changing its semantics.
        count, _ = nurse.solve()
        assert count == 3, (encoding, count)
        counts[encoding] = count
    with Solver(name="g421", bootstrap_with=[[1, 2]], warm_start=True) as solver:
        count = 0
        while solver.solve():
            model = solver.get_model()
            solver.add_clause([-lit for lit in model if abs(lit) <= 2])
            count += 1
        assert count == 3
    return {"pypblib_bdd_sat_unsat": True, "nrp_CII_H40_counts": counts,
            "independent_window_checks": True, "warm_start_small_formula": True}


def check_mp():
    from docplex.mp.model import Model
    with Model(name="environment_check") as model:
        x = model.binary_var()
        model.maximize(x)
        result = model.solve(log_output=False)
        assert result is not None and result.objective_value == 1
    return "tiny model solved; full experiment license not verified"


def check_gurobi():
    import gurobipy as gp
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        with gp.Model(env=env) as model:
            x = model.addVar(vtype=gp.GRB.BINARY)
            model.setObjective(x, gp.GRB.MAXIMIZE)
            model.optimize()
            assert model.Status == gp.GRB.OPTIMAL and model.ObjVal == 1
    return "tiny model solved; full experiment license not verified"


def check_cpp():
    with tempfile.TemporaryDirectory(prefix="nrp-toolchain-") as directory:
        root = Path(directory)
        source = root / "check.cpp"
        source.write_text("#include <vector>\nint main() { std::vector<int> v{1,2,3}; return v.size() == 3 ? 0 : 1; }\n")
        for compiler in ("g++", "clang++"):
            binary = root / ("check-" + compiler.replace("+", "p"))
            subprocess.run([compiler, "-std=c++17", str(source), "-o", str(binary)],
                           check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([str(binary)], check=True, timeout=5)
    return "GCC and Clang compiled and ran a C++17 program"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Run this check with Linux Python, e.g. inside WSL")
    report = {"python": platform.python_version(), "executable": sys.executable,
              "platform": platform.platform(), "checks": {}, "errors": {}}
    modules = ["pysat", "pypblib.pblib", "psutil", "openpyxl", "numpy", "pandas",
               "scipy", "cftime", "netCDF4", "xarray", "dask", "docplex.mp.model",
               "docplex.cp.model", "cplex", "gurobipy", "func_timeout", "stopit",
               "pytest", "yaml", "portalocker"]
    for module in modules:
        try:
            importlib.import_module(module)
            report["checks"][f"import:{module}"] = True
        except Exception as exc:
            report["errors"][f"import:{module}"] = f"{type(exc).__name__}: {exc}"
    for name, function in [("CXX17", check_cpp), ("SAT_and_NRP", check_sat_and_nurse),
                            ("CPLEX_MP", check_mp), ("Gurobi", check_gurobi)]:
        try:
            # Suppress solver banners, keep the structured result.
            with redirect_stdout(io.StringIO()):
                report["checks"][name] = function()
        except Exception as exc:
            report["errors"][name] = f"{type(exc).__name__}: {exc}"
    report["tools"] = {tool: shutil.which(tool) for tool in
                       ["git", "gcc", "g++", "clang++", "gdb", "make", "cmake", "runlim", "picat", "cpoptimizer"]}
    if report["tools"]["runlim"]:
        result = subprocess.run(["runlim", "-r", "10", "-s", "128",
                                 sys.executable, "-c", "import time; data = bytearray(32*1024*1024); time.sleep(2); print('runlim_ok')"],
                                capture_output=True, text=True, timeout=20)
        report["checks"]["runlim"] = {"returncode": result.returncode, "log": result.stderr}
        if result.returncode or "runlim_ok" not in result.stdout or "ok" not in result.stderr:
            report["errors"]["runlim"] = "Resource-limited subprocess failed"
    else:
        report["errors"]["runlim"] = "Executable not found"
    # Query a fresh process: importing stopit exposes setuptools' vendored
    # distributions on sys.path, which must not be mistaken for installed wheels.
    installed = json.loads(subprocess.check_output(
        [sys.executable, "-m", "pip", "list", "--format=json"], text=True, timeout=30))
    report["packages"] = {row["name"]: row["version"] for row in installed}
    report["tool_versions"] = {}
    for tool in ("git", "gcc", "clang++", "gdb", "cmake", "runlim"):
        if report["tools"][tool]:
            version = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=10)
            report["tool_versions"][tool] = (version.stdout or version.stderr).splitlines()[0]
    report["passed"] = not report["errors"]
    report["scope"] = "Python/SAT development environment only; not full solver integration or benchmark validation"
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
