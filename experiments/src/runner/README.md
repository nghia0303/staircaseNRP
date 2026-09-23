# amongNurse Ladder solver comparison

`run_among_nurse_ladder_solvers.sh` compares the same
`staircase-binomial` CNF with four enumeration paths:

- `g421-legacy-enum-models`: exact legacy loop. PySAT `enum_models()` adds
  one full-model blocking clause before each yield, and the legacy loop also
  builds one schedule-only blocking clause with the original per-day
  `get_variable()` loop;
- `g421-projected`: G421 with one schedule-only blocking clause per model;
- `cadical195-projected`: CaDiCaL 1.9.5 with the same projected loop;
- `tabularallsat`: projected TabularAllSAT with no blocking clauses.

The legacy configuration is not plain `enum_models()`. Its projected clause
subsumes the extra full-model clause, so it still counts schedules rather than
auxiliary assignments. The extra full-model clause is retained only to
reproduce the old implementation.

From the repository root, run the C-II/H=40 smoke comparison:

```bash
bash experiments/src/runner/run_among_nurse_ladder_solvers.sh
```

Run one selected instance or the full 15-instance grid:

```bash
bash experiments/src/runner/run_among_nurse_ladder_solvers.sh 3 40
bash experiments/src/runner/run_among_nurse_ladder_solvers.sh --grid
```

Useful environment variables:

- `LADDER_SOLVER_METHODS`: space-separated subset of the four method names;
- `LADDER_SOLVER_TIMEOUT_S`: per-method timeout, default `300`;
- `LADDER_SOLVER_MEMORY_MB`: runlim memory limit;
- `LADDER_SOLVER_OUTPUT_ROOT`: output directory;
- `LADDER_SOLVER_VALIDATE_MODELS=1`: validate every schedule and uniqueness;
- `TABULAR_ALLSAT_SOURCE` or `TABULAR_ALLSAT_BIN`: pinned solver location.

The main timing is GNU elapsed wall time around the complete method process.
Validation is intended for correctness runs, not timed performance runs. Raw
results and `summary.csv` are written under
`experiments/runs/amongNurse-ladder-solvers/` by default.
