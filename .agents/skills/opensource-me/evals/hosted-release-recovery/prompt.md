---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

The release automation PR is green and merged, but the first publication failed.
The release PR check passed; after merge its Actions run has pull_requests: [].
A draft create succeeded but the following release list omitted it. Binary asset
upload then got HTTP 400 Bad Content-Length and spawnSync EPIPE. Other changes
can merge while this is happening. I approve release repair commits/pushes
directly to main and recovery of this already approved release, but no tag
movement or replacement of published assets. Explain how you will diagnose,
test and finish this launch. Planning simulation only: no network or writes.
