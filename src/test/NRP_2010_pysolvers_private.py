#!/usr/bin/env python3
"""Experimental one-solution amongNurse driver using private ``pysolvers``.

This adapter deliberately has a separate executable and method ID.  It feeds
the exact CNF produced by :mod:`src.test.NRP_2010` to the native extension
without importing the public :mod:`pysat.solvers` wrappers.  The API is private
to python-sat and is therefore pinned to the version used by the experiment.

Usage::

    NRP_2010_pysolvers_private.py H CLASS ENCODING BACKEND

``BACKEND`` is one of ``g421``, ``cadical195``, or ``cadical300``.
"""

import os
import sys
import time

import pysolvers


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.test.NRP_2010 import NRP  # noqa: E402


BACKENDS = ("g421", "cadical195", "cadical300")


def parse_arguments(argv):
    if len(argv) != 5:
        raise SystemExit(
            "Usage: NRP_2010_pysolvers_private.py "
            "H CLASS ENCODING {g421|cadical195|cadical300}"
        )
    horizon = int(argv[1])
    class_id = int(argv[2])
    encoding = argv[3]
    backend = argv[4]
    if horizon <= 0:
        raise SystemExit("H must be positive")
    if class_id not in (1, 2, 3):
        raise SystemExit("CLASS must be 1, 2, or 3")
    if backend not in BACKENDS:
        raise SystemExit(f"unsupported private backend: {backend}")
    if "-" in encoding:
        encoding_mode, second_encoding_mode = encoding.split("-", 1)
    else:
        encoding_mode, second_encoding_mode = encoding, "nsc"
    return horizon, class_id, encoding_mode, second_encoding_mode, backend


def private_functions(backend):
    if backend == "g421":
        return (
            pysolvers.glucose421_new,
            pysolvers.glucose421_add_cl,
            pysolvers.glucose421_solve,
            pysolvers.glucose421_del,
        )
    if backend == "cadical195":
        return (
            pysolvers.cadical195_new,
            pysolvers.cadical195_add_cl,
            pysolvers.cadical195_solve,
            lambda handle: pysolvers.cadical195_del(handle, None),
        )
    return (
        pysolvers.cadical300_new,
        pysolvers.cadical300_add_cl,
        pysolvers.cadical300_solve,
        lambda handle: pysolvers.cadical300_del(handle, None),
    )


def solve_one(clauses, backend):
    create, add_clause, solve, delete = private_functions(backend)
    handle = create()
    try:
        for clause in clauses:
            # False means the accumulated formula is already inconsistent; it
            # is a valid solver result rather than a binding failure.
            add_clause(handle, clause)

        # Match PySAT Cadical300.new(): factor=0 is applied after bootstrap.
        if backend == "cadical300":
            pysolvers.cadical300_set(handle, "factor", 0)

        # This standalone driver always calls solve from Python's main thread.
        return bool(solve(handle, [], 1))
    finally:
        delete(handle)


def main(argv):
    horizon, class_id, encoding_mode, second_encoding_mode, backend = (
        parse_arguments(argv)
    )

    started = time.perf_counter()
    nrp = NRP(
        horizon=horizon,
        constraint=class_id,
        encoding_mode=encoding_mode,
        second_encoding_mode=second_encoding_mode,
        solver_name=backend,
        use_local_solver=False,
        use_tseintin=False,
        chunk_width=5,
    )
    nrp.add_constraints()
    satisfiable = solve_one(nrp.get_clauses(), backend)
    ended = time.perf_counter()

    print(f'"time" : {(ended - started) * 1000:.3f}')
    print(f'"solns" : {1 if satisfiable else 0}')
    print(f'"nvars" : {nrp.aux.get_last_used_var()}')
    print(f'"nclauses" : {len(nrp.get_clauses())}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
