# Parallel work

Use independent agents when available, with one coordinator integrating results.
If agent tools are unavailable, execute the same assignments sequentially and
record that limitation.

## Assignment contract

Give every worker an explicit contract before it starts.

```text
Repository: {{EXACT_REPOSITORY_AND_HOST}}
Goal and phase: {{BOUNDED_OUTCOME}}
Instructions: {{APPLICABLE_REPOSITORY_INSTRUCTIONS}}
Permissions: {{READ_ONLY_OR_LOCAL_EDIT_SCOPE}}
Owned paths: {{DISJOINT_PATH_LIST}}
Inputs and dependencies: {{DECISIONS_OR_COMPLETED_TASKS}}
Outputs: changed paths, findings, commands/results, blockers, integration needs
Verification: {{CHECKABLE_COMPLETION_CRITERIA}}
```

Workers perform only assigned reads or local edits. The coordinator owns git
writes and remote mutations within the user's authorization. Workers return
requested shared-file edits to their owner rather than editing those files.

## Dependency barriers

Complete each barrier before starting dependent work.

1. Run read-only audits concurrently: documentation/community; tracked
   content/history and notices; build/version/release/install; GitHub settings
   and hosted checks.
2. Reconcile findings and select the recipe. Assign disjoint preparation paths:
   documentation/community, CI/release, and distribution tooling, as applicable.
   Give manifests, lockfiles, release docs, and agent instructions one owner each.
3. Review the combined diff, resolve version/asset/check-name contracts, and run
   integration checks. Preserve unrelated work and working automation.
4. Perform authorized GitHub writes and publication in dependency order. A tap
   update depends on public release verification, not merely a completed build.

Done: every changed path has one owner; returned evidence is integrated; no
worker's passing check substitutes for the combined verification.
