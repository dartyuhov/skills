# macOS distribution

Use this recipe for a Swift macOS app with native downloadable packages. Choose
architectures, minimum OS, resources, and signing policy from the actual project.

## Versions and packaging

Make every version source and package input explicit.

1. Use a currently supported generic Release Please strategy, usually `simple`
   with `version.txt`. Map marketing version, build number, plist or build
   settings, and tag. Use validated extra-file updaters or derive build metadata
   from one source; a build number needn't share the marketing version's format.
2. Preserve actual SwiftPM/Xcode build and test commands. Verify the release
   scheme/configuration, toolchain, deployment target, and required entitlements.
3. Assemble the `.app` with executable, plist, icons, resources, embedded helpers,
   and license notices. Validate bundle identifier, versions, linked libraries,
   architectures, and minimum OS for every executable.
4. Build native DMGs on macOS, with an Applications shortcut if appropriate.
   Mount each DMG, inspect/copy the app, and detach reliably. Verify versions and
   resources in the packaged app, not just the build directory.
5. Produce checksums after final signing/stapling and packaging. Define the
   required DMG/sidecar/metadata set, then follow the
   [draft-first contract](github-operations.md#publication-contract).

Done: packages match the exact release source and asset contract. Separate
architecture builds are acceptable; a universal build is a project decision.

## Signing truth

Describe only the signing and notarization actually observed on shipped bytes.

- Development signing supports development; it isn't Developer ID distribution.
- Ad-hoc signing supplies a local signature without a verified developer
  identity. It isn't Developer ID signing or Apple notarization.
- Developer ID distribution and notarization require the appropriate certificate,
  hardened runtime, timestamp, accepted notary result, and ticket handling.
  Verify signatures, entitlements, ticket/stapling where applicable, and
  Gatekeeper assessment. Signature verification alone doesn't prove notarization.

Recheck Apple's [notarization requirements](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
and installed `codesign`, `spctl`, `notarytool`, and `stapler` help at runtime.
Apple's current workflow uses `notarytool`, not `altool`. Keep signing credentials
outside fork PR execution. Document app-specific launch approval honestly;
installation guidance must preserve global security protections.

## Installation evidence

Test the public download path, including quarantine behavior, on a clean user
profile or suitable test machine when available.

Verify first launch, requested permissions, a real app action, quit/relaunch,
and upgrade behavior. For privacy-sensitive apps, record permission grants and
restart behavior rather than inferring them from source. Mark UI, architecture,
or minimum-OS checks unavailable in the current environment as manual follow-ups.
An owned [Homebrew tap](homebrew.md) is a downstream route, not proof of launch.
