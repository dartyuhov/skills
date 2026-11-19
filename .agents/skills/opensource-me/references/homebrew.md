# Owned Homebrew tap

Update an owned tap only after the app release is complete, public, and verified.
This recipe covers casks; preserve a working formula route for source-built CLIs.

## Inputs and credentials

Recheck the installed Homebrew CLI and current [Cask Cookbook](https://docs.brew.sh/Cask-Cookbook)
before generating Ruby or validation commands.

- Resolve the exact public regular release and tag, app identity, supported
  architectures, minimum OS, asset URLs, and downloaded SHA-256 values.
- Verify every architecture's artifact and sidecar, plus any required metadata.
  Use the actual public URLs; a guessed URL or draft asset isn't an input.
- Use separate tap-only credentials restricted to the owned tap. The source
  repository's `GITHUB_TOKEN` doesn't grant cross-repository write access.
- Run updater code from a trusted default-branch revision, not an arbitrary
  dispatch ref. Keep tokens out of URLs, logs, files, and global Git config.

## Update and verify

Treat tap publication as an independently retryable transaction.

1. Read the tap's current branch and cask version. Reject downgrades and stale
   requests. For an equal version, verify equivalence and return a no-op; report
   conflicting URLs/digests rather than silently replacing them.
2. Render only the owned cask path. Set version, actual architecture mapping,
   matching checksums, app artifact, homepage, and observed OS requirements.
   Use verified digests rather than `:no_check` for versioned release packages.
3. Validate Ruby syntax and run supported Homebrew style/audit checks. Exercise
   installation on available architectures; report skipped checks explicitly.
4. Inspect the diff and constrain writes to the cask. Detect a changed remote
   base before pushing; refetch and revalidate instead of overwriting newer work.
5. After authorized publication, read back the cask, verify downloads, and run a
   first-install or upgrade smoke test through the actual tap route.

Done: report the app release and tap status separately. If tap authentication,
validation, or publication fails, retry the tap step against the same completed
release after fixing the failure. Keep the public app release intact; tap
recovery doesn't rebuild or republish it.
