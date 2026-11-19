#!/usr/bin/env python3
"""Read-only Git inventory; reports paths and metadata, never file contents."""

import json
import os
from pathlib import Path
import subprocess
import sys


class InventoryError(Exception):
    pass


def inventory(repo):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    # An explicit path must win over the caller's Git environment.
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(key, None)

    def git(*args, optional=False):
        try:
            result = subprocess.run(["git", "-C", str(repo), *args], env=env,
                                    capture_output=True, timeout=30)
        except FileNotFoundError:
            raise InventoryError("git is unavailable") from None
        except (OSError, subprocess.TimeoutExpired):
            raise InventoryError("git inventory could not complete") from None
        if result.returncode:
            if optional:
                return ""
            raise InventoryError("path is not an accessible Git worktree")
        return result.stdout.decode("utf-8", "replace")

    root = git("rev-parse", "--show-toplevel").rstrip("\n")
    repo = Path(root)
    files = {
        "tracked": git("ls-files", "-z").split("\0")[:-1],
        "untracked": git("ls-files", "--others", "--exclude-standard", "-z").split("\0")[:-1],
        "ignored": git("ls-files", "--others", "--ignored", "--exclude-standard", "-z").split("\0")[:-1],
    }
    paths = sorted(set(files["tracked"] + files["untracked"]))
    stacks = {"node": ("package.json",), "rust": ("Cargo.toml",),
              "python": ("pyproject.toml", "setup.py", "requirements.txt"),
              "swift": ("Package.swift",), "go": ("go.mod",),
              "dotnet": ("global.json",)}
    status_raw = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
    entries = []
    records = iter(status_raw.split("\0")[:-1])
    for record in records:
        entry = {"code": record[:2], "path": record[3:]}
        if "R" in record[:2] or "C" in record[:2]:
            entry["original_path"] = next(records, "")
        entries.append(entry)
    count = git("rev-list", "--count", "HEAD", optional=True).strip()
    return {
        "ok": True, "repo_root": root,
        "worktree": {"git_dir": git("rev-parse", "--absolute-git-dir").strip(),
                     "common_dir": git("rev-parse", "--path-format=absolute", "--git-common-dir").strip(),
                     "branch": git("symbolic-ref", "--short", "HEAD", optional=True).strip() or None},
        "status": {"dirty": bool(entries), "entries": entries},
        "files": files,
        "stack": [name for name, markers in stacks.items() if any(p in paths for p in markers)],
        "key_files": {
            "docs": [p for p in paths if Path(p).name.lower().startswith(
                ("readme", "license", "copying", "contributing", "security", "code_of_conduct", "changelog"))
                or p.startswith("docs/")],
            "config": [p for p in paths if Path(p).name in {
                "package.json", "Cargo.toml", "Cargo.lock", "pyproject.toml", "Package.swift",
                "go.mod", ".gitignore", "release-please-config.json", ".release-please-manifest.json"}
                or p.endswith((".xcodeproj/project.pbxproj", ".csproj", ".sln"))],
            "workflows": [p for p in paths if p.startswith(".github/workflows/")],
        },
        "history": {"commit_count": int(count) if count else 0,
                    "head": git("rev-parse", "--verify", "HEAD", optional=True).strip() or None,
                    "latest_commit_time": git("log", "-1", "--format=%cI", optional=True).strip() or None},
        "limitations": ["Path and Git metadata inventory only; no content or full-history secret scan."]}


def main():
    try:
        if len(sys.argv) != 2:
            raise InventoryError("usage: inspect-repo.py REPO")
        result = inventory(Path(sys.argv[1]).absolute())
    except InventoryError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
