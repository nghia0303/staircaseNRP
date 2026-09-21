# MiniCPP / HADDOCK build inputs

Upstream: https://bitbucket.org/ldmbouge/minicpp.git

Pinned commit: `9bf9110059c1e883efbc97d79640486c1cd5d8b2` (Bitbucket master, verified 2026-09-21). This matches the engine snapshot previously present in the project's ignored `MiniCP/master` directory. It is **not** the paper-2022 `v1.1` tag and is not the newer GitHub implementation.

`project-frontends.patch` preserves the project's three existing frontends relative to this upstream commit:

- `examples/mdd/amongNurse.cpp`: class/horizon parameters, lexicographic minimum-value branching, first/all-solution option and existing output.
- `examples/mdd/sequenceNurse.cpp`: nurse/horizon parameters and existing model/search.
- `examples/mdd/sequenceNurseNew.cpp`: project's additional Among-window frontend.

These files were previously under a gitignored dependency directory. Keeping their differences here makes installation on another Linux machine independent of that directory. Upstream files and license headers remain in the downloaded source; the installer does not vendor or commit compiled binaries.

`engine-defaults.patch` explicitly initializes two upstream Boolean fields:

- `CPSolver::_inBranching = false`: a newly created solver is not in a branching operation.
- `MDDSpec::_onlyApproximateFirstIteration = false`: approximate equivalence is not restricted to the first propagation unless its dedicated setter enables that restriction.

Both fields were read on the nurse execution path without guaranteed initialization. This is a local correctness patch, not an upstream release. Report the commit **and both patch hashes** with experiments. Old runs made before the fix cannot be assumed to have used these values.

Build: `bash scripts/setup_native_linux.sh` from the repository root. It builds Release/C++17 using GCC and the upstream CMake configuration. It installs versioned dependencies outside the repository, preserving the working tree.

## Scope of the runtime check

`scripts/check_native_solvers.py` checks first/all solution counts for NRP-2010 C-II/H=40 against the known SAT count (3), and runs the three existing Sequence frontends/modes on N=1/H=28. Each process is limited to 30 real seconds and 2048 MB by runlim. This verifies that the binaries execute, not every constraint or heuristic in every frontend.

The Sequence-N frontends still need the previously planned model audit and shift-off/demand integration. In particular, the old multi-nurse graph-posting lifecycle and the nested nurse loop in `sequenceNurseNew` need review before N>1 experiments. The old Sequence Picat model's evening-window constraint sums all shifts instead of evening only. None of these old Sequence models is certified by the installation smoke check.

The old shell batch scripts now resolve native paths through `scripts/linux_env.sh`; they remain historical runners. Their timeout, cache-clearing, result parsing and positional model options have not been converted into the agreed 300-second experiment runner.
