#!/usr/bin/env bash
# Run the complete amongNurse AllSAT comparison on C-I and C-II only.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# Keep the previous G421-only list visible for comparison:
# old_sat_methods="sat_g421_staircase-binomial sat_g421_pblib_bdd-pblib_bdd sat_g421_pblib_bdd-binomial"

methods=(
    ladder
    pblib_bdd-pblib_bdd
    de
    sat_g421_staircase-binomial
    sat_g421_pblib_bdd-pblib_bdd
    sat_g421_pblib_bdd-binomial
    sat_cadical195_staircase-binomial
    sat_cadical195_pblib_bdd-pblib_bdd
    sat_cadical195_pblib_bdd-binomial
    sat_cadical300_staircase-binomial
    sat_cadical300_pblib_bdd-pblib_bdd
    sat_cadical300_pblib_bdd-binomial
    classic
    amongMDD2
    seqMDD2
    CPLEX_CP
    CPLEX_MP
    Gurobi
    Picat
)

export ALLSAT_METHODS="${methods[*]}"
exec bash "$repo_root/Compare_NRP_2010/run_all_sat.sh" --ci-cii
