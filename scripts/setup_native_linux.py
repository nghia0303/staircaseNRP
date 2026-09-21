#!/usr/bin/env python3
"""Install pinned Picat and build the project's MiniCPP frontends on Linux."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile

REPO = Path(__file__).resolve().parents[1]
COMMIT = "9bf9110059c1e883efbc97d79640486c1cd5d8b2"
PICAT_URL = "https://picat-lang.org/download/picat39_12_linux64.tar.gz"
PICAT_SHA = "f053b11cccabfb69a3ccd779f2dc1c24cdf889805799bc8c779e6c56da703e4a"


def run(*args, **kwargs):
    print("+", " ".join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise SystemExit("This profile requires Linux x86_64.")
    for cmd in ("curl", "git", "cmake", "g++", "make"):
        if not shutil.which(cmd):
            raise SystemExit(f"Missing dependency: {cmd}")
    prefix = Path(os.environ.get("NRP_NATIVE_HOME", Path.home() / ".local/opt/sequenceconstraint")).expanduser().resolve()
    cache = Path.home() / ".cache/sequenceconstraint/native"
    cache.mkdir(parents=True, exist_ok=True)
    prefix.mkdir(parents=True, exist_ok=True)
    archive = cache / "picat39_12_linux64.tar.gz"
    if not archive.exists():
        partial = archive.with_suffix(".part")
        run("curl", "--fail", "--location", "--retry", "3", PICAT_URL, "-o", partial)
        partial.replace(archive)
    if digest(archive) != PICAT_SHA:
        raise SystemExit("Picat archive SHA256 mismatch; refusing installation.")
    picat_root = prefix / "picat-3.9-12"
    if not (picat_root / "Picat/picat").exists():
        picat_root.mkdir(exist_ok=True)
        with tarfile.open(archive) as tar:
            tar.extractall(picat_root, filter="data")
    picat = picat_root / "Picat/picat"
    run(picat, "-g", "halt")

    patches = [REPO / "native/minicpp" / name for name in ("project-frontends.patch", "engine-defaults.patch")]
    patch_sha = hashlib.sha256(b"".join(patch.read_bytes() for patch in patches)).hexdigest()
    git_dir = cache / "minicpp-bitbucket"
    if not git_dir.exists():
        run("git", "clone", "--no-checkout", "https://bitbucket.org/ldmbouge/minicpp.git", git_dir)
    run("git", "-C", git_dir, "cat-file", "-e", COMMIT + "^{commit}")
    native_root = prefix / ("minicpp-" + COMMIT[:12] + "-" + patch_sha[:12])
    source = native_root / "source"
    build = native_root / "build"
    if not (source / ".project-patch-applied").exists():
        if source.exists():
            raise SystemExit(f"Incomplete source directory; inspect before retry: {source}")
        source.mkdir(parents=True)
        source_tar = cache / (COMMIT + ".tar")
        with source_tar.open("wb") as out:
            run("git", "-C", git_dir, "archive", COMMIT, stdout=out)
        with tarfile.open(source_tar) as tar:
            tar.extractall(source, filter="data")
        for patch in patches:
            run("git", "apply", "--unidiff-zero", "--check", patch, cwd=source)
            run("git", "apply", "--unidiff-zero", patch, cwd=source)
        (source / ".project-patch-applied").write_text(patch_sha + "\n")
    build_log = native_root / "build.log"
    print(f"CMake/build output: {build_log}", flush=True)
    with build_log.open("a") as out:
        try:
            run("cmake", "-S", source, "-B", build, "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_CXX_COMPILER=g++", stdout=out, stderr=subprocess.STDOUT)
            run("cmake", "--build", build, "--target", "amongNurse", "sequenceNurse", "sequenceNurseNew", "--parallel", os.environ.get("NRP_BUILD_JOBS", "2"), stdout=out, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            out.flush()
            print("\n".join(build_log.read_text(errors="replace").splitlines()[-50:]))
            raise
    bin_dir = prefix / "bin"
    bin_dir.mkdir(exist_ok=True)
    binaries = {"picat": picat, **{name: build / name for name in ("amongNurse", "sequenceNurse", "sequenceNurseNew")}}
    for name, target in binaries.items():
        link = bin_dir / name
        if link.exists() and not link.is_symlink():
            raise SystemExit(f"Refusing to overwrite non-symlink: {link}")
        if link.is_symlink():
            link.unlink()
        link.symlink_to(target)
    manifest = {
        "picat_version": "3.9#12", "picat_url": PICAT_URL, "picat_archive_sha256": PICAT_SHA,
        "minicpp_repository": "https://bitbucket.org/ldmbouge/minicpp.git",
        "minicpp_commit": COMMIT, "project_patch_sha256": patch_sha,
        "patches": {patch.name: digest(patch) for patch in patches},
        "build_type": "Release", "build_log": str(build_log), "compiler": subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
        "binaries": {name: {"path": str(path), "sha256": digest(path)} for name, path in binaries.items()},
    }
    (prefix / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Installed native solvers. Source {REPO / 'scripts/linux_env.sh'} to use them.")


if __name__ == "__main__":
    main()
