# Spectracraft

**A ResetLab Craft tool for music quality and integrity checks.**

Read a music folder or one audio file, measure complete tracks, inspect the spectrum and save a report. Music, tags, artwork and DJ collection data stay unchanged. Processing stays local; there are no accounts, analytics or music-upload services. See [Privacy](docs/PRIVACY.md) for local caches and report contents.

## Current status

Private source preview, October 12, 2026. **A public release is not yet qualified.**
No downloadable installer is included. The private beta preparation uses this
source snapshot; native Windows checks and dependency redistribution review
must pass before sharing a packaged build with testers.

| Platform | Actual evidence |
| --- | --- |
| Windows x64 | Source tests, browser workflow and packaged analyzer worker validated. Native window/dialog, clean-machine and shutdown checks still pending. |
| macOS Intel / Apple Silicon | Native source entry point exists; neither architecture has been built or tested natively. No Mac installer is available. |
| Linux | Deferred and untested. Consider after Windows and Mac qualification. |

## Start here

1. Follow [Installation](docs/INSTALLATION.md) for the current local Windows build or developer setup.
2. Choose a folder (up to 50 selected tracks per batch) or one audio file.
3. Analyze, inspect results and save the latest completed batch.

The [short user guide](docs/USER_GUIDE.md) explains folder scores, grade filters and errors. Use the sun/moon button near the upper right for appearance. Scrolling is Smooth by default and respects reduced motion, keyboard, fine gestures and nested results.

## What the grade means

Supported candidates: MP3, WAV, AIFF, FLAC, AAC and ALAC; actual codecs/containers are checked.

- HQ: measurable signal near 20 kHz for at least 30% of the complete decoded duration.
- MQ: otherwise, at least 30% near 18 kHz.
- LQ: otherwise.

Bitrate and lossless encoding do not determine the grade. These are spectral coverage grades, not proof of authenticity or listening quality. Intentional lo-fi, vintage masters and bass stems may receive LQ and still sound right.

Folder score averages measured grades using HQ 100 / MQ 50 / LQ 0. Errors and unmeasured files are excluded and counted. A trustworthy four-minute header with one minute of decoded audio receives an ungraded integrity error; a valid one-minute edit can still be HQ. A cleanly ending short file without a reliable duration declaration cannot reveal its intended original length.

## Local limits

Analysis: 50 tracks per batch; inventory: 10,000 candidates / 100,000 visited entries with incomplete-inventory warnings. Current-session summaries accumulate across batches; detailed evidence and JSON export cover the latest completed batch. Rescanning resets the summary.

Canonical limits: 24 hours / 172,800 bins per track; 250,000 retained report bins per batch; 8–192 kHz and up to eight channels are bounds, not qualification of every variant. Spectrum evidence has a 32 MiB default budget; full grading continues without a graph if only that evidence budget is exceeded. New analysis caches retain the latest three finished owned jobs. Active, legacy and unrecognized cache contents are preserved; this is not a hard disk-size cap.

## Release and development

The [launch checklist](docs/LAUNCH_CHECKLIST.md), [local test record](docs/LOCAL_TEST_RESULTS.md), [security review](docs/SECURITY.md) and [release gates](docs/RELEASE_GATES.md) show passed and pending work. Project-owned code is licensed under GPLv3 only; dependency redistribution and ownership review must be completed before a public release. This source preview includes the [exact generated canonical scanner](canonical/README.md); dependencies, local reports and private music are excluded.

Grading uses one maintained canonical scanner. Build copies are generated and hash-verified; never edit another classifier independently. [Format scope](docs/FORMAT_SUPPORT.md) and [edge cases](docs/EDGE_CASES.md) describe practical limits.

Future ResetLab Craft tools: Keycraft, Stemcraft, Setcraft and Cratecraft. They are concepts in the [suite roadmap](docs/SUITE_ROADMAP.md). Paid website and automatic updates remain future ideas only.

## License and reuse

Project-owned Spectracraft source is licensed under **GNU GPL version 3 only** (`GPL-3.0-only`). Others may use, modify and redistribute it, including commercially, provided they follow the [license](LICENSE): preserve required notices, provide corresponding source for distributed covered versions, keep those versions under GPLv3 and identify modifications. Private modifications do not require public release.

The [reuse and branding policy](docs/REUSE_AND_BRANDING.md) distinguishes permitted code reuse from misleading claims of an official ResetLab Craft release. Third-party dependencies retain their own licenses; public binary distribution remains gated by their review. This license does not establish trademark registration or relicense users' music/reports.
