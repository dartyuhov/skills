#!/usr/bin/env python3
"""Read-only settings planning; writes require --apply. Uses only Python and gh."""

import argparse
import json
import re
import subprocess
import sys
from typing import Any
from urllib.parse import quote


class SettingsError(Exception):
    def __init__(self, message, http_status=None):
        super().__init__(message)
        self.http_status = http_status


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SettingsError(message)


def api(host, endpoint, method="GET", payload=None):
    command = ["gh", "api", endpoint, "--hostname", host, "--method", method,
               "-H", "Accept: application/vnd.github+json"]
    if payload is not None:
        command += ["--input", "-"]
    try:
        response = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                                  text=True, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SettingsError(f"{method} {endpoint}: gh execution failed or timed out") from exc
    if response.returncode:
        match = re.search(r"\(HTTP ([1-5][0-9]{2})\)", response.stderr)
        status = int(match[1]) if match else None
        label = f"HTTP {status}" if status else "HTTP unknown"
        raise SettingsError(f"{method} {endpoint}: {label}; API access failed", status)
    try:
        return json.loads(response.stdout)
    except ValueError as exc:
        raise SettingsError(f"{method} {endpoint}: gh returned invalid JSON") from exc


def pages(host, endpoint, key=None):
    result = []
    for page in range(1, 101):
        value = api(host, endpoint + ("&" if "?" in endpoint else "?") +
                    f"per_page=100&page={page}")
        if key and (not isinstance(value, dict) or key not in value):
            raise SettingsError(f"{endpoint}: missing {key}; incomplete response")
        batch = value[key] if key else value
        if not isinstance(batch, list):
            raise SettingsError(f"{endpoint}: expected a list")
        if any(not isinstance(item, dict) for item in batch):
            raise SettingsError(f"{endpoint}: malformed list entry")
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise SettingsError(f"{endpoint}: pagination limit reached; data is incomplete")


def parser():
    p = Parser(description=__doc__, epilog=(
        "Topics are additive. --squash-only changes only the three merge-method flags. "
        "Protection adds observed successful push/pull_request checks to existing classic "
        "required status checks; it preserves strictness and other protection fields. "
        "By default all qualifying observed checks are added. Repeat --check NAME to "
        "select only specific new checks; existing requirements are always preserved. "
        "--create-protection opts into new classic protection only after HTTP 404, with "
        "strict checks, admin enforcement, PRs with zero approvals, linear history, "
        "no push restrictions, and blocked force pushes/deletion. "
        "It refuses absent status-check protection on existing protection, active/evaluating "
        "rulesets, unknown controls, or unverifiable workflow events. It never replaces "
        "rulesets. Unrelated inspection failures are warnings for selected changes; "
        "unknown protection controls block protection changes. Selected changes must "
        "all pass planning before any writes. Offline plans show unassessed intents "
        "only and cannot apply."))
    p.add_argument("--repo", required=True, help="explicit OWNER/REPO")
    p.add_argument("--host", default="github.com", help="GitHub hostname (default: github.com)")
    p.add_argument("--description", help="desired description; empty text clears it")
    p.add_argument("--topics", action="append", help="topic to add; repeat for multiple topics")
    p.add_argument("--squash-only", action="store_true", help="enable squash, disable merge and rebase merging")
    p.add_argument("--protect", metavar="BRANCH", help="add required checks on this branch")
    p.add_argument("--create-protection", action="store_true", help="create only if protection GET returns HTTP 404; requires --protect and --checks-from")
    p.add_argument("--checks-from", metavar="SHA", help="full commit SHA supplying observed check evidence; requires --protect")
    p.add_argument("--check", metavar="NAME", action="append", help="add only this qualifying observed check name (exact match); repeat to select multiple; requires --protect/--checks-from")
    p.add_argument("--apply", action="store_true", help="explicitly apply and read back selected changes")
    p.add_argument("--offline", action="store_true", help="no gh/network calls; requires explicit desired settings; cannot apply or protect")
    return p


def operation(name, endpoint, method, desired, current):
    return {"name": name, "endpoint": endpoint, "method": method, "desired": desired,
            "changed": any(current.get(key) != value for key, value in desired.items())}


def normalized_checks(settings):
    """Keep app bindings and legacy unbound contexts, without response-only fields."""
    if not isinstance(settings.get("checks"), list) or not isinstance(settings.get("contexts"), list):
        raise SettingsError("Existing required checks data is incomplete; source app bindings are unknown")
    checks = {}
    for check in settings["checks"]:
        if not isinstance(check, dict) or "context" not in check or "app_id" not in check:
            raise SettingsError("Existing required check data is incomplete; source app bindings are unknown")
        context, app = check["context"], check["app_id"]
        app = -1 if app is None else app
        if not isinstance(context, str) or not context or not isinstance(app, int):
            raise SettingsError("Malformed existing required check; refusing to replace it")
        if context in checks and checks[context] != app:
            raise SettingsError(f"Ambiguous existing app bindings for {context}")
        checks[context] = app
    for context in settings["contexts"]:
        if not isinstance(context, str) or not context:
            raise SettingsError("Malformed existing required check context")
        checks.setdefault(context, -1)
    return [{"context": name, "app_id": checks[name]} for name in sorted(checks)]


def verify_created_protection(actual, desired):
    """Verify request fields against GitHub's nested response representation."""
    def require_equal(value, expected, field):
        if type(value) is not type(expected) or value != expected:
            raise SettingsError(f"create_protection: readback mismatch for {field}")

    for field in ("enforce_admins", "allow_force_pushes", "allow_deletions", "required_linear_history"):
        value = actual.get(field)
        if not isinstance(value, dict):
            raise SettingsError(f"create_protection: readback missing nested {field}")
        require_equal(value.get("enabled"), desired[field], field + ".enabled")
    if "restrictions" not in actual:
        raise SettingsError("create_protection: readback missing restrictions")
    require_equal(actual["restrictions"], desired["restrictions"], "restrictions")
    reviews = actual.get("required_pull_request_reviews")
    if not isinstance(reviews, dict):
        raise SettingsError("create_protection: readback missing required_pull_request_reviews")
    require_equal(reviews.get("required_approving_review_count"), 0,
                  "required_pull_request_reviews.required_approving_review_count")
    checks = actual.get("required_status_checks")
    if not isinstance(checks, dict):
        raise SettingsError("create_protection: readback missing required_status_checks")
    require_equal(checks.get("strict"), True, "required_status_checks.strict")
    require_equal(normalized_checks(checks), normalized_checks(desired["required_status_checks"]),
                  "required_status_checks.checks")


def protection_change(args, base, path, protection, rulesets, effective, result):
    if not isinstance(protection, dict) or not isinstance(rulesets, list) or not isinstance(effective, list):
        raise SettingsError("Cannot assess existing protection and inherited rulesets; protection is blocked")
    if effective or any(rule.get("enforcement") != "disabled" for rule in rulesets):
        raise SettingsError("Existing active/evaluating or unknown rulesets: refusing protection changes; rulesets are never replaced")
    creating = protection.get("status") == "absent" and protection.get("http_status") == 404
    if args.create_protection and not creating:
        raise SettingsError("--create-protection requires confirmed absent protection (HTTP 404); existing protection will not be replaced")
    if creating and not args.create_protection:
        raise SettingsError("Protection is absent (HTTP 404); creation requires --create-protection")
    settings = {"strict": True, "checks": [], "contexts": []} if creating else protection.get("required_status_checks")
    if not isinstance(settings, dict) or not isinstance(settings.get("strict"), bool):
        raise SettingsError("Existing status-check protection is absent/unknown; creating protection is unsupported")
    existing = normalized_checks(settings)
    discovered = {}
    evidence = []
    runs = pages(args.host, base + f"/commits/{args.checks_from}/check-runs?filter=latest", "check_runs")
    suites = {}
    for check in runs:
        if check.get("status") != "completed" or check.get("conclusion") != "success":
            continue
        if check.get("head_sha", "").lower() != args.checks_from.lower():
            continue
        if args.check and check.get("name") not in args.check:
            continue
        suite_id = (check.get("check_suite") or {}).get("id")
        app_id = (check.get("app") or {}).get("id")
        name = check.get("name")
        if not isinstance(suite_id, int) or not isinstance(app_id, int) or not isinstance(name, str) or not name:
            raise SettingsError("Successful check has missing name, suite or source app; cannot verify provenance")
        if suite_id not in suites:
            suite = api(args.host, base + f"/check-suites/{suite_id}")
            workflows = pages(args.host, base + f"/actions/runs?check_suite_id={suite_id}&head_sha={args.checks_from}", "workflow_runs")
            suites[suite_id] = (suite, workflows)
        suite, workflows = suites[suite_id]
        if (suite.get("id") != suite_id or suite.get("head_sha", "").lower() != args.checks_from.lower()
                or (suite.get("app") or {}).get("id") != app_id):
            raise SettingsError(f"Check suite {suite_id} identity/SHA/app mismatch")
        matching = [w for w in workflows if w.get("check_suite_id") == suite_id
                    and w.get("head_sha", "").lower() == args.checks_from.lower()]
        if not matching:
            raise SettingsError(f"Cannot verify workflow event for check {name!r} in suite {suite_id}; custom/external checks unsupported")
        if len(matching) != 1:
            raise SettingsError(f"Ambiguous workflow event for check {name!r} in suite {suite_id}")
        workflow = matching[0]
        if (workflow.get("event") not in ("pull_request", "push")
                or workflow.get("status") != "completed" or workflow.get("conclusion") != "success"):
            continue
        if name in discovered and discovered[name] != app_id:
            raise SettingsError(f"Ambiguous source apps for observed check {name!r}")
        discovered[name] = app_id
        evidence.append({"context": name, "app_id": app_id, "check_run_id": check.get("id"),
                         "check_suite_id": suite_id, "workflow_run_id": workflow.get("id"),
                         "event": workflow["event"], "head_sha": args.checks_from})
    result["check_evidence"] = evidence
    if args.check:
        missing = sorted(set(args.check) - set(discovered))
        if missing:
            raise SettingsError("Requested checks lack qualifying successful pull_request/push evidence: "
                                + ", ".join(repr(name) for name in missing))
    if not discovered:
        raise SettingsError("No qualifying successful pull_request/push checks found; manual dispatch is not merge-gate evidence")
    merged = {c["context"]: c["app_id"] for c in existing}
    for name, app_id in discovered.items():
        if name in merged and merged[name] != app_id:
            raise SettingsError(f"Existing check {name!r} has a different/unbound source app; refusing to replace its binding")
        merged[name] = app_id
    desired = {"strict": settings["strict"],
               "checks": [{"context": name, "app_id": merged[name]} for name in sorted(merged)]}
    if creating:
        desired["contexts"] = []
        return operation("create_protection", path, "PUT", {
            "required_status_checks": desired, "enforce_admins": True,
            "required_pull_request_reviews": {"required_approving_review_count": 0},
            "restrictions": None, "allow_force_pushes": False, "allow_deletions": False,
            "required_linear_history": True}, {})
    return operation("protection", path + "/required_status_checks", "PATCH", desired,
                     {"strict": settings["strict"], "checks": existing})


def run(args):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        raise SettingsError("--repo must be OWNER/REPO")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", args.host):
        raise SettingsError("--host must be a hostname")
    if bool(args.protect) != bool(args.checks_from):
        raise SettingsError("--protect and --checks-from must be supplied together")
    if args.create_protection and not (args.protect and args.checks_from):
        raise SettingsError("--create-protection requires --protect and --checks-from")
    if args.check and not (args.protect and args.checks_from):
        raise SettingsError("--check requires --protect and --checks-from")
    if args.check and any(not name.strip() for name in args.check):
        raise SettingsError("--check requires a nonempty exact check name")
    if args.checks_from and not re.fullmatch(r"[0-9a-fA-F]{40}", args.checks_from):
        raise SettingsError("--checks-from requires a full 40-character commit SHA")
    if args.topics and any(not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", t) for t in args.topics):
        raise SettingsError("topics must be lowercase letters, digits or hyphens, 1–50 characters")
    desired = {}
    if args.description is not None:
        desired["description"] = args.description
    if args.squash_only:
        desired.update(allow_squash_merge=True, allow_merge_commit=False, allow_rebase_merge=False)
    result = {"repo": args.repo, "host": args.host, "mode": "apply" if args.apply else "plan",
              "current": {}, "plan": [], "errors": [], "warnings": [], "results": []}
    if args.offline:
        if args.apply or args.protect or not (desired or args.topics):
            raise SettingsError("--offline requires explicit metadata/merge inputs and cannot --apply or --protect")
        result.update(offline=True, current={"status": "unknown: offline; no remote inspection"},
                      intents={"repository": desired, "add_topics": args.topics or []})
        return result
    base = "repos/" + args.repo
    # A pure inspection still reports incomplete inventory as an error. For
    # selected changes only their prerequisites gate writes; keep other gaps
    # visible without requiring branch-administration permissions for metadata.
    audit_only = not (desired or args.topics or args.protect)
    required_inspections = {"repository"}
    if args.topics:
        required_inspections.add("topics")
    if args.protect:
        required_inspections.update(("protection", "rulesets", "effective_rules"))

    def inspect(name, endpoint, paginated=False) -> Any:
        try:
            value = pages(args.host, endpoint) if paginated else api(args.host, endpoint)
            if not paginated and not isinstance(value, dict):
                raise SettingsError(f"{endpoint}: expected a JSON object; data is unknown")
            if name == "repository" and isinstance(value, dict) and not isinstance(value.get("default_branch"), str):
                raise SettingsError(f"{endpoint}: default branch is unknown")
            if name == "topics" and isinstance(value, dict) and (not isinstance(value.get("names"), list)
                                      or any(not isinstance(topic, str) for topic in value["names"])):
                raise SettingsError(f"{endpoint}: existing topics are unknown")
            result["current"][name] = value
            return value
        except SettingsError as exc:
            if name == "protection" and exc.http_status == 404:
                value = {"status": "absent", "http_status": 404}
                result["current"][name] = value
                return value
            result["current"][name] = {"status": "unknown", "reason": str(exc)}
            category = "errors" if audit_only or name in required_inspections else "warnings"
            result[category].append(str(exc))
            return None

    repository = inspect("repository", base)
    topics = inspect("topics", base + "/topics")
    branch = args.protect or (repository.get("default_branch") if isinstance(repository, dict) else None)
    protection_path = base + "/branches/" + quote(branch, safe="") + "/protection" if branch else None
    protection = inspect("protection", protection_path) if protection_path else None
    rulesets = inspect("rulesets", base + "/rulesets?includes_parents=true", True)
    effective = inspect("effective_rules", base + "/rules/branches/" + quote(branch, safe=""), True) if branch else None
    if isinstance(repository, dict) and desired:
        result["plan"].append(operation("repository", base, "PATCH", desired, repository))
    if isinstance(topics, dict) and args.topics:
        names = sorted(set(topics["names"]) | set(args.topics))
        if len(names) > 20:
            result["errors"].append("GitHub supports at most 20 topics; preserving existing topics exceeds that limit")
        else:
            result["plan"].append(operation("topics", base + "/topics", "PUT", {"names": names},
                                            {"names": sorted(topics["names"])}))
    if args.protect:
        try:
            result["plan"].append(protection_change(args, base, protection_path, protection,
                                                    rulesets, effective, result))
        except SettingsError as exc:
            result["errors"].append(str(exc))
    if args.apply and not result["errors"]:
        result["results"] = [{"name": change["name"], "status": "not_attempted"} for change in result["plan"]]
        for change, outcome in zip(result["plan"], result["results"]):
            if not change["changed"]:
                outcome["status"] = "unchanged"
                continue
            outcome["status"] = "failed"
            try:
                api(args.host, change["endpoint"], change["method"], change["desired"])
                actual = api(args.host, change["endpoint"])
                outcome["readback"] = actual
                if not isinstance(actual, dict):
                    raise SettingsError(f"{change['name']}: malformed readback; expected an object")
                selected = actual
                if change["name"] == "protection":
                    selected = {"strict": actual.get("strict"), "checks": normalized_checks(actual)}
                if change["name"] == "topics":
                    selected = {"names": sorted(actual.get("names", []))}
                if change["name"] == "create_protection":
                    verify_created_protection(actual, change["desired"])
                elif any(selected.get(key) != value for key, value in change["desired"].items()):
                    raise SettingsError(f"{change['name']}: readback does not match selected fields")
                outcome["status"] = "verified"
            except (SettingsError, KeyError, TypeError, ValueError, AttributeError) as exc:
                outcome["reason"] = str(exc)
                result["errors"].append(str(exc))
                # A nonzero gh exit can follow a server-side write. Observe rather
                # than asserting rollback; the next invocation plans from reality.
                if "readback" not in outcome:
                    try:
                        outcome["readback"] = api(args.host, change["endpoint"])
                    except SettingsError as read_error:
                        outcome["readback"] = {"status": "unknown", "reason": str(read_error)}
                break
    return result


def main():
    try:
        result = run(parser().parse_args())
    except (SettingsError, KeyError, TypeError, ValueError, AttributeError) as exc:
        result = {"errors": [str(exc)], "plan": [], "results": []}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
