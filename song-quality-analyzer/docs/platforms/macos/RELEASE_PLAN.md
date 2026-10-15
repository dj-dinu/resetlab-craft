# Mac public beta release plan

> October 15 update: **[0.1.0-beta.1 is public](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-beta.1)** for Apple silicon/macOS 15+. The owner explicitly chose an unsigned/ad-hoc beta with the first-launch warning explained. The runtime was refreshed to Python 3.13.16/OpenSSL 3.5.9/Expat 2.8.5 and checked inside the package. Build 1001, matching sources/checksums, all 19 Cocoa UI checks and shutdown cleanup pass. Public app downloads match the tested hashes. Developer ID/notarization and remaining manual qualifications are future work; the original findings/plan below are historical and do not describe an unpatched current beta.

## Historical review and plan

Updated October 14, 2026. Scope: **Apple silicon, macOS 15 or later**. Windows
0.1.0-alpha.5 is already public. Intel source tests do not qualify an Intel
installer. Linux, paid services, automatic updates and new tools are deferred.

## 1. Refresh and identify the candidate

The volunteer build has Python 3.12.10, OpenSSL 3.0.16 and Expat 2.7.1. Official
upstream security fixes postdate those libraries. Before public Mac release,
select a supported patched Python/runtime combination, verify the actual
embedded OpenSSL/Expat versions and regenerate the dependency inventory and
matching source materials. A newer executable alone does not establish which
native libraries it bundles. No Spectracraft exploit was demonstrated.

Keep the same canonical scanner and the full-duration 40% HQ/MQ rules. If
updating PyAV or another decoder, repeat exact metrics/time-bin/spectrum and
real HQ/MQ/LQ regressions; do not change the grader to make a test pass.

Give the Mac candidate a documented release/build identity. The current test
manifest/UI say `0.1.0-alpha.5`, while the bundle short version is `0.1.0` and
does not contain `CFBundleVersion`. At the next rebuild, include a numeric build
version and a readable prerelease identity, and verify both against the manifest.
Do not rename or replace existing published Windows assets.

References: [Python security release notes](https://www.python.org/downloads/release/python-31212/),
[Python 3.12 security maintenance](https://www.python.org/downloads/release/python-31215/),
[OpenSSL 3.0 security advisories](https://www.openssl-library.org/news/vulnerabilities-3.0/index.html).

## 2. Qualify the exact rebuilt Mac app

Use native ARM64 macOS and the existing workflow/validation tools. Save the
source commit, build/runtime inventory and archive SHA-256 with the results.

- Canonical hash and `--self-test`; application suite and both JavaScript checks.
- Six generated formats, errors/integrity cases, unchanged input hashes and
  exact source/frozen comparisons. Include real HQ/MQ/LQ regression inputs
  locally where authorized; never upload private music to CI.
- Normal `.app`: native slices, signature verification, archive/extract with
  executable modes/symlinks preserved, isolated runtime, ordinary launch/quit.
- Separate instrumented test app: all existing 17 UI checks, including automatic
  103-track batches, score, progress, acknowledged pause/resume, stop and paused
  shutdown. Keep that driver out of the distributed app.
- Bounded advisory lookup for exact Python package names/versions plus an
  explicit native-library review. No-match results are limited to that database
  and component inventory; they do not establish that every component is safe.

The earlier native run and positive M4 feedback remain useful baseline evidence.
A runtime/package change needs qualification of the resulting new bytes.

## 3. Complete downloaded-app volunteer checks

Use the [volunteer checklist](VOLUNTEER_TEST.md) on an ordinary account without
developer Python/Homebrew. Collect explicit results for native file/folder
pickers and cancellation, Finder drops, report save/cancel/existing-file
protection, Pause/Resume/Stop/paused close, half-screen resize and appearance.

Record exact launch/security/permission prompts; check offline operation and
Local Network permission denial. Confirm no private music is sent and original
file hashes stay unchanged. Remaining storage/cloud/removable-drive cases can
be disclosed as beta scope limits if they do not prevent safe ordinary use.
The current screenshots and general positive feedback do not prove every item.

## 4. Sign, notarize and verify distribution

Recommended broad-release route: Developer ID signing and Apple notarization.
The current kit has only an ad-hoc signature. Signature integrity verification
is separate from downloaded-app Gatekeeper qualification. Follow
[Apple's notarization workflow](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
and [safe app distribution guidance](https://support.apple.com/en-us/102445).

Account enrollment, certificates and credentials remain an owner decision. Do
not put credentials in the repository, logs, source ZIP or test artifacts. After
signing/notarization, archive the final app, verify its signature/notarization
result and test the actual downloaded archive on a clean account. Hash that
final archive; a pre-signing hash no longer identifies the shipped app.

If an explicitly unsigned/ad-hoc public preview is chosen instead, label its
limits and first-launch behavior clearly and obtain that release decision;
never describe it as notarized or ask users to disable security globally.

## 5. Publish a separate, clearly named Mac prerelease

After the gates and release approval:

- Freeze/tag the reviewed candidate and publish a prerelease, with Apple
  silicon/macOS minimum and signing status visible.
- Attach `Spectracraft-<version>-macos-arm64.zip`, matching project source,
  exact dependency source/build materials/notices and `SHA256SUMS.txt`.
- Use a permanent GitHub Releases link for public users. Workflow artifacts
  expire and require GitHub sign-in; do not publish a redirected storage URL.
- Verify public downloads, byte sizes, hashes, source correspondence and the
  ordinary install path before switching the main download table to Mac available.
- Start with a small audience, collect concrete bugs, then record Instagram
  demos of verified shipped behavior. No paid updater or extra feature scope.

## Current decision

**Continue release preparation; keep the existing Mac kit as a test candidate.**
Runtime refresh, explicit remaining native/manual results, signing choice and
final downloaded-package verification are open. See the [review record](RELEASE_REVIEW.md).
