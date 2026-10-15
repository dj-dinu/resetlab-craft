# Mac release review — October 14, 2026

> October 15 update: **[0.1.0-beta.1 is public](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-beta.1)** for Apple silicon/macOS 15+. The owner explicitly chose an unsigned/ad-hoc beta with the first-launch warning explained. The runtime was refreshed to Python 3.13.16/OpenSSL 3.5.9/Expat 2.8.5 and checked inside the package. Build 1001, matching sources/checksums, all 19 Cocoa UI checks and shutdown cleanup pass. Public app downloads match the tested hashes. Developer ID/notarization and remaining manual qualifications are future work; the original findings/plan below are historical and do not describe an unpatched current beta.

## Historical review and plan

Status: positive ARM64 candidate evidence; public Mac release remains pending.
This review separates software tests from deployment/security qualification.

## Executed evidence

| Check | Result and scope |
| --- | --- |
| Canonical source hash and self-test | Pass; unchanged engine `b1a7509f684641c6d23b381bea4853f4c87e94135227917a67bad9d9e5ccf0c8`, full-duration 40% rules |
| Fresh local application suite | 87 tests run: 86 passed, one POSIX-only filename case skipped on Windows |
| Auth/pause transport failure | Initial full run had one Windows socket-abort error during an expected cross-origin 403; isolated test and a complete unchanged rerun passed. Initial failure retained privately; no auth bypass or product fix established |
| JavaScript | Sorting/selection and automatic 50/50/3 batching pass; Cocoa whitelist/promise protocol passes with dynamic code generation disabled |
| Source format smoke | Six formats, acknowledged Pause/Resume and unchanged input hashes pass |
| Canonical format/edge harness | 56 cases pass in this rerun; this count is distinct from historical 58-case runs |
| Integrity harness | 16 cases pass, including four-minute declaration/one-minute decode remaining ungraded, and a valid one-minute HQ edit |
| Existing Windows alpha.5 frozen worker | Nine inputs across six formats and real HQ/MQ/LQ references; exact metrics, time bins, spectra and unchanged hashes pass |
| Existing native macOS 15 baseline | [Run 38637798836](https://github.com/dj-dinu/resetlab-craft/actions/runs/38637798836): 87 source tests pass on each Intel/ARM64 runner; ARM64 normal package and 17 separate instrumented Cocoa checks pass |
| Existing Mac kit re-verification | All 79 listed file checksums pass; normal app has no UI test driver; matching source, 23 source archives/receipts and 110 synthetic inputs present; archive preserves symlinks |
| Real Mac feedback | MacBook Air M4; macOS 26.6.2 as reported, not independently verified. Screenshots show 45/45 tracks measured, no errors, correct 56.7 folder score and a correct single-file HQ result |
| Fresh PyPI advisory lookup | Zero matches for 20 exact recorded Mac package/version pairs in OSV; Python/OpenSSL/Expat and all other native libraries are outside this result |

The Mac app ZIP remains SHA-256
`69565b7f409f8ae28bcda194f8298624bfbb8054107630a9e4ef64ff2796e263`.
No new Mac native execution is implied by rechecking an existing archive.

## Findings requiring action before public Mac release

1. **Bundled runtime refresh:** the inspected app contains Python 3.12.10,
   OpenSSL 3.0.16 and Expat 2.7.1, which lack later upstream security fixes.
   No Spectracraft exploit was demonstrated; refresh and requalify the native
   bundle rather than describing this inventory as security-complete.
2. **Downloaded-app and native interactions:** automation substitutes dialog
   selections. General volunteer success does not individually confirm Finder
   drops, native save/cancel, paused shutdown, network-permission denial or
   clean-account Gatekeeper behavior.
3. **Signing:** current package is ad-hoc signed, not notarized. Decide the
   distribution route, then test/hash the actual final downloaded package.
4. **Release identity:** align the next build's numeric bundle version and
   readable prerelease label with its manifest and published source.

See the [ordered release plan](RELEASE_PLAN.md) for actions and primary sources.
Intel installers, Linux and older macOS versions remain unqualified. Runtime
network capture and storage/cloud/device edge cases retain their documented
scope limits; do not turn the results above into universal privacy claims.

## Repository hygiene and organization

Platform guides now live under `docs/platforms/windows/`, `macos/` and `linux/`.
Old guide filenames forward to the current pages. Shared source, the canonical
engine, tests, launcher paths and workflow working directories remain intact.
Private screenshot attachments now have an explicit root ignore rule.
Review evidence with private paths stays outside publishable source.
