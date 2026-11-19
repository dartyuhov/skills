#!/usr/bin/env python3
"""Observe public release metadata and artifact integrity via read-only gh calls."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote


class VerificationError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise VerificationError("invalid command arguments")


def safe_name(name):
    return (isinstance(name, str) and bool(name) and name not in (".", "..")
            and not name.startswith(("-", " ")) and not name.endswith((" ", "."))
            and not any(c in name for c in '/\\*?[]{}:')
            and all(c.isprintable() for c in name))


def verify(args):
    if args.checksums and not args.expect:
        raise VerificationError("--checksums requires at least one --expect artifact")
    parts = args.repo.split("/")
    if (len(parts) != 2 or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", p)
                               or p in (".", "..") for p in parts)):
        raise VerificationError("repo must be OWNER/REPO")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", args.host):
        raise VerificationError("invalid GitHub host")
    if (not args.tag or args.tag.startswith("-")
            or any(not c.isprintable() or c.isspace() for c in args.tag)):
        raise VerificationError("invalid release tag")
    if any(not safe_name(name) for name in args.expect) or len(set(args.expect)) != len(args.expect):
        raise VerificationError("expected asset names must be unique safe literal basenames")

    def gh(*command):
        try:
            result = subprocess.run(["gh", *command], capture_output=True, timeout=120)
        except FileNotFoundError:
            raise VerificationError("gh is unavailable") from None
        except (OSError, subprocess.TimeoutExpired):
            raise VerificationError("gh request could not complete") from None
        if result.returncode:
            raise VerificationError("gh request failed; check authentication, access, and release availability")
        return result.stdout

    def api(endpoint):
        try:
            return json.loads(gh("api", "--hostname", args.host, "--method", "GET", endpoint))
        except (ValueError, UnicodeError):
            raise VerificationError("gh returned invalid JSON") from None

    repo = api("repos/" + args.repo)
    release = api("repos/" + args.repo + "/releases/tags/" + quote(args.tag, safe=""))
    if (not isinstance(repo, dict) or repo.get("visibility") != "public"
            or repo.get("private") is not False
            or str(repo.get("full_name", "")).lower() != args.repo.lower()):
        raise VerificationError("repository metadata does not confirm the requested public repository")
    if (not isinstance(release, dict) or release.get("tag_name") != args.tag
            or release.get("draft") is not False or release.get("prerelease") is not args.prerelease
            or not isinstance(release.get("published_at"), str) or not release["published_at"]
            or not isinstance(release.get("html_url"), str)
            or not isinstance(release.get("assets"), list)):
        raise VerificationError("release metadata does not confirm the exact published release and intended prerelease status")
    assets = {}
    for asset in release["assets"]:
        if not isinstance(asset, dict) or not safe_name(asset.get("name")):
            raise VerificationError("invalid asset metadata")
        if asset["name"] in assets:
            raise VerificationError("duplicate release asset names")
        assets[asset["name"]] = asset
    evidence = []
    checksum_assets = []
    with tempfile.TemporaryDirectory(prefix="verify-release-") as temporary:
        def download(name):
            asset = assets.get(name)
            if (not asset or asset.get("state") != "uploaded"
                    or type(asset.get("size")) is not int or asset["size"] <= 0):
                raise VerificationError("expected asset is missing or incomplete")
            gh("release", "download", args.tag, "--repo", args.host + "/" + args.repo,
               "--pattern", name, "--dir", temporary)
            path = Path(temporary) / name
            if not path.is_file() or path.is_symlink() or path.stat().st_size != asset["size"]:
                raise VerificationError("downloaded asset is missing or has an unexpected size")
            return path

        checksums = {}
        if args.checksums:
            checksum_assets = sorted(name for name in assets if name.lower() in {
                "sha256sums", "sha256sums.txt", "sha256sum.txt", "checksums.txt", "checksums.sha256"}
                or name.lower().endswith((".sha256", ".sha256sum")))
            for name in checksum_assets:
                if (type(assets[name].get("size")) is not int
                        or assets[name]["size"] > 4 * 1024 * 1024):
                    raise VerificationError("checksum asset exceeds supported size")
                path = download(name)
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeError:
                    raise VerificationError("checksum asset is not UTF-8 text") from None
                source_targets = set()
                for line in text.splitlines():
                    if not line.strip():
                        continue
                    match = re.fullmatch(r"([a-fA-F0-9]{64}) [ *](.+)", line)
                    if match:
                        digest, target = match.groups()
                    elif re.fullmatch(r"[a-fA-F0-9]{64}", line.strip()):
                        digest = line.strip()
                        target = re.sub(r"\.(sha256|sha256sum)$", "", name, flags=re.IGNORECASE)
                        if target == name:
                            raise VerificationError("bare checksum requires a named asset sidecar")
                    else:
                        raise VerificationError("invalid SHA-256 checksum entry")
                    if not safe_name(target):
                        raise VerificationError("checksum entry must reference a safe literal basename")
                    if target in source_targets:
                        raise VerificationError("duplicate checksum entries")
                    source_targets.add(target)
                    if target in checksums and checksums[target] != digest.lower():
                        raise VerificationError("conflicting checksum entries")
                    checksums[target] = digest.lower()
        for name in args.expect:
            if name in checksum_assets:
                raise VerificationError("expected artifacts must be distinct from checksum assets")
            path = download(name)
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            if args.checksums and checksums.get(name) != digest.hexdigest():
                raise VerificationError("expected asset checksum is missing or mismatched")
            evidence.append({"name": name, "size": assets[name]["size"], "sha256": digest.hexdigest(),
                             "checksum_verified": args.checksums})
    return {"ok": True, "repo": args.repo, "host": args.host, "tag": args.tag,
            "release_url": release["html_url"], "public": repo["visibility"] == "public",
            "prerelease": release["prerelease"],
            "assets": evidence, "checksum_assets": checksum_assets, "installation_verified": False,
            "limitations": ["Release metadata and artifact evidence only; installation smoke test outstanding."]}


def main():
    parser = Parser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--prerelease", action="store_true",
                        help="require a prerelease (default: require a stable release)")
    parser.add_argument("--expect", action="append", default=[])
    parser.add_argument("--checksums", action="store_true",
                        help="verify SHA-256 checksums; requires at least one --expect")
    parser.add_argument("--host", default="github.com")
    try:
        result = verify(parser.parse_args())
    except VerificationError as exc:
        print(json.dumps({"ok": False, "error": str(exc), "installation_verified": False}))
        return 1
    except OSError:
        print(json.dumps({"ok": False, "error": "local artifact I/O failed",
                          "installation_verified": False}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
