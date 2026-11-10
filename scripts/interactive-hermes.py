"""Owner-authorized temporary CLI testing; never starts a messaging gateway.

Prepare uses a throwaway named profile, then parks it outside the live profile
registry. A home beneath the native Hermes root uses Hermes's supported login
fallback without copying credentials. Cleanup returns it to its isolated registry
for profile deletion. Run cleanup only after the owner finishes testing.
"""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def environment(source: Path, python: Path, home: Path, root: Path) -> dict[str, str]:
    return {
        "PATH": f"{python.parent}:/usr/bin:/bin:/usr/sbin:/sbin",
        "PYTHONPATH": str(source),
        "HERMES_HOME": str(home),
        "HERMES_ENABLE_PROJECT_PLUGINS": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
        "LANG": "en_US.UTF-8",
        "TERM": os.environ.get("TERM", "xterm-256color"),
        "TMPDIR": str(root / "tmp"),
        "XDG_CACHE_HOME": str(root / "cache"),
        "UV_CACHE_DIR": str(root / "cache" / "uv"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "chat", "check", "cleanup"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--query")
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    python = args.python.absolute()
    root = args.root.absolute()
    if root.parent != Path.home() / ".hermes" or not root.name.startswith("spoonmaster-test-"):
        raise ValueError("Use a new spoonmaster-test-* directory directly beneath ~/.hermes")
    if root.is_symlink():
        raise ValueError("Test root cannot be a symlink")
    # Gateway ownership is inferred from this layout; an arbitrary /home path
    # falls back to "default" and conflicts with the owner's live gateway.
    home = root / "profiles" / root.name
    marker = root / "test-owner.json"

    def cli(target: Path, *arguments: str) -> None:
        child_env = environment(source, python, target, root)
        if target == home:
            # Fail before any gateway action if a host upgrade changes identity inference.
            subprocess.run(
                [
                    str(python),
                    "-B",
                    "-c",
                    "import os, sys; from gateway.host_attach import profile_name_for_home; "
                    "actual = profile_name_for_home(os.environ['HERMES_HOME']); "
                    "sys.exit(0 if actual == sys.argv[1] else 'Test profile identity mismatch')",
                    root.name,
                ],
                cwd=root,
                env=child_env,
                check=True,
            )
        subprocess.run(
            [str(python), "-B", "-m", "hermes_cli.main", *arguments],
            cwd=root,
            env=child_env,
            check=True,
        )

    if args.action == "prepare":
        root.mkdir(mode=0o700)
        (root / ".env").touch(mode=0o600)
        (root / "profiles").mkdir()
        (root / "tmp").mkdir()
        staging = Path(tempfile.mkdtemp(prefix="spoonmaster-interactive-")).resolve()
        name = root.name
        marker.write_text(json.dumps({"staging": str(staging), "profile": name}))
        cli(staging, "profile", "create", name, "--no-alias", "--no-skills")
        shutil.move(str(staging / "profiles" / name), home)
        (home / "gateway.parked").touch()
        # Only public routing names are seeded. No .env, auth, memories or skills copied.
        import sys

        sys.path.insert(0, str(source))
        from hermes_cli.config import atomic_config_write, read_user_config_raw

        original = read_user_config_raw(Path.home() / ".hermes" / "config.yaml")
        model = original.get("model", {})
        if not isinstance(model, dict) or model.get("provider") != "openai-codex":
            raise ValueError("This harness requires the existing openai-codex login provider")
        web = original.get("web", {})
        atomic_config_write(
            home / "config.yaml",
            {
                "model": {"default": model["default"], "provider": "openai-codex"},
                "web": {k: web[k] for k in ("search_backend", "extract_backend") if web.get(k)},
                "gateway": {"standalone": True},
            },
        )
        plugin = home / "plugins" / "spoonmaster"
        shutil.copytree(
            Path(__file__).resolve().parents[1],
            plugin,
            ignore=shutil.ignore_patterns(".git", ".agents", ".venv", "__pycache__", ".ruff_cache"),
        )
        cli(home, "plugins", "enable", "spoonmaster")
        cli(home, "plugins", "doctor", str(plugin), "--ci")
        cli(home, "plugins", "validate", str(plugin), "--install-deps")
        print("INSTALLED: run check before hands-on testing; cleanup remains explicit")
        return

    receipt = json.loads(marker.read_text())
    staging = Path(receipt["staging"])
    if staging.parent != Path(tempfile.gettempdir()).resolve() or not staging.name.startswith(
        "spoonmaster-interactive-"
    ):
        raise ValueError("Unexpected staging root; refusing cleanup")
    if args.action == "cleanup":
        destination = staging / "profiles" / receipt["profile"]
        if home.exists():
            cli(home, "gateway", "stop")
            shutil.move(str(home), destination)
        if destination.exists():
            cli(staging, "profile", "delete", receipt["profile"], "--yes")
        if destination.exists():
            raise RuntimeError("Profile deletion did not complete")
        shutil.rmtree(staging)
        shutil.rmtree(root)
        print("CLEAN: profile, plugin, conversations and test caches removed")
        return
    arguments = ["chat", "--ignore-rules", "-t", "web,spoonmaster"]
    if args.action == "check":
        arguments += ["--oneshot", "-q", args.query or "Reply with TEST_READY only."]
    cli(home, *arguments)


if __name__ == "__main__":
    main()
