---
name: opensource-me
description: Prepare and launch an existing Git repository as an open-source GitHub project. Use when asked to open-source a repo, make a personal project public, audit launch readiness, or set up its public docs, contribution workflow, CI, releases, and installation. Supports audit-only and resumed launches, agreed release automation, and verification from public downloads. Uses parallel subagents for independent work and preserves unrelated work.
compatibility: Python 3, Git, and GitHub CLI (gh) for remote operations. Subagent-capable harness recommended.
---

# opensource-me

Take a repository from personal checkout to a usable public project. Finish with
evidence of what works locally, what is configured remotely, and what users can
actually install.

## Establish scope

Read the target repository's agent instructions. Identify its absolute path,
GitHub host and owner/name, default branch, current visibility, and dirty files.
Resolve identity from the repository and remote metadata; local directory names
alone aren't enough. Preserve unrelated work.

Choose the requested mode: **audit**, **prepare**, or **launch**. Resume from
observed reality when earlier steps already exist. Audit mode is read-only.
Ask only for decisions that the project and user haven't established.

For new setups, default to Conventional Commits, squash merges, Release Please,
and maintainer-merged release PRs. Preserve useful existing tooling while checking
that its behavior matches the requested release experience. Use MIT
for an unlicensed repository after establishing the actual copyright holder
and year; preserve existing licenses and third-party notices.

Read [the launch checklist](references/launch-checklist.md) for phase completion
criteria. Use the host harness's task tracker. When work includes a ticket,
load its tracker workflow before reading or updating it; discussion-only work
doesn't change task state.

## Agree on the release contract and execution scope

Before choosing automation, establish what happens after a feature/fix merge and
which action approves publication. If the user names a reference project,
inspect its actual workflows and release scripts before proposing the contract.
An existing manual workflow is evidence of current behavior, not a preference
that overrides the user. Reuse its sound build/validation pieces when changing
orchestration.

Record a short release contract alongside the work plan:

- Trigger, version/changelog owner, and source revision used for packaging.
- Approval point: for example, merging a generated release PR authorizes automatic
  tag creation and publication after checks; or an explicitly selected manual path.
- Asset names, signing responsibility, supported installation route, and retry
  behavior. Distinguish shared app configuration from personal account sessions.
- Requested endpoint: local preparation, hosted automation, first public release,
  or installation/upgrade verified from that release.

Capture an **authorization ledger** in the task state: operation, target, approved
scope, and unresolved limits. Offer local preparation, PR-based delivery, or
end-to-end repair only as appropriate to the request; none grants permissions by
itself. Record commits, local merges, pushes, PR creation, settings, visibility,
tags, and publication separately. Reuse explicit approvals within their scope and
carry them through handoffs; ask again when the target or permitted operation
changes. A release-PR merge can be the agreed publication approval without a
second publish-button gate. Audit mode remains read-only.

For hosted automation, complete the access preflight in
[release operations](references/release-operations.md#access-preflight) before
spending implementation effort on a path that needs unavailable credentials.
Continue independent local work while clearly identifying human-only setup.

## Delegate independent work

Read [parallel work](references/parallel-work.md) before dispatching agents.
Use parallel subagents whenever independent work exists. Send assignments in
one batch and continue with non-overlapping coordinator work.

Start with concurrent read-only audits:

- Documentation, onboarding, and community files.
- Tracked content/history exposure and resource licensing.
- Build, CI, versioning, distribution, and installation.
- GitHub metadata, permissions, effective settings, and hosted checks.

Give each agent its scope, owned paths, applicable instructions, output contract,
and verification criteria. After reconciling findings, assign preparation work
with disjoint file ownership. One owner edits each shared manifest or workflow;
other agents return proposed changes to that owner. Workers report changed
paths, evidence, blockers, and integration needs.

The coordinator integrates changes and owns remote writes, git operations,
visibility, and publication. Run dependent steps in order. When subagents are
unavailable, state the limitation and execute the same assignments sequentially.

## Inspect and prepare

Resolve this skill's directory from its loaded location. Use explicit paths;
the commands below use `SKILL_DIR` and `REPO` as shell variables set by the agent.

```sh
python3 "$SKILL_DIR/scripts/inspect-repo.py" "$REPO"
```

The JSON inventory lists tracked, untracked, and ignored paths, worktree state,
stack markers, documentation, workflows, and history metadata. It doesn't
inspect file contents or prove absence of secrets. Use a maintained available
scanner for history/content checks and record its actual scope. Review accessible
Actions logs/artifacts before public exposure. Keep credential values out of
reports. Resolve concrete exposure findings before launch.

Adapt templates from `assets/templates/` using
[rendering guidance](references/reference-examples.md#render-and-validate).
Derive commands and claims from the project. Replace every `{{UPPER_CASE}}`
placeholder, verify links, and run examples where feasible. Fill gaps in README,
installation, source setup, contributing, issue forms, PR template, license,
configuration examples, and ignore rules. Existing useful files are inputs to
edit rather than disposable scaffolding.

## Automate the appropriate release route

Select only the references needed for the project:

- [Rust binaries and plugins](references/rust-distribution.md): locked builds,
  supported platform matrix, checksums, installers, and plugin-specific metadata.
- [macOS apps and DMGs](references/macos-distribution.md): Swift version sources,
  packaging, resources, architecture checks, and honest signing requirements.
- [Owned Homebrew taps](references/homebrew.md): public artifact contracts,
  constrained cask updates, stale-update handling, and independent retries.
- [GitHub operations](references/github-operations.md): source-only releases,
  token strategy, observed checks, effective rules, and publication contracts.
- [Release operations](references/release-operations.md): access preflight,
  workflow lifecycle/transport tests, first hosted release, and guide-driven
  installation. Read this when implementing or repairing release automation.

The example origins and trade-offs are in
[reference examples](references/reference-examples.md). Treat them as recipes,
not dependencies or mandatory platform matrices.

Check current official documentation for the installed CLI and pinned actions
before generating automation. Templates deliberately leave action SHAs and
project commands unresolved. Pin reviewed action revisions, validate actual
schemas, and verify version files stay synchronized. Keep fork PR checks
read-only and publication credentials confined to publishing jobs.

Build the intended source and verify the full expected asset set before
publishing binary releases. Use draft-first publication and retry failed drafts.
Verify completed public releases without replacing their assets. Source-only
projects need a source-release contract rather than fabricated binary assets.
Draft staging is an internal validation step, not necessarily another human
approval: publish automatically after validation when that is the agreed contract.

## Configure and launch on GitHub

Run the settings helper as a read-only plan first:

```sh
python3 "$SKILL_DIR/scripts/github-settings.py" --repo OWNER/REPO \
  --description "PROJECT DESCRIPTION" --squash-only
```

It uses `gh` to read remote state. `--offline` makes no network calls and emits
unassessed metadata/merge intents only. `--topics` is additive. `--apply` writes
selected changes and verifies readback; use it only within authorized scope.

After real qualifying CI has completed, use `--protect BRANCH --checks-from SHA`
to plan additive required checks for existing classic protection. For a branch
confirmed unprotected by HTTP 404, add `--create-protection` to plan first-time
protection. The helper preserves existing controls and refuses ambiguous or
active rulesets; use the operations guide to reconcile these cases explicitly.
Review selected checks: not every successful job is necessarily a desired gate.
Use repeatable `--check "EXACT JOB NAME"` to select qualifying observed checks;
without it the helper adds all qualifying successful checks from that SHA.
Manual dispatch alone isn't proof of a qualifying PR merge gate.

Before each remote mutation, check the authorization ledger against harness
permissions. Leave changes uncommitted without commit approval; permission to
create local files doesn't imply remote permissions. Identify the exact repository
and desired visibility before a transition. Keep history rewriting a separate
recovery decision. Update the ledger when the user explicitly expands scope,
including whether repairs go through PRs or directly to the approved branch.

Verify public release metadata and artifacts with the read-only helper:

```sh
python3 "$SKILL_DIR/scripts/verify-release.py" --repo OWNER/REPO \
  --tag vVERSION --expect ARTIFACT --checksums
```

Repeat `--expect` for every required artifact; include provenance files when
part of the contract. With no `--expect`, only release metadata is verified.
The helper defaults to a public stable release; use `--prerelease` to require
a prerelease instead. It validates safe asset names and
checks conventional SHA-256 manifests/sidecars. It uses authenticated `gh` for
reads: separately verify anonymous public access. It doesn't run installers or
establish signing authenticity. For launch mode, follow
[first hosted release](references/release-operations.md#first-hosted-release)
through the authorized endpoint rather than stopping at a green automation PR.
Then perform the documented installation and first-use/upgrade checks using
public downloads, recording unavailable manual coverage.

## Verify and report

Run relevant project tests and integration checks after combining agent work.
To verify this skill's own helpers, run:

```sh
python3 -B -m unittest discover -s "$SKILL_DIR/tests" -p 'test_*.py'
```

Review the final diff against repository standards and requested scope. Report:

- Local changes and verification commands/results.
- Observed GitHub configuration with URLs or readback evidence.
- Published release and expected artifact verification.
- Installation/first-use evidence and outstanding manual coverage.
- Remaining blockers with a concrete next action.

Keep **prepared locally**, **configured on GitHub**, **published**, and
**installation verified** distinct. Successful CI, a tag, or generated files
alone don't establish a completed launch.
