# GitHub operations

Reconcile observed settings with the requested launch scope. Read-only inspection
and a proposed plan precede any authorized remote mutation.

## Runtime documentation check

Check installed `gh --version` and relevant subcommand `--help`, the target host's
capabilities, and official docs for each pinned action and Release Please schema
before generating executable automation. Record the date and selected versions.

As checked on November 8, 2026, GitHub's [token documentation](https://docs.github.com/en/actions/concepts/security/github_token)
says `GITHUB_TOKEN` events generally suppress new workflow runs, except dispatch
events and PR `opened`, `synchronize`, and `reopened` events, which can create
approval-required runs. A writer must approve those PR runs. Other PR event types
remain suppressed. The [Release Please action README](https://github.com/googleapis/release-please-action)
still describes broader suppression: resolve this difference against the current
target host and observed runs, rather than copying either assumption blindly.

Use a narrowly scoped GitHub App installation token or PAT when approved,
unattended bot PR checks are required. Repository policy must also permit release
PR creation. Keep fork PR checks read-only and secret-free. Never execute PR code
with write credentials through `pull_request_target`.

Before implementing that path, use the
[access preflight](release-operations.md#access-preflight) to verify effective App
installation/permissions and setting names. Treat an App rename and an installation
permission update as observable state changes, not assumptions.

## PR merge gates

Prove that a check is a usable merge gate before requiring it.

1. Observe ordinary and bot-created release PR runs. Record event, tested SHA,
   check name, source application, result, and any approval requirement.
2. Inspect branch protection and all effective/inherited rulesets, including
   organization rules and bypasses. Preserve existing requirements.
3. Select observed qualifying checks and verify their association with the PR's
   current head or merge SHA. A successful `workflow_dispatch` run alone doesn't
   prove that a required PR check reports or permits merging.
4. Keep required workflow entry points running for all applicable PRs. Avoid
   workflow-level path filters that leave required checks pending. Put expensive
   conditional work behind a stable reporting job. Add `merge_group` handling
   if the repository uses a merge queue.
5. Avoid running the same suite for both a feature-branch push and its PR unless
   the distinction is intentional. A usual topology is PR events plus main pushes
   and reusable exact-source release checks. Update the publisher's event/identity
   lookup at the same time. Verify current API metadata: PR associations may be
   absent after merge; use independent exact commit/PR verification rather than
   accepting unrelated checks or treating missing metadata as a failed test.

The PR-title starter includes `edited` to recheck human title changes. Since
token-created `edited` events may be suppressed, verify automated retitles too.
Use PR titles as squash subjects and recheck them at merge time; checking the
title doesn't validate every commit's message or breaking-change footer.

## Settings readback

Apply only the agreed settings diff, then read each setting back.

Reconcile description, topics, repository features, squash/merge settings,
default branch, visibility, protections, and rulesets. Record partial writes
individually; organization restrictions, plan limitations, and permission errors
are blockers with next actions, not success. Visibility changes require the
exact target and desired state to be established first.

## Publication contract

Separate release approval, packaging, publication, and downstream installation.

1. Resolve the maintainer-merged release PR to an exact source commit and version.
   Verify manifest, lockfile, app/plugin metadata, changelog, and tag agreement.
2. Define exact asset names per supported platform, checksum sidecars, and any
   required metadata/notices. Build and smoke-test that source, not a moving
   default branch. Record artifact provenance and tested architectures.
3. Create or resume the intended draft. Verify target commit, version, asset
   names, sizes, digests, and completeness before changing it to public.
4. Publish only after all contract checks pass. Serialize publication and reject
   stale retries; concurrency alone doesn't guarantee ordering. Resume incomplete
   drafts without overwriting a completed public release's contents.
5. Verify public metadata/downloads and installation independently. For a
   source-only release, use a source archive/tag contract and reproducible setup;
   binary assets aren't mandatory.

Don't rely solely on token-created tag/release events to start packaging or tap
updates. Use explicit job dependencies or an authorized, verified event path.
Release Please JSON starters in [template guidance](reference-examples.md#render-and-validate)
create drafts but don't implement packaging or public publication.

For workflow queues, transport-boundary tests, and first live publication, follow
[release operations](release-operations.md). A passing mocked publisher or green
automation PR is local/hosted-check evidence, not proof of a functioning release.
