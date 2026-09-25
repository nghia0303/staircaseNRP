#!/usr/bin/env python3
"""Measure the end-to-end wall time of one method process.

The measured boundary starts immediately before ``subprocess.run(command)``
spawns the command and ends immediately after that call returns.  It therefore
includes process creation, program startup, all work performed by the command,
and process shutdown.  It excludes this helper's own startup and argument
parsing, along with writing the elapsed-time and exit-code files.

Usage::

    time_method_process.py --elapsed-file ELAPSED --exit-file EXIT -- COMMAND ...

Elapsed time is written in seconds with nine digits after the decimal point.
If the child is terminated by a signal, its negative ``subprocess`` return code
is normalized to the conventional shell value ``128 + signal_number``.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def write_text_atomic(path: Path, text: str) -> None:
    """Atomically replace *path* with UTF-8 *text*."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def normalized_return_code(return_code: int) -> int:
    """Return a shell-style nonnegative status for a subprocess return code."""

    return return_code if return_code >= 0 else 128 - return_code


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Measure one complete method process with perf_counter_ns.",
        usage=(
            "%(prog)s --elapsed-file PATH --exit-file PATH "
            "-- COMMAND [ARG ...]"
        ),
    )
    parser.add_argument("--elapsed-file", required=True, type=Path)
    parser.add_argument("--exit-file", required=True, type=Path)

    if "--" not in argv:
        if any(item in argv for item in ("-h", "--help")):
            parser.parse_args(argv)
        parser.error("COMMAND must follow a -- separator")

    separator = argv.index("--")
    args = parser.parse_args(argv[:separator])
    command = argv[separator + 1 :]
    if not command:
        parser.error("COMMAND must not be empty")
    return args, command


def main(argv: list[str] | None = None) -> int:
    args, command = parse_args(sys.argv[1:] if argv is None else argv)

    # Prepare directories before the timed boundary.
    args.elapsed_file.parent.mkdir(parents=True, exist_ok=True)
    args.exit_file.parent.mkdir(parents=True, exist_ok=True)

    started_ns = time.perf_counter_ns()
    try:
        completed = subprocess.run(command, check=False)
        return_code = normalized_return_code(completed.returncode)
    except KeyboardInterrupt:
        # A terminal SIGINT normally reaches both this wrapper and its child.
        return_code = 128 + 2
    except FileNotFoundError as error:
        print(f"time_method_process: command not found: {error.filename}", file=sys.stderr)
        return_code = 127
    except PermissionError as error:
        print(f"time_method_process: cannot execute: {error.filename}", file=sys.stderr)
        return_code = 126
    except OSError as error:
        print(f"time_method_process: failed to execute command: {error}", file=sys.stderr)
        return_code = 125
    elapsed_ns = time.perf_counter_ns() - started_ns

    write_text_atomic(args.elapsed_file, f"{elapsed_ns / 1_000_000_000:.9f}\n")
    write_text_atomic(args.exit_file, f"{return_code}\n")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
