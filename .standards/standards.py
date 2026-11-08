#!/usr/bin/env python3
"""Plain Git hook support. No network, dependency installs, or index edits."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

KIT = Path(__file__).resolve().parent
CODE = {".js", ".cjs", ".mjs", ".jsx", ".ts", ".cts", ".mts", ".tsx", ".svelte", ".py"}
EXCLUDED = {"vendor", "generated", "archives", "dist", "node_modules", ".venv", ".standards"}
DOCS = {".md", ".mdx", ".rst", ".txt"}
EVENTS = {
    "applypatch-msg",
    "pre-applypatch",
    "post-applypatch",
    "pre-commit",
    "pre-merge-commit",
    "prepare-commit-msg",
    "commit-msg",
    "post-commit",
    "pre-rebase",
    "post-checkout",
    "post-merge",
    "pre-push",
    "pre-receive",
    "update",
    "proc-receive",
    "post-receive",
    "post-update",
    "reference-transaction",
    "push-to-checkout",
    "pre-auto-gc",
    "post-rewrite",
    "sendemail-validate",
    "fsmonitor-watchman",
    "p4-changelist",
    "p4-prepare-changelist",
    "p4-post-changelist",
    "p4-pre-submit",
}


def run(args, cwd=None, capture=False, check=True):
    return subprocess.run(args, cwd=cwd, check=check, stdout=subprocess.PIPE if capture else None)


def git(*args, root=None):
    return run(["git", *args], cwd=root, capture=True).stdout


def root_dir():
    return Path(os.fsdecode(git("rev-parse", "--show-toplevel")).strip())


def config(key, root):
    result = run(["git", "config", "--get", key], cwd=root, capture=True, check=False)
    return os.fsdecode(result.stdout).strip() if result.returncode == 0 else ""


def files(root, staged):
    args = (
        ("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
        if staged
        else ("ls-files", "-z")
    )
    return [os.fsdecode(p) for p in git(*args, root=root).split(b"\0") if p]


def selected(paths):
    return [p for p in paths if Path(p).suffix in CODE and not EXCLUDED.intersection(Path(p).parts)]


def binary(root, name):
    candidate = root / (f".venv/bin/{name}" if name == "ruff" else f"node_modules/.bin/{name}")
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise ValueError(f"Missing pinned local tool: {candidate.relative_to(root)}")
    return str(candidate.resolve())


def check_files(root, snapshot, paths):
    paths = selected(paths)
    js = [p for p in paths if Path(p).suffix != ".py"]
    py = [p for p in paths if Path(p).suffix == ".py"]
    if js:
        for required in (".prettierrc.json", "eslint.config.mjs", "package.json"):
            if not (snapshot / required).is_file():
                raise ValueError(f"Missing staged configuration: {required}")
        if (snapshot / "node_modules").exists():
            raise ValueError("node_modules must be untracked")
        (snapshot / "node_modules").symlink_to(root / "node_modules", target_is_directory=True)
        run([binary(root, "prettier"), "--check", "--", *js], cwd=snapshot)
        run([binary(root, "eslint"), "--no-warn-ignored", "--", *js], cwd=snapshot)
    if py:
        if not (snapshot / "ruff.toml").is_file():
            raise ValueError("Missing staged configuration: ruff.toml")
        run([binary(root, "ruff"), "format", "--check", "--", *py], cwd=snapshot)
        run([binary(root, "ruff"), "check", "--no-cache", "--", *py], cwd=snapshot)


def enforcement_probes(root, snapshot, paths):
    if any(Path(p).suffix != ".py" for p in selected(paths)):
        probes = [
            ("long.ts", "const " + "identifier" * 14 + " = 1;\n", "@stylistic/max-len"),
            ("chain.js", "let first = 1; let second = 2;\n", "@stylistic/max-statements-per-line"),
            (
                "dense.tsx",
                "const view = <div><span>one</span><span>two</span></div>;\n",
                "@stylistic/jsx-one-expression-per-line",
            ),
        ]
        for name, content, rule in probes:
            path = snapshot / name
            path.write_text(content)
            result = run(
                [binary(root, "eslint"), "--format", "json", name],
                cwd=snapshot,
                capture=True,
                check=False,
            )
            findings = json.loads(result.stdout or b"[]")
            if not any(
                m.get("ruleId") == rule and m.get("severity") == 2
                for file in findings
                for m in file["messages"]
            ):
                raise ValueError(f"Enforcement probe failed: {rule}")
            path.unlink()
    if any(Path(p).suffix == ".py" for p in selected(paths)):
        path = snapshot / "long.py"
        path.write_text("identifier" * 11 + " = 1\n")
        result = run(
            [binary(root, "ruff"), "check", "--no-cache", "--output-format", "json", path.name],
            cwd=snapshot,
            capture=True,
            check=False,
        )
        if not any(m["code"] == "E501" for m in json.loads(result.stdout or b"[]")):
            raise ValueError("Enforcement probe failed: E501")
        path.unlink()
    print("PASS: applicable readability rules reject bad fixtures")


def snapshot_check(root, staged):
    paths = files(root, staged)
    with tempfile.TemporaryDirectory(prefix="standards-index-") as folder:
        snapshot = Path(folder)
        git("checkout-index", "--all", f"--prefix={snapshot}/", root=root)
        # Config symlinks could escape the index and load unstaged executable config.
        for name in (".prettierrc.json", "eslint.config.mjs", "ruff.toml", ".prettierignore"):
            if (snapshot / name).is_symlink():
                raise ValueError(f"Configuration must be a regular tracked file: {name}")
        check_files(root, snapshot, paths)
        if not staged:
            enforcement_probes(root, snapshot, paths)
    label = "staged" if staged else "tracked index"
    print(f"PASS: {label} checks ({len(selected(paths))} code files)")


def headings_ok(message, needed):
    lines = message.splitlines()[1:]
    found = {}
    current = None
    for line in lines:
        heading = re.fullmatch(
            r"(Why|Changed|Verified|Limits|Origin(?: / authority)?|Recovery|Follow-up):\s*(.*)",
            line,
        )
        if heading:
            current = heading[1]
            found[current] = bool(heading[2].strip())
        elif line.strip() and current:
            found[current] = True
    return all(found.get(name) for name in needed)


def open_ancestor_scripts():
    """Inspect paths only, never process arguments or credential values."""
    pid = os.getppid()
    for _ in range(32):
        if pid <= 1:
            break
        proc = Path(f"/proc/{pid}/fd")
        if proc.is_dir():
            for fd in proc.iterdir():
                try:
                    yield fd.resolve(strict=True)
                except (OSError, RuntimeError):
                    pass
        elif shutil.which("lsof"):
            result = subprocess.run(
                ["lsof", "-a", "-p", str(pid), "-d", "255", "-Fn"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            for line in os.fsdecode(result.stdout).splitlines():
                if line.startswith("n/"):
                    yield Path(line[1:]).resolve()
        parent = run(
            ["ps", "-o", "ppid=", "-p", str(pid)], capture=True, check=False
        ).stdout.strip()
        if not parent.isdigit():
            break
        pid = int(parent)


def automation_exception(root, message, paths):
    # This policy list is copied from the single reviewed inventory at adoption.
    inventory = root / ".standards/AUTOMATED-COMMITS.md"
    evidence = root / ".standards/AUTOMATED-COMMITS-EVIDENCE.json"
    if not inventory.is_file() or not evidence.is_file():
        return False
    data = json.loads(evidence.read_text())
    records = []

    def collect(value):
        if isinstance(value, dict):
            if "path" in value and "sha256" in value:
                records.append(value)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(data)
    ancestors = set(open_ancestor_scripts())
    for row in inventory.read_text().splitlines():
        if not row.startswith("| "):
            continue
        cells = row.split("|")[1:-1]
        if len(cells) != 3:
            continue
        named = re.findall(r"`([^`]+)`", cells[0])
        forms = re.findall(r"`([^`]+)`", cells[1])
        if not named or not forms:
            continue
        source = named[0]
        source_suffix = source.lstrip("~/")
        matches = [p for p in ancestors if str(p).endswith("/" + source_suffix)]
        for script in matches:
            sha = hashlib.sha256(script.read_bytes()).hexdigest()
            if not any(
                r["sha256"] == sha and r["path"].endswith("/" + source_suffix) for r in records
            ):
                continue
            if "no body" in cells[1] and message.strip() == forms[0]:
                # The reviewed script's configured brief directory is the allowed scope.
                scope = re.search(
                    r'BRIEF_DIR="\$\{BIGGIE_HQ_BRIEF_DIR:-([^}]+)\}"', script.read_text()
                )
                if scope and os.environ.get("BIGGIE_HQ_BRIEF_DIR", scope[1]) == scope[1]:
                    return bool(paths) and all(p.startswith(scope[1] + "/") for p in paths)
            # Inventory metadata form: subject, Payload, Origin, exact Verification.
            payload = next((i for i, f in enumerate(forms) if f.startswith("Payload: ")), None)
            if payload is None or payload == 0 or len(forms) < payload + 3:
                continue
            if message.splitlines()[0] != forms[payload - 1]:
                continue
            body = [s.strip() for s in message.splitlines()[1:] if s.strip()]
            expected = forms[payload : payload + 3]
            patterns = [
                re.escape(s)
                .replace(re.escape("<payload_commit>"), r"[0-9a-f]{40,64}")
                .replace(re.escape("<origin_label>"), r"[^\r\n]+")
                for s in expected
            ]
            if len(body) == 3 and all(re.fullmatch(p, b) for p, b in zip(patterns, body)):
                return bool(paths) and set(paths) == {".canon/status.json"}
    return False


def commit_message(root, filename):
    comment = config("core.commentChar", root) or "#"
    lines = Path(filename).read_text().splitlines()
    message = "\n".join(line for line in lines if not line.startswith(comment)).strip()
    paths = [
        os.fsdecode(p)
        for p in git("diff", "--cached", "--name-only", "-z", root=root).split(b"\0")
        if p
    ]
    merge = Path(os.fsdecode(git("rev-parse", "--git-path", "MERGE_HEAD", root=root)).strip())
    revert = Path(os.fsdecode(git("rev-parse", "--git-path", "REVERT_HEAD", root=root)).strip())
    if not merge.is_absolute():
        merge = root / merge
    if not revert.is_absolute():
        revert = root / revert
    if merge.is_file():
        return
    if revert.is_file() and re.search(r"^This reverts commit [0-9a-f]{40,64}\.$", message, re.M):
        return
    needed = (
        ("Why", "Changed")
        if paths and all(Path(p).suffix in DOCS for p in paths)
        else ("Why", "Changed", "Verified")
    )
    if headings_ok(message, needed) or automation_exception(root, message, paths):
        return
    raise ValueError("Commit body requires nonempty " + "/".join(needed) + " sections")


def previous_hook(root, event, args):
    previous = config("standards.previousHooksPath", root)
    if previous:
        hook = Path(previous) / event
        if hook.is_file() and os.access(hook, os.X_OK):
            run([str(hook), *args], cwd=root)


def hook(root, event, args):
    before = git("ls-files", "--stage", "-z", root=root)
    previous_hook(root, event, args)
    if event == "pre-commit":
        if git("ls-files", "--stage", "-z", root=root) != before:
            raise ValueError("Preserved hook changed the index; review/restage and retry")
        snapshot_check(root, True)
    elif event == "commit-msg":
        commit_message(root, args[0])


def wrapper(event):
    weight = (
        "0.5-3s plus file volume, formatter/linter startup"
        if event == "pre-commit"
        else "<100ms normally; up to 1s for named-automation proof"
        if event == "commit-msg"
        else "~30-100ms Python startup plus preserved hook cost"
    )
    return (
        "#!/bin/sh\n# standards-kit: preserve previous hook, then enforce adopted rules\n"
        f"# Weight: {event}: {weight}; preserved hooks add their existing cost.\n"
        'exec python3 "$(git rev-parse --show-toplevel)/.standards/standards.py" '
        f'hook {event} "$@"\n'
    )


def setup(root):
    active = config("core.hooksPath", root)
    default = Path(os.fsdecode(git("rev-parse", "--git-path", "hooks", root=root)).strip())
    old = Path(active).expanduser() if active else default
    if not old.is_absolute():
        old = root / old
    target = root / ".githooks"
    hooks = (
        [p for p in old.iterdir() if p.name in EVENTS and p.is_file() and os.access(p, os.X_OK)]
        if old.is_dir()
        else []
    )
    for location in {old, root / ".git/hooks", root / ".husky"}:
        if location.is_dir():
            names = sorted(
                p.name for p in location.iterdir() if p.is_file() and not p.name.endswith(".sample")
            )
            print(f"Found {location}: {', '.join(names) or '(no active hook files)'}")
    existing = list(target.iterdir()) if target.is_dir() else []
    for path in existing:
        if path.name not in EVENTS or path.is_symlink() or path.read_text() != wrapper(path.name):
            raise ValueError("Existing .githooks requires reviewed migration; nothing overwritten")
    if old.resolve() == target.resolve():
        if not {"pre-commit", "commit-msg"}.issubset({p.name for p in existing}):
            raise ValueError("Active .githooks is missing required wrappers; review migration")
        print(
            "Hooks already installed; preserved path: "
            + config("standards.previousHooksPath", root)
        )
        return
    target.mkdir(exist_ok=True)
    for event in (
        {"pre-commit", "commit-msg"} | {p.name for p in hooks} | {p.name for p in existing}
    ):
        destination = target / event
        destination.write_text(wrapper(event))
        destination.chmod(0o755)
    git("config", "--local", "standards.previousHooksPath", str(old.resolve()), root=root)
    git("config", "--local", "core.hooksPath", ".githooks", root=root)
    git("config", "--local", "commit.template", ".standards/commit-template.txt", root=root)
    print("Kept unchanged and chained: " + (", ".join(p.name for p in hooks) or "none"))
    print("Other hook directories remain unchanged; only the formerly active hooks are chained")


def front_door(root):
    """Report the lean front door without changing files or the Git index."""
    gaps = []

    def report(ok, label):
        print(("PASS: " if ok else "GAP: ") + label)
        if not ok:
            gaps.append(label)

    report((root / "README.md").is_file(), "front door README.md exists")
    agents = root / "AGENTS.md"
    text = agents.read_text() if agents.is_file() else ""
    lines = [line for line in text.splitlines() if line.strip()]
    title = next((i for i, line in enumerate(lines) if re.match(r"^# ", line)), -1)
    opening = lines[title + 1 : title + 21]
    reading_heading = re.search(
        r"^#+ .*(read(ing)? (in )?order|read first|start here)", text, re.I | re.M
    )
    reading_sentence = any(
        re.match(r"^(Read |1\. Read )", line)
        and re.search(r"\[[^\]\n]+\]\([^)\n]+\)", line)
        for line in opening
    )
    report(
        agents.is_file() and bool(reading_heading or reading_sentence),
        "front door AGENTS.md has a reading order",
    )
    match = re.search(
        r"^Standards baseline: (adopted|deferred|declined) (\d{4}-\d{2}-\d{2})\b",
        text, re.M,
    )
    decision = match.group(1) + " " + match.group(2) if match else None
    report(bool(decision), "front door Standards baseline: " + (decision or "missing"))
    states = [root / p for p in ("CURRENT_STATE.md", "CURRENT-STATE.md", "STATUS.md")
              if (root / p).is_file()]
    sizes = [(p.name, sum(bool(line.strip()) for line in p.read_text().splitlines()))
             for p in states]
    report(
        len(states) <= 1 and all(size <= 40 for _, size in sizes),
        "front door at most one state file, at most 40 non-blank lines: "
        + (", ".join(f"{name} ({size})" for name, size in sizes) or "none"),
    )
    trackers = [p for p in ("TRACKER.md", "docs/plan.md", "TODO.md", "TASKS.md",
                            "TASK.md", "checklist.md") if (root / p).is_file()]
    report(len(trackers) <= 1, "front door at most one tracker: "
           + (", ".join(trackers) or "none"))
    if (root / ".ralph/fix_plan.md").is_file():
        print("INFO: .ralph/fix_plan.md is loop-scoped; the repo tracker stays authoritative")
    pattern = re.compile(
        r"\b(STOP(ped)? before|not (yet )?pushed|awaiting (push|review)|"
        r"handoff \d|step \d+ (complete|done))", re.I,
    )
    hits = []
    for path in [root / "README.md", *states, root / "TRACKER.md"]:
        if path.is_file():
            hits.extend(f"{path.name}:{number}" for number, line in
                        enumerate(path.read_text().splitlines(), 1) if pattern.search(line))
    report(not hits, "front door active docs have no handoff/STOP/push state"
           + (": " + ", ".join(hits) if hits else ""))
    return decision, gaps


def baseline(root):
    agents = root / "AGENTS.md"
    text = agents.read_text() if agents.is_file() else ""
    recorded = bool(re.search(
        r"^Standards baseline: (deferred|declined) \d{4}-\d{2}-\d{2}\b", text, re.M
    ))
    # Recorded decisions retain all diagnostics, but gaps are informational.
    if recorded:
        import contextlib
        import io

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            decision, gaps = front_door(root)
        print(output.getvalue().replace("GAP: ", "INFO: "), end="")
    else:
        decision, gaps = front_door(root)
    paths = selected(files(root, False))
    required = [
        ".standards/commit-template.txt",
        ".githooks/pre-commit",
        ".githooks/commit-msg",
    ]
    if any(Path(p).suffix != ".py" for p in paths):
        required += [".prettierrc.json", "eslint.config.mjs", "package.json"]
    if any(Path(p).suffix == ".py" for p in paths):
        required += ["ruff.toml"]
    missing = [p for p in required if not (root / p).is_file()]
    if config("core.hooksPath", root) != ".githooks":
        missing.append("active core.hooksPath .githooks")
    if config("commit.template", root) != ".standards/commit-template.txt":
        missing.append("active commit.template .standards/commit-template.txt")
    for event in ("pre-commit", "commit-msg"):
        path = root / ".githooks" / event
        if not path.is_file() or not os.access(path, os.X_OK) or path.read_text() != wrapper(event):
            missing.append(f"active executable kit wrapper: {event}")
    if paths and not re.search(r"^#+ .*code.style", text, re.I | re.M):
        missing.append("AGENTS.md code-style section")
    for path in required:
        print(("INFO: " if recorded and path in missing else
               "GAP: " if path in missing else "PASS: ") + path)
    for gap in missing:
        if gap not in required:
            print(("INFO: " if recorded else "GAP: ") + gap)
    if not missing:
        try:
            snapshot_check(root, False)
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            gaps.append("code enforcement: " + str(error))
            print(("INFO: " if recorded else "GAP: ") + gaps[-1])
    if recorded:
        print(f"RECORDED {decision}: no offer")
        return
    if decision is None:
        raise ValueError("NO DECISION: make the one-time R7 offer")
    if missing or gaps:
        raise ValueError("Baseline incomplete: " + ", ".join(missing + gaps))

def main():
    started = time.monotonic()
    root = root_dir()
    mode = sys.argv[1]
    if mode == "setup":
        setup(root)
    elif mode == "check":
        if sys.argv[2:] == ["--staged"]:
            snapshot_check(root, True)
        elif sys.argv[2:]:
            raise ValueError("Usage: check-standards.sh [--staged]")
        else:
            baseline(root)
    elif mode == "hook":
        hook(root, sys.argv[2], sys.argv[3:])
    else:
        raise ValueError("Unknown operation")
    print(f"Standards {mode}: {time.monotonic() - started:.3f}s")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print("FAIL: " + str(error), file=sys.stderr)
        sys.exit(1)
