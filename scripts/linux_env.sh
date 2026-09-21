#!/usr/bin/env bash
# Source this file; do not execute it as a child shell.
export SRC_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export NRP_VENV="${NRP_VENV:-$HOME/.venvs/sequenceconstraint}"
export NRP_NATIVE_HOME="${NRP_NATIVE_HOME:-$HOME/.local/opt/sequenceconstraint}"
export PATH="$NRP_NATIVE_HOME/bin:$NRP_VENV/bin:$PATH"
export PICAT_RUN_PATH="$NRP_NATIVE_HOME/bin/picat"
export AMONG_NURSE_SCRIPT="$NRP_NATIVE_HOME/bin/amongNurse"
export HADDOCK_CP_SCRIPT="$NRP_NATIVE_HOME/bin/sequenceNurse"
export HADDOCK_CP_SEQ_SCRIPT="$NRP_NATIVE_HOME/bin/sequenceNurseNew"
export CPLEX_STUDIO_DIR="${CPLEX_STUDIO_DIR:-$HOME/.local/opt/ibm/ILOG/CPLEX_Studio2220}"
if [[ -x "$CPLEX_STUDIO_DIR/cpoptimizer/bin/x86-64_linux/cpoptimizer" ]]; then
    export CPO_EXECUTABLE="$CPLEX_STUDIO_DIR/cpoptimizer/bin/x86-64_linux/cpoptimizer"
    export PATH="$CPLEX_STUDIO_DIR/cpoptimizer/bin/x86-64_linux:$CPLEX_STUDIO_DIR/cplex/bin/x86-64_linux:$PATH"
fi
# Compatibility names for legacy scripts: both now use the same Linux env.
export VENV_3_12_PATH="$NRP_VENV/bin/activate"
export VENV_3_8_PATH="$NRP_VENV/bin/activate"
