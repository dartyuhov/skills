# Rust distribution

Use this recipe for a native executable or a host plugin implemented in Rust.
Preserve working Cargo/release automation and select only supported platforms.

## Version and build contract

Map versions before adapting the Release Please starter.

1. Inventory package/workspace manifests, inherited versions, `Cargo.lock`, tags,
   changelog, and host-plugin manifests. Use Release Please's `rust` strategy;
   inspect current workspace support and `cargo-workspace` plugin requirements
   in the [manifest docs](https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md).
   Review its proposed changes instead of assuming every workspace file updates.
2. Add explicit extra-file updaters or annotated generic fields for plugin
   metadata. Verify all released version sources in CI.
3. Run `cargo test --locked` and `cargo build --release --locked` with the
   repository's toolchain and required features. For each chosen target, add
   `--target` with its real triple and verify linker/runtime requirements.
4. Smoke-test on compatible native runners. A successful cross-compile doesn't
   establish execution, libc compatibility, architecture, or minimum macOS.
5. Package deterministic asset names and SHA-256 sidecars. Stage installation in
   a temporary directory, verify digests before replacing an installed binary,
   and exercise repeat installation and failed-download/checksum recovery.

Done: each advertised target has build, runtime, and installation evidence, or
an explicit outstanding verification. Follow the [draft publication contract](github-operations.md#publication-contract).

## Native versus plugin installation

Treat the installation route as a separate contract from compilation.

- A native CLI installs an executable and its required runtime resources; use
  only verified flags for its first-use smoke test. Not every CLI has `--version`.
- A plugin also needs the host version, plugin identifier, manifest, registration,
  resource paths, and host install/link/update behavior. Verify current host docs
  and exercise loading and one host action. Running the binary alone isn't enough.
- Keep developer linking separate from public installation. Explain conflicts
  between linked and installed copies using actual host behavior.
- If the installer selects a fallback release, select only complete compatible
  public releases and report the installed version. Never silently mix versions
  of the binary, manifest, or resources.

The `herdr-blink` provenance in [reference examples](reference-examples.md) informs
the plugin branch; its host commands and target matrix aren't portable defaults.
