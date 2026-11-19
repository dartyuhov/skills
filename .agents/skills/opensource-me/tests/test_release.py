import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify-release.py"
FAKE_GH = r'''#!PYTHON
import json, os, pathlib, sys
args = sys.argv[1:]
fixture = pathlib.Path(os.environ['GH_FIXTURE'])
with (fixture / 'calls.jsonl').open('a') as log:
    log.write(json.dumps(args) + '\n')
if (fixture / 'fail').exists():
    print('AUTH_TOKEN=never-print-this', file=sys.stderr)
    sys.exit(1)
if args[0] == 'api':
    endpoint = next(a for a in args if a.startswith('repos/'))
    name = 'release.json' if '/releases/tags/' in endpoint else 'repo.json'
    print((fixture / name).read_text())
elif args[:2] == ['release', 'download']:
    dest = pathlib.Path(args[args.index('--dir') + 1])
    name = args[args.index('--pattern') + 1]
    source = fixture / 'assets' / name
    if source.exists():
        (dest / name).write_bytes(source.read_bytes())
    else:
        sys.exit(1)
else:
    sys.exit(9)
'''


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="release tests ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(FAKE_GH.replace("#!PYTHON", "#!" + sys.executable))
        gh.chmod(0o755)
        (self.root / "assets").mkdir()
        self.env = dict(os.environ, PATH=str(self.bin), GH_FIXTURE=str(self.root))
        self.metadata = {"visibility": "public", "private": False, "full_name": "owner/project"}
        self.release: Any = {"tag_name": "v1.0", "draft": False, "prerelease": False,
                        "html_url": "https://github.com/owner/project/releases/tag/v1.0",
                        "published_at": "2026-11-08T12:00:00Z", "assets": []}

    def invoke(self, *args):
        (self.root / "repo.json").write_text(json.dumps(self.metadata))
        (self.root / "release.json").write_text(json.dumps(self.release))
        result = subprocess.run([sys.executable, str(SCRIPT), "--repo", "owner/project",
                                 "--tag", "v1.0", *args], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.stderr, "")
        return result.returncode, json.loads(result.stdout)

    def calls(self):
        path = self.root / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def asset(self, name, content):
        (self.root / "assets" / name).write_bytes(content)
        self.release["assets"].append({"name": name, "state": "uploaded", "size": len(content)})

    def test_source_only_verifies_exact_public_release_without_claiming_installation(self):
        code, data = self.invoke()
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["tag"], "v1.0")
        self.assertEqual(data["installation_verified"], False)
        self.assertEqual(data["assets"], [])
        endpoints = [next(a for a in call if a.startswith("repos/")) for call in self.calls()]
        self.assertEqual(endpoints, ["repos/owner/project", "repos/owner/project/releases/tags/v1.0"])

    def test_rejects_nonpublic_unpublished_or_wrong_release_metadata(self):
        cases = [("repo", "visibility", "private"), ("repo", "private", True),
                 ("repo", "full_name", "other/project"),
                 ("release", "draft", True), ("release", "prerelease", True),
                 ("release", "tag_name", "v2.0"), ("release", "published_at", None),
                 ("release", "draft", None), ("release", "assets", None)]
        for target, key, value in cases:
            with self.subTest(target=target, key=key):
                obj = self.metadata if target == "repo" else self.release
                original = obj[key]
                obj[key] = value
                code, data = self.invoke()
                self.assertNotEqual(code, 0)
                self.assertFalse(data["ok"])
                obj[key] = original

    def test_explicit_prerelease_requires_exact_status_and_reports_observed_status(self):
        self.release["prerelease"] = True
        code, data = self.invoke("--prerelease")
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertTrue(data["public"])
        self.assertIs(data["prerelease"], True)
        self.assertFalse(data["installation_verified"])
        for status in (False, None, 1, "true"):
            with self.subTest(status=status):
                self.release["prerelease"] = status
                code, data = self.invoke("--prerelease")
                self.assertNotEqual(code, 0)
                self.assertFalse(data["ok"])
        self.release["prerelease"] = False
        code, data = self.invoke()
        self.assertEqual(code, 0)
        self.assertIs(data["prerelease"], False)

    def test_invalid_cli_names_are_rejected_before_gh(self):
        cases = [("--expect", "../escape"), ("--expect", "/tmp/escape"),
                 ("--expect", "sub/file"), ("--expect", "back\\slash"),
                 ("--expect", "*.zip"), ("--expect", "file[1]"),
                 ("--expect", "-option"), ("--expect", "line\nbreak"),
                 ("--expect", "a", "--expect", "a"),
                 ("--repo", "../project"), ("--repo", "owner/repo/extra"),
                 ("--host", "evil/host"), ("--host", "-evil"),
                 ("--tag=-option",), ("--tag", "line\nbreak")]
        for args in cases:
            with self.subTest(args=args):
                code, data = self.invoke(*args)
                self.assertNotEqual(code, 0)
                self.assertFalse(data["ok"])
                self.assertEqual(self.calls(), [])

    def test_checksums_require_an_expected_artifact_before_any_gh_request(self):
        code, data = self.invoke("--checksums")
        self.assertNotEqual(code, 0)
        self.assertFalse(data["ok"])
        self.assertFalse(data["installation_verified"])
        self.assertIn("--expect", data["error"])
        self.assertEqual(self.calls(), [])

    def test_unsafe_remote_asset_name_is_rejected_without_downloading(self):
        self.release["assets"] = [{"name": "../escape", "state": "uploaded", "size": 1}]
        code, data = self.invoke()
        self.assertNotEqual(code, 0)
        self.assertFalse(data["ok"])
        self.assertFalse(any(c[:2] == ["release", "download"] for c in self.calls()))

    def test_gh_failure_and_malformed_json_are_sanitized(self):
        (self.root / "fail").touch()
        code, data = self.invoke()
        self.assertNotEqual(code, 0)
        self.assertNotIn("never-print-this", json.dumps(data))
        (self.root / "fail").unlink()
        self.release = []
        code, data = self.invoke()
        self.assertNotEqual(code, 0)
        self.assertFalse(data["ok"])

    def test_expected_artifact_is_downloaded_checked_and_temporary_files_removed(self):
        self.asset("tool mac.zip", b"verified local fixture")
        code, data = self.invoke("--expect", "tool mac.zip", "--host", "git.example.com")
        self.assertEqual(code, 0)
        self.assertEqual(data["assets"], [{"name": "tool mac.zip", "size": 22,
                         "sha256": hashlib.sha256(b"verified local fixture").hexdigest(),
                         "checksum_verified": False}])
        download = next(call for call in self.calls() if call[:2] == ["release", "download"])
        self.assertIn("git.example.com/owner/project", download)
        self.assertFalse(Path(download[download.index("--dir") + 1]).exists())
        self.assertIn("git.example.com", self.calls()[0])

    def test_expected_artifact_missing_incomplete_duplicate_or_truncated_fails(self):
        self.asset("tool.zip", b"abc")
        original = dict(self.release["assets"][0])
        for assets in ([], [dict(original, state="new")], [original, original],
                       [dict(original, size=99)], [dict(original, size=0)]):
            with self.subTest(assets=assets):
                self.release["assets"] = assets
                code, data = self.invoke("--expect", "tool.zip")
                self.assertNotEqual(code, 0)
                self.assertFalse(data["ok"])

    def test_checksum_manifest_and_sidecar_verify_expected_bytes(self):
        self.asset("tool.zip", b"abc")
        self.asset("other.tar.gz", b"hello")
        self.asset("SHA256SUMS", b"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  tool.zip\n")
        self.asset("other.tar.gz.sha256", b"2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824\n")
        for _ in range(2):
            code, data = self.invoke("--expect", "tool.zip", "--expect", "other.tar.gz", "--checksums")
            self.assertEqual(code, 0)
            self.assertTrue(all(a["checksum_verified"] for a in data["assets"]))
            self.assertEqual(data["checksum_assets"], ["SHA256SUMS", "other.tar.gz.sha256"])

    def test_checksum_contract_rejects_missing_mismatch_duplicate_and_unsafe_entries(self):
        self.asset("tool.zip", b"abc")
        valid = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        cases = [None, "0" * 64 + "  tool.zip\n", valid + "  different.zip\n",
                 (valid + "  tool.zip\n") * 2, valid + "  ../tool.zip\n",
                 valid + "  /tmp/tool.zip\n", "not a checksum\n"]
        for text in cases:
            with self.subTest(text=text):
                self.release["assets"] = self.release["assets"][:1]
                if text is not None:
                    self.asset("checksums.txt", text.encode())
                code, data = self.invoke("--expect", "tool.zip", "--checksums")
                self.assertNotEqual(code, 0)
                self.assertFalse(data["ok"])

    def test_agreeing_manifest_and_sidecar_checksums_verify_artifact(self):
        self.asset("tool.zip", b"abc")
        checksum = b"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  tool.zip\n"
        self.asset("SHA256SUMS", checksum)
        self.asset("tool.zip.sha256", checksum)
        code, data = self.invoke("--expect", "tool.zip", "--checksums")
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertTrue(data["public"])
        self.assertTrue(data["assets"][0]["checksum_verified"])
        self.assertEqual(data["checksum_assets"], ["SHA256SUMS", "tool.zip.sha256"])
        self.assertFalse(data["installation_verified"])

    def test_conflicting_manifest_and_sidecar_checksums_fail(self):
        self.asset("tool.zip", b"abc")
        self.asset("SHA256SUMS", b"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  tool.zip\n")
        self.asset("tool.zip.sha256", b"0" * 64 + b"\n")
        code, data = self.invoke("--expect", "tool.zip", "--checksums")
        self.assertNotEqual(code, 0)
        self.assertFalse(data["ok"])
        self.assertIn("conflicting", data["error"])

    def test_incomplete_or_unavailable_checksum_downloads_fail_as_json(self):
        self.asset("tool.zip", b"abc")
        self.asset("SHA256SUMS", b"invalid")
        original = dict(self.release["assets"][1])
        for size in (None, "7", -1, True):
            with self.subTest(size=size):
                self.release["assets"][1] = dict(original, size=size)
                code, data = self.invoke("--expect", "tool.zip", "--checksums")
                self.assertNotEqual(code, 0)
                self.assertFalse(data["ok"])
        self.release["assets"][1] = original
        (self.root / "assets" / "SHA256SUMS").unlink()
        code, data = self.invoke("--expect", "tool.zip", "--checksums")
        self.assertNotEqual(code, 0)
        self.assertFalse(data["ok"])

    def test_missing_gh_and_invalid_json_are_structured_errors(self):
        self.env["PATH"] = ""
        code, data = self.invoke()
        self.assertNotEqual(code, 0)
        self.assertFalse(data["ok"])
        self.env["PATH"] = str(self.bin)
        gh = self.bin / "gh"
        gh.write_text("#!" + sys.executable + "\nprint('not JSON')\n")
        code, data = self.invoke()
        self.assertNotEqual(code, 0)
        self.assertFalse(data["ok"])

    def test_tag_with_slash_is_encoded_for_api_and_literal_for_download(self):
        self.release["tag_name"] = "release/v1.0"
        code, data = self.invoke("--tag", "release/v1.0")
        self.assertEqual(code, 0)
        self.assertIn("repos/owner/project/releases/tags/release%2Fv1.0", self.calls()[1])


if __name__ == "__main__":
    unittest.main()
