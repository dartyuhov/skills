# Launch checklist

Use this checklist for a full launch, audit, or resumed launch. Record each item
as observed, pending, blocked, or out of scope, with a path, command result, or
hosted URL. An inaccessible check is unknown, not passed.

## Inspect

Establish identity and scope before preparation or public exposure.

- Confirm the exact repository, host, default branch, visibility, worktree,
  dirty files, stack, version sources, CI, and distribution routes.
- Record the authorization ledger for commit, local merge, push, PR creation,
  settings, visibility, tags, and publication. Reuse approvals within scope;
  handoffs retain both approvals and limits. Audit mode permits inspection only.
- Agree on feature-merge behavior, the publication approval point, artifacts,
  signing responsibilities, and the requested verification endpoint. Inspect a
  user-named reference project before choosing the release route. Preserve useful
  tooling, adapting orchestration to this contract rather than assuming manual
  behavior is desired. New setups default to release-PR approval.
- Assign independent audits using [parallel work](parallel-work.md).

Done: findings identify the target and distinguish evidence from unknowns.

## Prepare

Resolve launch blockers before exposing the repository.

- Adapt the README, source setup, contribution guide, issue forms, PR template,
  example configuration, and ignore rules using [template guidance](reference-examples.md#render-and-validate).
- Preserve the existing license. For an unlicensed project, offer MIT and
  confirm the actual copyright holder and year; an account name isn't evidence
  of ownership. Inventory third-party fonts, icons, binaries, and notices.
- Review tracked content and history, example configuration, bundled resources,
  and accessible Actions logs/artifacts. Select an available maintained secret
  scanner, check its current invocation, and record versions, refs, history
  depth, exclusions, and inaccessible surfaces. Inventory isn't secret scanning;
  a clean scan isn't proof of absence. Report locations, never secret values.
- If exposure exists, record containment and credential rotation actions.
  History rewriting requires a separate recovery decision and authorization.

Done: blockers are resolved or recorded with an owner and next action.

## Automate and configure

Choose only the recipes the repository needs.

- Run real build/test commands locally; verify version sources stay synchronized.
- Use [Rust](rust-distribution.md), [macOS](macos-distribution.md), or existing
  source-only tooling. Define an explicit asset contract before binary builds.
- Follow [GitHub operations](github-operations.md) for credentials, hosted checks,
  repository settings, effective rulesets, and readback.
- Complete the [access preflight](release-operations.md#access-preflight): verify
  App identity, installation, effective permissions, token/event behavior, and
  configuration presence. Give concrete steps for human-only setup; keep keys
  out of source, logs, and chat.
- Exercise lifecycle recovery and the actual CLI/HTTP boundary with controlled
  responses; mocked orchestration alone doesn't establish hosted compatibility.
- Verify one intended PR check per update while retaining main/exact-release
  checks, and update publisher check lookup when changing event triggers.
- Preserve required checks and unrelated settings. Add checks only after
  observing their actual names and source applications on qualifying PR runs.

Done: local checks pass; authorized hosted execution and configuration have
readback evidence, or specific permission/plan restrictions are recorded.

## Launch and verify

Execute remote changes only within the recorded scope and dependency order.

- Reconfirm repository identity and desired visibility before transitioning.
- Build the exact release source; stage a draft and validate every expected
  asset and checksum before publishing. See the [publication contract](github-operations.md#publication-contract).
- Observe the first bot-authored release PR, qualifying CI, and authorized
  release-PR merge through actual publication. Verify lifecycle labels and
  next-release reconciliation. Record permission-blocked steps rather than
  substituting a manual release for unverified automation.
- Read public metadata without private credentials. Verify the release is
  non-draft, has the intended prerelease status, and contains the complete set.
- Follow the guide from public downloads in a clean user environment, verify
  checksums, and check signing, installation, first use, and an upgrade retaining
  state/identity where applicable. Record guide discrepancies and prerequisites
  learned from local maintainer state. Obtain permission for destructive tests;
  record unsupported/unavailable hosts as outstanding manual checks.
- Update an owned [Homebrew tap](homebrew.md) only after public verification.

Done: report changed paths, local checks, observed settings, release/asset URLs,
installation evidence, and remaining blockers. A passing workflow alone doesn't
establish public availability or installability.
