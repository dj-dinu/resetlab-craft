# Spectracraft for Mac

**Status: Apple silicon beta candidate; no public Mac release yet.**

The current `.app` targets Apple silicon (M1 or newer), macOS 15 or later. The
package contains its own runtime and audio decoders; Python and Homebrew are
build requirements, not requirements for a tester running the app. Intel app
packages and older macOS versions need separate qualification.

## What has been tested

- Native macOS 15 Intel and ARM64: 87 application tests on each architecture,
  canonical hash/self-test, JavaScript checks and six-format analysis.
- ARM64 package: extracted archive, exact source/worker comparisons, native
  decoder, normal window launch/quit and 17 instrumented Cocoa/WKWebView checks.
- Volunteer feedback: a MacBook Air M4 successfully processed a real 45-track
  folder and a single file. Screenshots show zero analysis errors, correct
  folder arithmetic and grades consistent with the 40% spectral coverage rule.
  The tester reported macOS 26.6.2; that OS version was not independently verified.

The [testing guide](TESTING.md) distinguishes native source tests, normal
packaged launch, instrumented UI automation and volunteer feedback. Native
dialog selections were substituted in automation; actual dialogs, Finder
drops, permission prompts and clean downloaded-app launch remain manual checks.

## Volunteer download

The qualified October 14 test kit is available from
[GitHub Actions run 38637798836](https://github.com/dj-dinu/resetlab-craft/actions/runs/38637798836/artifacts/11928298915).
GitHub sign-in/read access is required for workflow artifact downloads. This
artifact expires November 13, 2026; it is not a permanent public download.
See [GitHub's artifact download guidance](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).

Extract the outer kit and then `Spectracraft-apple-silicon-test.zip` with Finder.
Follow the included `MACOS_VOLUNTEER_TEST.md` or the [full checklist](VOLUNTEER_TEST.md).
The kit supplies matching project/dependency sources, notices, checksums and
generated test audio. No private music is needed for reporting a UI issue.

This build is **ad-hoc signed and not notarized**. Record any launch block or
permission prompt. The review also found that its bundled Python/OpenSSL/Expat
runtime needs a security refresh before a public Mac release. No Spectracraft
exploit was demonstrated. Do not disable system security globally to test.
See the [release plan](RELEASE_PLAN.md) for runtime, signing and manual gates.

## Next steps

1. Complete the runtime and remaining manual checks in the [release plan](RELEASE_PLAN.md).
2. Freeze and requalify the exact rebuilt candidate and its source materials.
3. Publish a clearly versioned Apple silicon prerelease with matching source,
   dependency materials, checksums and installation notes after release approval.

For development, use [native source/build instructions](TESTING.md).
For everyday behavior, use the [shared user guide](../../USER_GUIDE.md).
