"""Validate on an existing Hermes runtime without using its live profile.

Supply the existing source checkout and its selected venv Python explicitly.
This script does not discover credentials, install Hermes, connect remotely, or
start a gateway. It creates and removes only its own temporary directory tree.
"""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def check_runtime(source: Path, python: Path, plugin_source: Path) -> None:
    source = source.resolve(strict=True)
    # Preserve the venv path: resolving the Python symlink would lose its environment.
    python = python.absolute()
    if not (source / "hermes_cli" / "main.py").is_file() or not python.is_file():
        raise ValueError("Supply an existing Hermes source checkout and its venv Python.")
    # macOS may spell the temporary root /var while profile.resolve() uses /private/var.
    scratch = Path(tempfile.mkdtemp(prefix="spoonmaster-check-")).resolve()
    root = scratch / "home"
    root.mkdir()
    temporary = scratch / "tmp"
    temporary.mkdir()
    profile_name = scratch.name
    profile = root / "profiles" / profile_name
    # An explicit allowlist prevents inherited API keys, bot tokens and proxy settings.
    environment = {
        "PATH": f"{python.parent}:/usr/bin:/bin:/usr/sbin:/sbin",
        "HERMES_HOME": str(root),
        "TMPDIR": str(temporary),
        "XDG_CACHE_HOME": str(scratch / "cache"),
        "UV_CACHE_DIR": str(scratch / "cache" / "uv"),
        "PYTHONPATH": str(source),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
        "HERMES_ENABLE_PROJECT_PLUGINS": "0",
        "LANG": "en_US.UTF-8",
    }

    def run(arguments: list[str], *, cwd: Path = source) -> None:
        completed = subprocess.run(
            [str(python), "-B", *arguments],
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
        )
        print(completed.stdout, end="", flush=True)
        if completed.returncode:
            raise RuntimeError(f"Hermes check failed (exit {completed.returncode}).")

    def cli(*arguments: str) -> None:
        run(["-m", "hermes_cli.main", *arguments])

    try:
        print(f"Isolated test root: {scratch}", flush=True)
        run(["--version"])
        cli("--version")
        cli("profile", "create", profile_name, "--no-alias", "--no-skills")
        if (
            not profile.is_dir()
            or profile.is_symlink()
            or not profile.resolve().is_relative_to(root)
        ):
            raise RuntimeError("Profile was not created inside the isolated root.")
        copied = profile / "plugins" / "spoonmaster"
        shutil.copytree(
            plugin_source,
            copied,
            ignore=shutil.ignore_patterns(
                ".git", ".agents", ".venv", "__pycache__", ".ruff_cache", ".pytest_cache", "*.pyc"
            ),
        )
        cli("-p", profile_name, "plugins", "enable", "spoonmaster")
        cli("-p", profile_name, "plugins", "doctor", str(copied), "--ci")
        cli("-p", profile_name, "plugins", "validate", str(copied), "--install-deps")
        # Model-free handler smoke and regression suite using the host's actual Python.
        environment["HERMES_HOME"] = str(profile)
        run(["-m", "unittest", "discover", "-v"], cwd=copied)
        print("PASS: real Hermes registration/validation and model-free tool tests", flush=True)
    finally:
        environment["HERMES_HOME"] = str(root)
        try:
            if profile.exists():
                cli("profile", "delete", profile_name, "--yes")
                if profile.exists():
                    raise RuntimeError("Profile teardown left its directory behind.")
                print(
                    "PASS: named profile and copied plugin absent after profile delete", flush=True
                )
        finally:
            # Delete only the fresh directory owned by this invocation, even after failure.
            shutil.rmtree(scratch)
            if os.path.lexists(scratch):
                raise RuntimeError("Isolated test root remains after cleanup.")
            print("PASS: temporary root, copied files and command caches absent", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    args = parser.parse_args()
    check_runtime(args.source, args.python, Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
