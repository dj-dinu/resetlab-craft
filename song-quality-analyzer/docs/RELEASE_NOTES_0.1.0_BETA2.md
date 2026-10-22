# Bandprism 0.1.0-beta.2

Formerly Spectracraft, by ResetLab Craft. The suite repository stays resetlab-craft.

- Windows now ships as a single-file EXE. This addresses the .NET managed-DLL
  loader failure caused by Internet-zone metadata on beta.1's extracted DLLs.
  No manual ZIP Unblock step is needed for that failure; OS security protections
  and the EXE download marker remain intact. Unsigned publisher/reputation
  warnings and managed-device policies may still apply.
- App windows, UI, exported report filenames, native bundles and current
  documentation use Bandprism. Historical Spectracraft downloads/checksums remain
  unchanged. Existing reports, music and library metadata are not migrated or edited.
- Uses the already-maintained canonical rule: HQ20kHz40%; otherwise MQ15kHz40%;
  otherwise LQ, across the full decoded duration. Reanalyze earlier reports to
  apply the15kHz MQ rule. Bitrate is informational; no authenticity/audible-quality
  guarantee is implied.
- Mac keeps the normal Apple silicon app bundle, ad-hoc signature and per-app
  first-launch warning. No Developer-ID signing/notarization was added.

Release gates include native Windows downloaded-marker startup, application
suite, six-format source/frozen comparisons, integrity and pause/resume/shutdown;
Mac has its own source/frozen/Cocoa UI checks. Qualification is tied to the
recorded source commit and exact artifact hashes. Controlled CI is not a claim
of testing every computer, security policy, gesture or storage device.

No telemetry, accounts, automatic updater or music uploads. Music/audio samples,
filenames, tags, artwork and DJ collection data remain untouched by the analyzer.
Cratecraft remains a separate local prototype and is not included in this release.

Project source: GPL-3.0-only. Exact dependency sources, build materials, notices
and per-platform checksums accompany the release. Both platforms remain unsigned
public betas. Windows requires x64 and WebView2; Mac requires Apple silicon/macOS 15+.
