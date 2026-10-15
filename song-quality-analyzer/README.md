# Spectracraft

**A ResetLab Craft tool for music quality and integrity checks.**

Read a music folder or one audio file, measure complete tracks, inspect the spectrum and save a report. Music, tags, artwork and DJ collection data stay unchanged. Processing stays local; there are no accounts, analytics or music-upload services. See [Privacy](docs/PRIVACY.md) for local caches and report contents.

## Current status

**Public beta: 0.1.0-beta.1, published October 15, 2026.**
[Windows x64 ZIP](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-beta.1/Spectracraft-0.1.0-beta.1-windows-x64.zip) ·
[Apple silicon Mac ZIP](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-beta.1/Spectracraft-0.1.0-beta.1-macos-arm64.zip) ·
[Release notes, sources and checksums](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-beta.1).
Both packages are unsigned early betas. Mac requires Apple silicon/macOS 15+,
is ad-hoc signed and is not notarized; see its first-launch instructions.
Native checks passed and M4 volunteer feedback was positive; manual qualification
limits remain documented. Linux is deferred.

| Platform | Actual evidence |
| --- | --- |
| Windows x64 | Beta target. User testing reported good; source, browser and packaged worker checks pass. Clean-machine installation, native gestures/display scaling/shutdown and runtime traffic capture are not fully qualified. |
| macOS Apple silicon | Public unsigned beta. Native macOS 15 source, normal extracted package and 19 Cocoa UI checks pass; positive M4 feedback. Patched runtime and numeric build identity verified. [Download and first launch](docs/platforms/macos/README.md). Signing/notarization and remaining manual qualification are future work. |
| macOS Intel | Native macOS 15 source suite and six-format checks passed; no Intel app package qualified. |
| Linux | Deferred and untested. Consider after Windows and Mac qualification. |

## Start here

1. Choose [Windows](docs/platforms/windows/README.md) or [Mac](docs/platforms/macos/README.md), then follow [Installation](docs/INSTALLATION.md) for download or source setup.
2. Add music using one control for a folder or audio file; metadata loads automatically. Select the tracks you want to analyze.
3. Analyze: selected tracks run in title A–Z order through automatic batches of 50. Pause/Resume holds your place; Stop retains completed batches. Inspect results and save the latest completed batch.

The [short user guide](docs/USER_GUIDE.md) explains folder scores, grade filters and errors. Use the sun/moon button near the upper right for appearance. Scrolling is Smooth by default and respects reduced motion, keyboard, fine gestures and nested results.

Title/artist sorting preserves selections and scores. Analysis has a sticky progress panel with current-track context, processed counts and elapsed time. The native drop receiver keeps the strict CSP; actual Windows/Mac gestures remain unqualified. The in-app demo was removed after feedback; synthetic fixtures remain developer tests only.

The desktop window can shrink to 420 × 360 logical pixels for split-screen
work. At narrow widths, the results table scrolls inside its panel while
the page and controls fit the window.

Beta.1 has a larger text default and an **Aa** menu beside the sun/moon control
for locally saved 90–150% text sizing. Click the percentage to reset.

## What the grade means

Supported candidates: MP3, WAV, AIFF, FLAC, AAC and ALAC; actual codecs/containers are checked.

- HQ: measurable signal at or above 20 kHz for at least 40% of the complete decoded duration.
- MQ: otherwise, at least 40% at or above 18 kHz.
- LQ: otherwise.

Alpha.3 uses the updated 40% rule and measures FFT bins at or above each target.
Earlier reports retain their original results; reanalyze to apply the new rule.
See [Quality rules](docs/QUALITY_RULES.md) for the measurement details.

Bitrate and lossless encoding do not determine the grade. These are spectral coverage grades, not proof of authenticity or listening quality. Intentional lo-fi, vintage masters and bass stems may receive LQ and still sound right.

Folder score averages measured grades using HQ 100 / MQ 50 / LQ 0. Errors and unmeasured files are excluded and counted. A trustworthy four-minute header with one minute of decoded audio receives an ungraded integrity error; a valid one-minute edit can still be HQ. A cleanly ending short file without a reliable duration declaration cannot reveal its intended original length.

## Local limits

Analysis automatically continues through batches of 50; 50 is not a selection or folder-size limit. Inventory: 10,000 candidates / 100,000 visited entries with incomplete-inventory warnings. Current-session summaries accumulate across completed batches; detailed evidence and JSON export cover the latest completed batch. Rescanning resets the summary. Processing uses the CPU; GPU acceleration is not implemented.

Canonical limits: 24 hours / 172,800 bins per track; 250,000 retained report bins per batch; 8–192 kHz and up to eight channels are bounds, not qualification of every variant. Spectrum evidence has a 32 MiB default budget; full grading continues without a graph if only that evidence budget is exceeded. New analysis caches retain the latest three finished owned batches. Active, legacy and unrecognized cache contents are preserved; this is not a hard disk-size cap.

## Release and development

The [documentation index](docs/README.md), [repository layout](docs/REPOSITORY_LAYOUT.md), [Windows beta notes](docs/platforms/windows/README.md), [Mac release review](docs/platforms/macos/RELEASE_REVIEW.md) and [release gates](docs/RELEASE_GATES.md) show passed and pending work. Project-owned code is licensed under GPLv3 only. A binary release must include its reviewed dependency notices and corresponding source/build materials. This repository includes the [exact generated canonical scanner](canonical/README.md); dependencies, local reports and private music are excluded from Git source.

Grading uses one maintained canonical scanner. Build copies are generated and hash-verified; never edit another classifier independently. [Format scope](docs/FORMAT_SUPPORT.md) and [edge cases](docs/EDGE_CASES.md) describe practical limits.

Future ResetLab Craft tools: Keycraft, Stemcraft, Setcraft and Cratecraft. They are concepts in the [suite roadmap](docs/SUITE_ROADMAP.md). Paid website and automatic updates remain future ideas only.

## License and reuse

Project-owned Spectracraft source is licensed under **GNU GPL version 3 only** (`GPL-3.0-only`). Others may use, modify and redistribute it, including commercially, provided they follow the [license](LICENSE): preserve required notices, provide corresponding source for distributed covered versions, keep those versions under GPLv3 and identify modifications. Private modifications do not require public release.

The [reuse and branding policy](docs/REUSE_AND_BRANDING.md) distinguishes permitted code reuse from misleading claims of an official ResetLab Craft release. Third-party dependencies retain their own licenses; public binary distribution remains gated by their review. This license does not establish trademark registration or relicense users' music/reports.
