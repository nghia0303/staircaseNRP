#!/usr/bin/env bash
# Install the separately downloaded IBM Linux installer; never store it in Git.
set -euo pipefail
if [[ $# != 1 || ! -f "$1" ]]; then
    printf 'Usage: bash scripts/setup_cplex_linux.sh /path/to/IBM_ILOG_CPLEX_OptStdv22.2_LIN.bin\n' >&2
    exit 2
fi
installer="$(realpath -- "$1")"
install_dir="${CPLEX_STUDIO_DIR:-$HOME/.local/opt/ibm/ILOG/CPLEX_Studio2220}"
if [[ -e "$install_dir" ]]; then
    printf 'Target already exists; inspect it before installing: %s\n' "$install_dir" >&2
    exit 1
fi
command -v java >/dev/null || { echo 'Install openjdk-21-jre-headless first.' >&2; exit 1; }
cache_dir="$HOME/.cache/sequenceconstraint/cplex-install"
mkdir -p "$cache_dir"
response_file="$cache_dir/response.properties"
printf 'INSTALLER_UI=silent\nLICENSE_ACCEPTED=true\nUSER_INSTALL_DIR=%s\n' "$install_dir" > "$response_file"
sha256sum "$installer" > "$cache_dir/installer.sha256"
# The requested installation accepts IBM's bundled software license.
java_bin="$(readlink -f -- "$(command -v java)")"
bash "$installer" LAX_VM "$java_bin" -i silent -f "$response_file" > "$cache_dir/install.log" 2>&1 || {
    tail -60 "$cache_dir/install.log" >&2
    exit 1
}
test -x "$install_dir/cpoptimizer/bin/x86-64_linux/cpoptimizer"
docplex_bin="${NRP_VENV:-$HOME/.venvs/sequenceconstraint}/bin/docplex"
if [[ -x "$docplex_bin" ]]; then
    "$docplex_bin" config --upgrade "$install_dir"
else
    printf 'Python env not found; after setup_linux.sh run: docplex config --upgrade "%s"\n' "$install_dir"
fi
printf 'CPLEX Optimization Studio: %s\nInstaller log: %s/install.log\n' "$install_dir" "$cache_dir"
