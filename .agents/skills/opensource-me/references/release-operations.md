# Release operations

Use this reference when implementing or repairing release automation. The release
contract in the work plan determines approval and completion; these checks make
that contract observable across local tests, hosted execution, and user installs.

## Access preflight

Resolve the access path before implementing jobs that depend on it. Use current
official host/CLI documentation and verify the actual installation when access
permits; configuration presence alone doesn't prove permission.

1. Inventory required capabilities: opening/updating release PRs, triggering their
   CI, reading exact-source checks, creating tags/releases, and any downstream
   updates. Choose the supported token/event path for those capabilities.
2. Read the actual App identity and installation repository selection. Verify
   required effective permissions, not just requested App permissions. After a
   permission change, check whether the installation needs its update accepted.
   After an App rename, reconcile bot-login settings in each authorized target;
   identify other affected repositories without silently modifying them.
3. Check required variable/secret names and presence only. Shared OAuth/build
   configuration, release-bot keys, and end-user signing/account material have
   different owners and lifetimes. Keep these roles separate in instructions.
4. Existing GitHub secrets cannot be read back. If a key file is required, ask
   for its local path or guide the user to generate an additional key. Upload
   through stdin without printing its contents. Retain active keys needed by
   other projects. Reuse an existing App only within explicitly authorized access.
5. For human-only actions, give the URL, UI path, setting name, and expected value
   source together. Explain what the key enables before requesting it. Batch
   related setup where practical; verify access afterward with read-only requests
   and TLS certificate verification enabled. Keep keys/tokens out of chat, saved
   logs, source files, command arguments, and generated artifacts.

Done: required access is verified or a precise blocker names the missing
permission/setting, owner, and next action. Continue unrelated local work while
blocked; don't claim the automation is active.

## Workflow lifecycle and transport checks

Test the lifecycle and executable boundary, not just generated YAML or an ideal
in-memory GitHub server. Choose checks relevant to the selected release route.

- Verify the first version and subsequent bumps using the pinned planner. Check
  every version source, lockfile, release manifest, changelog, and package metadata.
- Qualify trusted bot PRs by repository, author/App, managed branch, generated
  release metadata, and exact source/version. Titles or labels alone don't prove
  approval. A copied pending label/body on an ordinary PR must neither authorize
  publication nor indefinitely block the release-PR writer.
- Check ordinary and bot-created PR events and exact tested SHAs. A failed or
  unfinished latest qualifying check must not be bypassed by an unrelated green
  run. Missing API associations require independent verification, not looser trust.
- Simulate changes merged while publication is in progress, workflow replacement,
  missed wake-ups, and lifecycle-label failures. Default Actions concurrency may
  replace pending runs despite `cancel-in-progress: false`; it isn't a durable
  release queue. Reconcile durable approved state, process versions in order,
  and wake the release-PR writer after publication. Use recovery triggers suited
  to the current host; verify schedules/events rather than promising timing.
- Exercise the real CLI against a controlled server for binary request/response
  bytes, headers, process exits, and early connection closure. For GitHub uploads,
  verify the installed CLI's handling of stdin and known content length. Keep
  useful redacted stderr when a broken pipe otherwise hides the HTTP error.
- Validate creation responses and read back the exact draft ID before asset
  writes. Test a newly created draft absent from a subsequent list response;
  don't depend on immediate list visibility or blindly repeat ambiguous writes.
- Cover missing/corrupt assets, interrupted uploads, tag/source mismatch, and
  completed-release retries. Resume the intended draft, preserve correct assets,
  and verify public releases without replacing bytes or moving published tags.
- Run contracts under the hosted runtime/version and relevant concurrency. If
  the runner crashes, distinguish its diagnostics from an assertion failure.
  Reproduce and correct the interaction; avoid hiding failures with retries,
  skipped tests, or broader timeouts. Test fixtures must control asynchronous
  ordering where the scenario depends on it.

Done: local behavioral and transport checks pass, and remaining hosted-only
assumptions are explicitly identified for the first live run.

## First hosted release

For a requested launch, continue through the authorized endpoint. If authorization
stops earlier, leave the remaining steps as explicit pending work with URLs and
the required approval. Never merge a release PR just to test automation without
publication approval.

1. Observe the App create/update the real release PR. Confirm synchronized version
   files and one intended PR check per update, including unattended bot events.
2. After the agreed approval action, follow exact-source checks, packaging, draft
   validation, publication, and lifecycle completion. Retain first failed results;
   fix evidenced causes within the authorization ledger rather than rerunning
   until green or introducing an unagreed manual publication step.
3. Verify the public tag/source, full asset names, sizes, digests/checksums, and
   anonymous downloads with no private authentication. Compare to the approved
   same-run artifacts, including signing state and legal resources where relevant.
   Inspect final distributables for unintended account/signing material; classify
   intentionally embedded app configuration without printing its value.
4. Verify the pending release state clears and changes deferred during publication
   reach the next release PR. Stop before merging that PR unless authorized.

Done: actual hosted URLs and readbacks establish publication and lifecycle
recovery. CI success alone doesn't establish either public downloads or installability.

## Guide-driven installation

Follow the published guide as a new user, using the public release rather than a
local source rebuild. A separate clean directory/host reveals dependencies hidden
by the maintainer's checkout, ignored configuration, certificates, or cached tools.

1. Record selected release/source, asset hashes, host/device versions, and the
   guide revision. Run its download and integrity steps as written. Check that
   independently fetched components resolve to the same selected release.
2. Follow setup/signing/install steps using only documented prerequisites. Where
   signing is per-user or per-device, explain who supplies each certificate and
   why. Preserve an existing author's identity and user state for upgrades; the
   same profile name alone doesn't prove certificate continuity.
3. Verify launch and representative first use. Coordinate account approval and
   physical output confirmation with the owner. Native playback, sound, device
   controls, and readability need device/viewer evidence beyond browser fixtures.
4. Verify an upgrade with retained session/settings where applicable. A destructive
   fresh-install test needs explicit permission; don't uninstall a working app to
   manufacture acceptance. Mark unavailable checks blocked or pending.
5. Record incorrect commands, missing prerequisites, and unsupported claims as
   guide defects. Repair and rerun affected steps; distinguish a documentation
   error, an installer defect, and an environment-specific limitation.

Done: evidence separates public availability from guide accuracy, successful
installation, first use, and upgrade retention. Report exact pending device checks.
