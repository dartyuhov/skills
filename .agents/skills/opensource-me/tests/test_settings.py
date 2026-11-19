"""CLI integration tests: only the external gh executable is substituted."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/github-settings.py"
REPO = "repos/owner/project"
SHA = "a" * 40
FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
state_path = Path(os.environ["GH_STATE"])
state = json.loads(state_path.read_text())
args = sys.argv[1:]
assert args[0] == "api", args
method = args[args.index("--method") + 1]
endpoint = args[1]
payload = json.load(sys.stdin) if "--input" in args else None
call = {"method": method, "endpoint": endpoint, "payload": payload, "args": args}
with open(os.environ["GH_LOG"], "a") as log:
    log.write(json.dumps(call) + "\n")
key = method + " " + endpoint
failure = state.get("failures", {}).get(key)
if failure:
    print(failure, file=sys.stderr)
    sys.exit(1)
if method != "GET":
    if endpoint not in state.get("stale", []):
        state["responses"][endpoint].update(payload)
        if method == "PUT" and endpoint.endswith("/protection"):
            protection = state["responses"][endpoint]
            for field in ("enforce_admins", "allow_force_pushes", "allow_deletions", "required_linear_history"):
                protection[field] = {"enabled": payload[field], "url": "https://example.invalid"}
            protection["required_status_checks"]["contexts"] = [c["context"] for c in payload["required_status_checks"]["checks"]]
            protection["required_pull_request_reviews"]["dismiss_stale_reviews"] = False
            state.get("failures", {}).pop("GET " + endpoint, None)
            for field, value in state.get("protection_overrides", {}).items():
                protection[field] = value
        state_path.write_text(json.dumps(state))
    if endpoint in state.get("malformed_readback", []):
        state["responses"][endpoint] = []
        state_path.write_text(json.dumps(state))
response = state["responses"].get(endpoint)
if response is None:
    print("gh: unexpected endpoint " + endpoint, file=sys.stderr)
    sys.exit(1)
print(json.dumps(response))
'''


class SettingsCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        gh = self.root / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        self.state_path = self.root / "state.json"
        self.log_path = self.root / "calls.jsonl"
        self.state: dict[str, Any] = {"responses": {
            REPO: {"description": "Old", "default_branch": "main", "private": True,
                   "allow_merge_commit": True, "allow_rebase_merge": True,
                   "allow_squash_merge": False, "has_issues": True},
            REPO + "/topics": {"names": ["existing"]},
            REPO + "/branches/main/protection": {
                "required_status_checks": {"strict": True, "contexts": ["legacy"],
                                           "checks": [{"context": "legacy", "app_id": 9}]},
                "enforce_admins": {"enabled": True},
                "required_pull_request_reviews": {"required_approving_review_count": 2},
                "restrictions": {"users": [{"login": "maintainer"}]}},
            REPO + "/rulesets?includes_parents=true&per_page=100&page=1": [],
            REPO + "/rules/branches/main?per_page=100&page=1": [],
        }}

    def run_cli(self, *args):
        self.state_path.write_text(json.dumps(self.state))
        env = dict(os.environ, PATH=str(self.root) + os.pathsep + os.environ["PATH"],
                   GH_STATE=str(self.state_path), GH_LOG=str(self.log_path))
        result = subprocess.run([sys.executable, str(SCRIPT), "--repo", "owner/project", *args],
                                env=env, text=True, capture_output=True)
        self.state = json.loads(self.state_path.read_text())
        self.assertTrue(result.stdout, result.stderr)
        return result.returncode, json.loads(result.stdout)

    def calls(self):
        return [json.loads(line) for line in self.log_path.read_text().splitlines()] if self.log_path.exists() else []

    def checks(self, event="pull_request"):
        self.state["responses"].update({
            REPO + f"/commits/{SHA}/check-runs?filter=latest&per_page=100&page=1": {
                "check_runs": [{"id": 10, "name": "test", "head_sha": SHA,
                                "status": "completed", "conclusion": "success",
                                "app": {"id": 15368}, "check_suite": {"id": 20}}]},
            REPO + "/check-suites/20": {"id": 20, "head_sha": SHA, "app": {"id": 15368}},
            REPO + f"/actions/runs?check_suite_id=20&head_sha={SHA}&per_page=100&page=1": {
                "workflow_runs": [{"id": 30, "check_suite_id": 20, "head_sha": SHA,
                                   "event": event, "status": "completed", "conclusion": "success"}]},
            REPO + "/branches/main/protection/required_status_checks":
                self.state["responses"][REPO + "/branches/main/protection"]["required_status_checks"],
        })

    def test_protection_adds_observed_pr_check_preserving_existing_controls(self):
        self.checks()
        before = json.loads(json.dumps(self.state["responses"][REPO + "/branches/main/protection"]))
        code, result = self.run_cli("--protect", "main", "--checks-from", SHA, "--apply")
        self.assertEqual(code, 0, result)
        writes = [c for c in self.calls() if c["method"] != "GET"]
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]["endpoint"], REPO + "/branches/main/protection/required_status_checks")
        self.assertEqual(writes[0]["payload"], {
            "strict": True, "checks": [{"context": "legacy", "app_id": 9},
                                       {"context": "test", "app_id": 15368}]})
        self.assertEqual(self.state["responses"][REPO + "/branches/main/protection"], before)
        self.assertEqual(result["results"][0]["status"], "verified")

    def test_selected_checks_narrow_new_requirements_and_keep_existing_checks(self):
        self.checks()
        runs = self.state["responses"][REPO + f"/commits/{SHA}/check-runs?filter=latest&per_page=100&page=1"]["check_runs"]
        runs.extend([{**runs[0], "id": 11, "name": "lint"},
                     {**runs[0], "id": 12, "name": "incidental"}])
        code, result = self.run_cli("--protect", "main", "--checks-from", SHA,
                                    "--check", "test", "--check", "lint", "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["plan"][0]["desired"]["checks"], [
            {"context": "legacy", "app_id": 9}, {"context": "lint", "app_id": 15368},
            {"context": "test", "app_id": 15368}])
        self.assertEqual(result["results"][0]["status"], "verified")

    def test_unknown_or_nonqualifying_requested_checks_block_all_writes(self):
        for event, name in (("pull_request", "unknown"), ("workflow_dispatch", "test")):
            with self.subTest(event=event, name=name):
                self.checks(event)
                code, result = self.run_cli("--protect", "main", "--checks-from", SHA,
                                            "--check", name, "--description", "New", "--apply")
                self.assertEqual(code, 1, result)
                self.assertIn("Requested checks lack qualifying", " ".join(result["errors"]))
                self.assertIn(name, " ".join(result["errors"]))
                self.assertTrue(all(c["method"] == "GET" for c in self.calls()))

    def test_check_selection_applies_to_creation_and_ignores_unselected_external_jobs(self):
        self.absent_protection()
        runs = self.state["responses"][REPO + f"/commits/{SHA}/check-runs?filter=latest&per_page=100&page=1"]["check_runs"]
        runs.append({**runs[0], "id": 11, "name": "external", "check_suite": {"id": 999}})
        code, result = self.run_cli("--protect", "main", "--checks-from", SHA,
                                    "--create-protection", "--check", "test", "--check", "test")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["plan"][0]["desired"]["required_status_checks"]["checks"],
                         [{"context": "test", "app_id": 15368}])
        self.assertFalse(any("check-suites/999" in c["endpoint"] for c in self.calls()))
        self.assertTrue(all(c["method"] == "GET" for c in self.calls()))

    def absent_protection(self):
        self.checks()
        self.state["failures"] = {
            "GET " + REPO + "/branches/main/protection": "gh: Branch not protected (HTTP 404)"}

    def test_confirmed_404_creation_plan_is_explicit_and_read_only(self):
        self.absent_protection()
        code, result = self.run_cli("--protect", "main", "--checks-from", SHA, "--create-protection")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["current"]["protection"]["status"], "absent")
        change = result["plan"][0]
        self.assertEqual(change["method"], "PUT")
        self.assertEqual(change["endpoint"], REPO + "/branches/main/protection")
        self.assertEqual(change["desired"], {
            "required_status_checks": {"strict": True, "contexts": [],
                                       "checks": [{"context": "test", "app_id": 15368}]},
            "enforce_admins": True,
            "required_pull_request_reviews": {"required_approving_review_count": 0},
            "restrictions": None, "allow_force_pushes": False, "allow_deletions": False,
            "required_linear_history": True})
        self.assertTrue(all(c["method"] == "GET" for c in self.calls()))

    def test_confirmed_404_creation_applies_and_verifies_nested_response(self):
        self.absent_protection()
        self.state["responses"][REPO + "/branches/main/protection"] = {}
        code, result = self.run_cli("--protect", "main", "--checks-from", SHA, "--create-protection", "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["results"][0]["status"], "verified")
        writes = [c for c in self.calls() if c["method"] != "GET"]
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]["method"], "PUT")
        self.assertEqual(writes[0]["endpoint"], REPO + "/branches/main/protection")
        self.assertEqual(result["results"][0]["readback"]["enforce_admins"]["enabled"], True)

    def test_creation_refuses_403_and_unconfirmed_absence_without_leaking_stderr(self):
        for error in ("gh: secret-token=private (HTTP 403)",
                      "gh: secret-token=private not found 404", "gh: secret-token=private (HTTP 500)"):
            with self.subTest(error=error):
                self.absent_protection()
                self.state["failures"]["GET " + REPO + "/branches/main/protection"] = error
                code, result = self.run_cli("--protect", "main", "--checks-from", SHA,
                                            "--create-protection", "--apply")
                self.assertEqual(code, 1, result)
                self.assertEqual(result["current"]["protection"]["status"], "unknown")
                self.assertNotIn("secret-token", json.dumps(result))
                self.assertIn("API access failed", " ".join(result["errors"]))
                self.assertTrue(all(c["method"] == "GET" for c in self.calls()))

    def test_creation_requires_absence_and_no_effective_or_active_rules(self):
        for kind in ("existing", "active", "effective", "inaccessible_rules"):
            with self.subTest(kind=kind):
                self.absent_protection()
                rulesets = REPO + "/rulesets?includes_parents=true&per_page=100&page=1"
                effective = REPO + "/rules/branches/main?per_page=100&page=1"
                self.state["responses"][rulesets] = []
                self.state["responses"][effective] = []
                if kind == "existing":
                    self.state["failures"] = {}
                elif kind == "active":
                    self.state["responses"][rulesets] = [{"enforcement": "active"}]
                elif kind == "effective":
                    self.state["responses"][effective] = [{"type": "required_signatures"}]
                else:
                    self.state["failures"]["GET " + rulesets] = "gh: forbidden (HTTP 403)"
                code, result = self.run_cli("--protect", "main", "--checks-from", SHA,
                                            "--create-protection", "--apply")
                self.assertEqual(code, 1, result)
                self.assertTrue(result["errors"])
                self.assertTrue(all(c["method"] == "GET" for c in self.calls()))

    def test_creation_rejects_mismatched_nested_readback_fields(self):
        overrides = ({"enforce_admins": {"enabled": False}},
                     {"allow_deletions": {"enabled": True}},
                     {"allow_force_pushes": {"enabled": True}},
                     {"required_linear_history": {}},
                     {"required_pull_request_reviews": {"required_approving_review_count": False}},
                     {"restrictions": {"users": []}},
                     {"required_status_checks": {"strict": False, "contexts": ["test"],
                                                  "checks": [{"context": "test", "app_id": 15368}]}},
                     {"required_status_checks": {"strict": True, "contexts": ["test"],
                                                  "checks": [{"context": "test", "app_id": 42}]}})
        for override in overrides:
            with self.subTest(override=override):
                self.absent_protection()
                self.state["responses"][REPO + "/branches/main/protection"] = {}
                self.state["protection_overrides"] = override
                code, result = self.run_cli("--protect", "main", "--checks-from", SHA,
                                            "--create-protection", "--apply")
                self.assertEqual(code, 1, result)
                self.assertEqual(result["results"][0]["status"], "failed")
                self.assertIn("readback", result["results"][0]["reason"])

    def test_disabled_rulesets_allow_creation_but_manual_checks_do_not(self):
        self.absent_protection()
        self.state["responses"][REPO + "/rulesets?includes_parents=true&per_page=100&page=1"] = [
            {"id": 1, "enforcement": "disabled"}]
        code, result = self.run_cli("--protect", "main", "--checks-from", SHA, "--create-protection")
        self.assertEqual(code, 0, result)
        self.checks("workflow_dispatch")
        code, result = self.run_cli("--protect", "main", "--checks-from", SHA, "--create-protection", "--apply")
        self.assertEqual(code, 1, result)
        self.assertIn("No qualifying", " ".join(result["errors"]))
        self.assertTrue(all(c["method"] == "GET" for c in self.calls()))

    def test_default_plan_reads_current_controls_without_writes(self):
        code, result = self.run_cli("--description", "New", "--topics", "python", "--squash-only")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["mode"], "plan")
        self.assertEqual(result["current"]["repository"]["description"], "Old")
        self.assertTrue(result["current"]["protection"]["enforce_admins"]["enabled"])
        self.assertEqual(result["plan"][0]["desired"], {
            "description": "New", "allow_squash_merge": True,
            "allow_merge_commit": False, "allow_rebase_merge": False})
        self.assertEqual(result["plan"][1]["desired"], {"names": ["existing", "python"]})
        self.assertTrue(all(call["method"] == "GET" for call in self.calls()))

    def test_apply_metadata_preserves_unselected_settings_and_verifies_readback(self):
        code, result = self.run_cli("--description", "New", "--topics", "python", "--squash-only", "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual([r["status"] for r in result["results"]], ["verified", "verified"])
        repo = self.state["responses"][REPO]
        self.assertEqual(repo["description"], "New")
        self.assertTrue(repo["private"])
        self.assertTrue(repo["has_issues"])
        self.assertEqual(self.state["responses"][REPO + "/topics"]["names"], ["existing", "python"])
        writes = [c for c in self.calls() if c["method"] != "GET"]
        self.assertEqual(len(writes), 2)
        self.assertNotIn("private", writes[0]["payload"])
        for write in writes:
            self.assertTrue(any(c["method"] == "GET" and c["endpoint"] == write["endpoint"]
                                for c in self.calls()[self.calls().index(write) + 1:]))

    def test_metadata_apply_on_confirmed_unprotected_branch(self):
        self.state["failures"] = {
            "GET " + REPO + "/branches/main/protection": "gh: Branch not protected (HTTP 404)"}
        code, result = self.run_cli("--description", "New", "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["current"]["protection"], {"status": "absent", "http_status": 404})
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["results"][0]["status"], "verified")
        self.assertEqual([c["endpoint"] for c in self.calls() if c["method"] != "GET"], [REPO])

    def test_description_apply_reports_unrelated_unknown_inspections_as_warnings(self):
        endpoints = {"protection": "/branches/main/protection", "topics": "/topics",
                     "rulesets": "/rulesets?includes_parents=true&per_page=100&page=1",
                     "effective_rules": "/rules/branches/main?per_page=100&page=1"}
        self.state["failures"] = {"GET " + REPO + path: "gh: forbidden secret (HTTP 403)"
                                  for path in endpoints.values()}
        code, result = self.run_cli("--description", "New", "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(result["warnings"]), 4)
        for name in endpoints:
            self.assertEqual(result["current"][name]["status"], "unknown")
        self.assertEqual(result["results"][0]["status"], "verified")
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual([c["endpoint"] for c in self.calls() if c["method"] != "GET"], [REPO])

    def test_topic_apply_does_not_require_protection_permissions(self):
        self.state["failures"] = {
            "GET " + REPO + "/branches/main/protection": "gh: forbidden (HTTP 403)"}
        code, result = self.run_cli("--topics", "python", "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["current"]["protection"]["status"], "unknown")
        self.assertEqual(len(result["warnings"]), 1)
        self.assertEqual(result["results"][0]["status"], "verified")

    def test_selected_protection_still_blocks_combined_apply_with_unknown_controls(self):
        self.checks()
        self.state["failures"] = {
            "GET " + REPO + "/branches/main/protection": "gh: forbidden (HTTP 403)"}
        code, result = self.run_cli("--description", "New", "--protect", "main",
                                    "--checks-from", SHA, "--apply")
        self.assertEqual(code, 1, result)
        self.assertEqual(result["current"]["protection"]["status"], "unknown")
        self.assertTrue(result["errors"])
        self.assertTrue(all(c["method"] == "GET" for c in self.calls()))

    def test_partial_apply_retry_skips_completed_write(self):
        self.state["failures"] = {"PUT " + REPO + "/topics": "gh: Resource not accessible (HTTP 403)"}
        code, result = self.run_cli("--description", "New", "--topics", "python", "--apply")
        self.assertEqual(code, 1, result)
        self.assertEqual([r["status"] for r in result["results"]], ["verified", "failed"])
        self.assertIn("403", result["results"][1]["reason"])
        self.assertEqual(result["results"][1]["readback"], {"names": ["existing"]})
        self.assertEqual(self.state["responses"][REPO]["description"], "New")
        self.state["failures"] = {}
        count = len(self.calls())
        code, result = self.run_cli("--description", "New", "--topics", "python", "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual([r["status"] for r in result["results"]], ["unchanged", "verified"])
        self.assertEqual([c["method"] for c in self.calls()[count:] if c["method"] != "GET"], ["PUT"])

    def test_successful_write_with_stale_readback_is_failure_and_stops(self):
        self.state["stale"] = [REPO]
        code, result = self.run_cli("--description", "New", "--topics", "python", "--apply")
        self.assertEqual(code, 1, result)
        self.assertIn("readback", result["errors"][0])
        self.assertEqual([c["method"] for c in self.calls() if c["method"] != "GET"], ["PATCH"])
        self.assertEqual([r["status"] for r in result["results"]], ["failed", "not_attempted"])

    def test_incomplete_existing_check_data_blocks_all_apply(self):
        self.checks()
        del self.state["responses"][REPO + "/branches/main/protection"]["required_status_checks"]["checks"]
        code, result = self.run_cli("--description", "New", "--protect", "main", "--checks-from", SHA, "--apply")
        self.assertEqual(code, 1, result)
        self.assertIn("incomplete", " ".join(result["errors"]).lower())
        self.assertFalse(any(c["method"] != "GET" for c in self.calls()))

    def test_missing_and_manually_dispatched_checks_never_become_requirements(self):
        for event in ("workflow_dispatch", "pull_request_target", "push"):
            with self.subTest(event=event):
                self.checks(event)
                if event == "push":
                    self.state["responses"][REPO + f"/commits/{SHA}/check-runs?filter=latest&per_page=100&page=1"]["check_runs"] = []
                code, result = self.run_cli("--protect", "main", "--checks-from", SHA, "--apply")
                self.assertEqual(code, 1, result)
                self.assertIn("No qualifying", " ".join(result["errors"]))
                self.assertFalse(any(c["method"] != "GET" for c in self.calls()))

    def test_push_event_qualifies_and_plan_is_read_only(self):
        self.checks("push")
        code, result = self.run_cli("--protect", "main", "--checks-from", SHA, "--host", "github.example.com")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["check_evidence"][0]["event"], "push")
        self.assertTrue(all(c["method"] == "GET" for c in self.calls()))
        self.assertTrue(all("github.example.com" in c["args"] for c in self.calls()))

    def test_unknown_provenance_and_app_conflicts_block_apply(self):
        for kind in ("no_workflow", "wrong_suite", "conflict"):
            with self.subTest(kind=kind):
                self.checks()
                if kind == "no_workflow":
                    self.state["responses"][REPO + f"/actions/runs?check_suite_id=20&head_sha={SHA}&per_page=100&page=1"]["workflow_runs"] = []
                elif kind == "wrong_suite":
                    self.state["responses"][REPO + "/check-suites/20"]["head_sha"] = "b" * 40
                else:
                    settings = self.state["responses"][REPO + "/branches/main/protection"]["required_status_checks"]
                    settings["checks"].append({"context": "test", "app_id": 42})
                code, result = self.run_cli("--protect", "main", "--checks-from", SHA, "--apply")
                self.assertEqual(code, 1, result)
                self.assertTrue(result["errors"])
                self.assertFalse(any(c["method"] != "GET" for c in self.calls()))

    def test_inaccessible_controls_and_rulesets_block_protection(self):
        for kind in ("403", "404", "ruleset", "unknown_enforcement", "effective"):
            with self.subTest(kind=kind):
                self.checks()
                self.state["failures"] = {}
                rulesets_path = REPO + "/rulesets?includes_parents=true&per_page=100&page=1"
                effective_path = REPO + "/rules/branches/main?per_page=100&page=1"
                self.state["responses"][rulesets_path] = []
                self.state["responses"][effective_path] = []
                if kind in ("403", "404"):
                    self.state["failures"]["GET " + REPO + "/branches/main/protection"] = "gh: plan/auth restriction (HTTP " + kind + ")"
                elif kind == "effective":
                    self.state["responses"][effective_path] = [{"type": "required_status_checks"}]
                else:
                    self.state["responses"][rulesets_path] = [{"id": 7, **({"enforcement": "active"} if kind == "ruleset" else {})}]
                code, result = self.run_cli("--protect", "main", "--checks-from", SHA, "--apply")
                self.assertEqual(code, 1, result)
                self.assertTrue(result["errors"])
                if kind in ("403", "404"):
                    self.assertEqual(result["current"]["protection"]["status"],
                                     "absent" if kind == "404" else "unknown")
                self.assertFalse(any(c["method"] != "GET" for c in self.calls()))

    def test_missing_auth_is_json_unknown_and_nonzero(self):
        self.state["failures"] = {"GET " + REPO: "gh: To get started, run gh auth login"}
        code, result = self.run_cli("--description", "New", "--apply")
        self.assertEqual(code, 1, result)
        self.assertEqual(result["current"]["repository"]["status"], "unknown")
        self.assertIn("HTTP unknown; API access failed", " ".join(result["errors"]))
        self.assertNotIn("auth login", json.dumps(result))
        self.assertFalse(any(c["method"] != "GET" for c in self.calls()))

    def test_paginated_inherited_rulesets_are_all_assessed(self):
        path = REPO + "/rulesets?includes_parents=true&per_page=100&page="
        self.state["responses"][path + "1"] = [{"id": i, "enforcement": "disabled"} for i in range(100)]
        self.state["responses"][path + "2"] = [{"id": 101, "enforcement": "active"}]
        code, result = self.run_cli("--protect", "main", "--checks-from", SHA, "--apply")
        self.assertEqual(code, 1, result)
        self.assertEqual(len(result["current"]["rulesets"]), 101)
        self.assertIn("rulesets", " ".join(result["errors"]))
        self.assertFalse(any(c["method"] != "GET" for c in self.calls()))

    def test_malformed_inspection_response_is_unknown_and_blocks_apply(self):
        self.state["responses"][REPO + "/topics"] = []
        code, result = self.run_cli("--topics", "python", "--apply")
        self.assertEqual(code, 1, result)
        self.assertEqual(result["current"]["topics"]["status"], "unknown")
        self.assertFalse(any(c["method"] != "GET" for c in self.calls()))

    def test_malformed_readback_retains_partial_apply_evidence(self):
        self.state["malformed_readback"] = [REPO + "/topics"]
        code, result = self.run_cli("--description", "New", "--topics", "python", "--apply")
        self.assertEqual(code, 1, result)
        self.assertEqual([r["status"] for r in result["results"]], ["verified", "failed"])
        self.assertIn("readback", result["results"][1]["reason"])

    def test_offline_explicit_intents_make_no_gh_calls_and_cannot_apply(self):
        code, result = self.run_cli("--offline", "--description", "New", "--topics", "python")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["intents"], {"repository": {"description": "New"}, "add_topics": ["python"]})
        self.assertEqual(self.calls(), [])
        for args in (("--offline",), ("--offline", "--description", "New", "--apply"),
                     ("--check", "test"), ("--protect", "main", "--checks-from", SHA, "--check", ""),
                     ("--create-protection",), ("--create-protection", "--protect", "main"),
                     ("--offline", "--protect", "main", "--checks-from", SHA),
                     ("--protect", "main"), ("--checks-from", SHA),
                     ("--protect", "main", "--checks-from", "main"), ("--topics", "UpperCase"),
                     ("--unknown-option",)):
            with self.subTest(args=args):
                code, result = self.run_cli(*args)
                self.assertEqual(code, 1, result)
                self.assertTrue(result["errors"])
                self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
