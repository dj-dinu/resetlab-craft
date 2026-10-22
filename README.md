# ResetLab Craft

Focused local music tools for DJs, musicians and producers.

## Bandprism

**See the spectrum. Understand the result.** Formerly Spectracraft, Bandprism
inspects complete tracks and folders, shows spectral evidence and integrity
warnings, and exports a report. Your audio, names, tags, artwork and DJ collection
stay unchanged. No accounts, analytics or music uploads.

**[Windows x64 — download EXE](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-beta.2/Bandprism-0.1.0-beta.2-windows-x64.exe)** ·
**[Apple silicon Mac — download ZIP](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-beta.2/Bandprism-0.1.0-beta.2-macos-arm64.zip)** ·
[Beta.2 release, checksums and matching sources](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-beta.2)

Windows: open the downloaded EXE as a normal user. No separate `_internal` folder
or DLL-unblocking step is needed for the beta.1 loader issue. Microsoft Edge
WebView2 Runtime is required. The unsigned build can still trigger Windows
publisher/reputation warnings; follow your device policy.

Mac: extract the ZIP with Finder and open `Bandprism.app`. Apple silicon (M1+),
macOS 15+. The app is ad-hoc signed, not Developer-ID signed or notarized; its
[per-app first-launch instructions](song-quality-analyzer/docs/platforms/macos/README.md)
still apply.

[User guide](song-quality-analyzer/docs/USER_GUIDE.md) ·
[Windows guide](song-quality-analyzer/docs/platforms/windows/README.md) ·
[Installation](song-quality-analyzer/docs/INSTALLATION.md) ·
[Privacy](song-quality-analyzer/docs/PRIVACY.md) ·
[Repository map](song-quality-analyzer/docs/REPOSITORY_LAYOUT.md)

HQ/MQ/LQ describe spectral coverage, not listening quality or authenticity.
HQ: at least40% of the full duration at/above20kHz. Otherwise MQ: at least40%
at/above15kHz. Otherwise LQ. Bitrate is informational. Older reports keep their
original measurement rules; reanalyze to apply this release's rule.

| Tool | Purpose | Status |
| --- | --- | --- |
| Bandprism | Spectral inspection, folder summaries and integrity checks | Windows x64 and Apple silicon beta |
| Cratecraft | Library organization with reviewed names and tags | Local development, not released |
| Keycraft | Key, BPM and harmonic preparation | Concept |
| Stemcraft | Reuse separated stems where supported | Research |
| Setcraft | Next-song and transition suggestions | Concept |

Intel Mac has historical source-test evidence but no released app package.
Linux remains deferred. See the [suite roadmap](song-quality-analyzer/docs/SUITE_ROADMAP.md).
The parent brand and repository remain **ResetLab Craft / resetlab-craft**;
the shared craft suffix is optional. Prior Spectracraft releases remain historical
downloads with their original filenames, checksums and known limitations.

## Reuse

Project source is [GPL-3.0-only](LICENSE). Use, modify and redistribute under its
conditions; third-party dependencies retain their own terms. See
[reuse and branding](song-quality-analyzer/docs/REUSE_AND_BRANDING.md).
