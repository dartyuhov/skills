# Reference examples and templates

These projects inform patterns, not dependencies. Their identities below describe
provenance only; generated repositories use their own verified values.

## Provenance

The examples were inspected read-only on November 8, 2026. Working-tree content
can evolve; these observations aren't guarantees about future hosted behavior.

- `dartyuhov/herdr-blink`: `README.md`, `release-please-config.json`, and
  `.github/workflows/release.yml` illustrate a Rust host plugin, synchronized
  Cargo/plugin versions, locked target builds, binary smoke tests, SHA-256
  sidecars, and draft-first publication. Its workflow also dispatches release
  PR builds: that pattern alone doesn't establish a valid required PR gate.
- `dartyuhov/vishot`: `README.md`, `release-please-config.json`,
  `.github/workflows/publish-release.yml`, and
  `.github/workflows/update-tap.yml` illustrate Swift `simple` versioning,
  plist updates, exact-source package approval, complete native DMG publication,
  truthful ad-hoc signing documentation, separate release/tap credentials, and
  independent tap recovery.
- Their trade-offs differ: a host plugin needs host installation and resource
  compatibility; a GUI app needs app-bundle, DMG, signing, permission, and UI
  verification. Neither project's platform matrix, account, minimum OS, helper
  scripts, or install commands are universal defaults.

## Render and validate

Templates are small starting points. Adapt them to the inspected repository;
preserve working automation instead of replacing it wholesale.

1. Select templates from [the template directory](../assets/templates/). Copy
   into a staging tree, remove `.tmpl`, and map to these destination paths:
   `README.md`, `CONTRIBUTING.md`, `LICENSE`,
   `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/bug.yml`,
   `.github/ISSUE_TEMPLATE/feature.yml`, `scripts/check-pr-title.py`,
   `.github/workflows/pr-title.yml`, `.github/workflows/ci.yml`,
   `release-please-config.json`, `.release-please-manifest.json`, and `version.txt`.
   Use the corresponding basename; choose only one release config starter.
   If you choose `release-please-rust-config.json.tmpl`, rename its destination
   to `release-please-config.json`.
2. Replace literal `{{UPPER_CASE}}` tokens using confirmed project values.
   This isn't Jinja: preserve GitHub `${{ ... }}` expressions. Escape replacements
   for JSON/YAML/Markdown context; multiline command tokens require correct YAML
   indentation. Never evaluate replacement values as template code.
3. Fill commands from actual verified setup/build/test/use behavior. Provide
   installation instructions only for an observed route; remove unsupported
   claims and optional sections. Configuration examples use synthetic values and
   document defaults, discovery, and secret environment variables; exclude real
   credentials and personal state through the existing ignore mechanism.
4. For MIT, use the actual approved holder and year. For another existing
   license, retain it and adapt the README license sentence. Retain all required
   third-party notices separately.
5. For `simple`, create `version.txt` with the current version and seed the
   manifest consistently with release history. For Rust, use the Rust starter
   and verify Cargo/workspace/plugin updates. The JSON files don't install a
   workflow: wire the pinned Release Please action into existing trusted CI,
   using current schema/docs and the [GitHub contracts](github-operations.md).
6. Reject remaining `{{[A-Z][A-Z0-9_]*}}` tokens in destination files. Parse JSON
   and YAML, validate issue forms against GitHub's current schema, and lint
   workflows with an available maintained checker. Verify referenced commands,
   action SHAs, toolchain versions, local paths, and links.
7. Exercise the title checker with valid and invalid titles. Run the rendered
   CI commands locally and inspect real ordinary/release PR checks before adding
   required checks. Record unavailable hosted or platform validation explicitly.

The CI template expects setup and verification commands you supply. Action refs
must be verified full commit SHAs; hosted runner labels must support those action
runtimes. The title workflow runs the base revision's checker against event JSON,
not shell-interpolated PR text. It needs Python 3 and Git, but no write token.

The release JSON starters create drafts and release PRs; they don't package,
publish, sign, notarize, update a tap, or configure merge gates. Source-only
projects can use a reviewed source-release contract instead of binary packaging.
