# Spectracraft 0.1.0-alpha.5 — Windows public beta

Spectracraft by ResetLab Craft analyzes spectral coverage across complete
music tracks and helps DJs/producers inspect a folder without changing music.
This is the first Windows x64 public beta candidate; mark the release as a
GitHub prerelease. Mac and Linux packages are not included.

## Start

Download the Windows ZIP, extract the complete folder and open
`Spectracraft.exe`. Keep `_internal` beside it. No Python installation or app
account is needed; the native window needs Microsoft Edge WebView2 Runtime.
See [installation](INSTALLATION.md) and [beta notes](WINDOWS_BETA.md).

## Features

- Folder or single-file selection with automatic metadata loading.
- MP3, WAV, AIFF, FLAC, AAC and ALAC with validated codec/container handling.
- Full-duration HQ/MQ/LQ spectral grades, folder scores and integrity errors.
- Alphabetical automatic batches of 50, overall progress, Pause/Resume and Stop.
- Filters, title/artist sorting, timeline/spectrum evidence and JSON export.
- Purple light/dark interface, smooth scrolling and compact long titles.
- Local processing that preserves music, metadata and DJ collection data.

HQ requires measurable signal at or above 20 kHz for >=40% of complete decoded
duration; otherwise MQ requires >=40% at or above 18 kHz; otherwise LQ.
Bitrate does not determine a grade. Spectral coverage is one piece of evidence,
not a certificate of authenticity or audible quality.

## Known beta limits

CPU processing only; no GPU acceleration. Inventory is bounded to 10,000
candidates. Folder summaries span completed batches, while detailed evidence
and export cover the latest completed batch. Closing the app ends a run.
Noise may add high-frequency energy; vintage or intentionally filtered tracks
may have limited bandwidth and still sound correct. Reliable declared/decoded
duration mismatches remain ungraded; a cleanly ending short file cannot reveal
an unknown original intended length.

The build is unsigned. Clean-machine Windows installs, native gestures,
display scaling, shutdown and runtime network capture need broader feedback.
No native Mac/Linux qualification is claimed. Existing reports retain the
rule under which they were made; reanalyze for current grades.

## Validation and source

83 application tests pass with one platform-specific skip; 58 format/edge
cases and 16 integrity cases pass. Source/frozen real-track regressions,
Pause/Resume/Stop and a 103-track 50/50/3 browser run pass with preserved file
hashes. See [test scope](LOCAL_TEST_RESULTS.md).

Ship the Windows ZIP, project source ZIP, dependency source/build-materials
ZIP and SHA-256 checksums together. Project-owned source is GPL-3.0-only;
third-party terms and source materials remain included. Review filenames
before sharing reports and keep private diagnostics/session links out of issues.
