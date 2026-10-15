# Spectracraft 0.1.0-beta.1 — release candidate

This candidate prepares Windows x64 and Apple silicon macOS 15+ packages.
It is not a stable release. Publication and final download verification are pending.

## Changes

- Text starts about 12.5% larger. Aa beside the appearance button offers saved
  90–150% text sizing; click the percentage to reset to 100%.
- Small windows reflow while the track table can scroll horizontally.
- Windows initializes the NumPy runtime before background processing threads,
  fixing a first-import stall reproduced during repeated UI checks.
- Refreshed release runtime: Python 3.13.16; actual embedded OpenSSL and Expat
  versions are recorded and checked against each package's manifest.
- Mac metadata includes numeric build 1001 and the readable beta version.

The sole canonical scanner and the 40% full-duration HQ/MQ rules are unchanged.
Bitrate remains informational. Songs, names, tags, artwork and DJ collections
are unchanged. Processing stays local; no accounts or analytics are added.

## Install and known limits

Windows: extract the entire ZIP and run Spectracraft.exe with _internal beside
it. Microsoft Edge WebView2 Runtime is required. The build is unsigned.

Mac: extract the macos-arm64 ZIP with Finder and open Spectracraft.app.
Apple silicon and macOS 15+ only; no Intel Mac package or Linux support is
claimed. The candidate is ad-hoc signed and not notarized. Apple may block the
first launch; follow the per-app Privacy & Security instructions only if you
trust the downloaded source. Do not disable Gatekeeper globally. The signing
route is an owner release decision, not a software test result.

Native picker/save/drag gestures, clean-account installation, permission denial,
runtime network capture and storage/cloud/device edge cases retain the documented
beta qualification limits. Automated dialogs substitute selected paths. General
positive M4 feedback does not individually prove every native interaction.

Spectral grades indicate measured high-frequency coverage, not audible quality
or original-source authenticity. Silence counts toward the whole duration.
Noise may add high-frequency energy. Detailed report export covers the latest
completed batch; folder summaries combine completed batches.

Each platform has matching dependency source materials, notices, manifest and
SHA256SUMS. Project-owned source is GPL-3.0-only; dependencies retain their own
terms. The earlier Windows alpha.5 release remains available unchanged.
