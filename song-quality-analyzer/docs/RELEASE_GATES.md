# Analyzer release status

October 14, 2026: the user reported positive beta testing and authorized a
**Windows-only public beta**. Spectracraft 0.1.0-alpha.5 remains an early beta,
with its actual validation scope stated in [Windows beta notes](WINDOWS_BETA.md).
The repository is public and the [Windows prerelease](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-alpha.5)
is published with source, dependency materials and checksums. All uploaded asset
digests match the locally verified files.

## Executed evidence

- The sole canonical full-spectrum scanner supports validated MP3, WAV, AIFF,
  FLAC, AAC and ALAC variants. HQ requires >=40% at or above 20 kHz;
  otherwise MQ requires >=40% at or above 18 kHz. Bitrate is informational.
- 83 app tests passed, with one POSIX-only skip on Windows; 58 format/edge
  fixtures and 16 integrity fixtures passed. Real-track metrics and hashes
  remained unchanged. Packaged worker/source comparisons passed.
- A 103-track browser run completed as automatic alphabetical 50/50/3 batches.
  Pause/Resume, refresh reconnect, Stop retaining completed batches, source
  preservation, report redaction and a narrow viewport were checked.
- The loopback API checks token, Host and Origin; metadata renders as text.
  The decoder restricts protocols/demuxers. No app upload or telemetry flow
  was found. This does not qualify every native runtime's network behavior.
- Source/package provenance, scanner hashes and actual test scope are recorded
  in [local results](LOCAL_TEST_RESULTS.md) and [dependency review](DEPENDENCY_REVIEW.md).

## Beta publication contents

Publish reviewed source, a complete Windows x64 portable ZIP, dependency
notices and matching source/build materials, checksums and beta notes.
Exclude music, artwork, machine-specific settings, tokens, private caches,
patch helpers and diagnostic logs. Mark the GitHub release as a prerelease.
Keep the unsigned status and prerequisites visible. Do not claim a stable
release, native Mac/Linux support or a universal privacy/security guarantee.

## Continued qualification

Clean Windows installation, native pickers/drop, display scaling/snapping,
window shutdown, outbound runtime traffic capture, storage pressure and
broader device/usability testing remain work for the beta. Use the
[native beta guide](BETA_TEST_GUIDE.md) to collect concrete results.

Mac Intel and Apple Silicon need separate builds and native qualification
before being advertised. Linux is deferred. A paid website, automatic updater
and other suite tools remain future concepts; no such services are included.

## Disclosed limits

Automatic analysis batches contain up to 50 selected tracks; 50 is not a
selection/folder-size limit. Inventory is bounded to 10,000 candidates and
100,000 visited entries. Canonical processing is bounded to 24 hours/172,800
bins per track and 250,000 retained report bins per batch. Rate/channel bounds
are 8–192 kHz and up to eight channels, not qualification of every variant.

Detailed evidence/export covers the latest completed batch, while compact
folder summaries span completed batches. Spectrum evidence defaults to 32 MiB;
that budget can omit a graph while complete grading continues. Other limits
return ungraded errors. The latest three finished owned batch caches are
retained; active, legacy/unmarked and unexpected contents are protected.
This is not a total disk-size cap. Processing uses CPU, without GPU acceleration.

The analyzer does not rename, retag, move, delete or re-encode songs, and it
does not edit DJ collections. Reports are sanitized, not anonymous. Instagram
promotion should demonstrate verified shipped behavior after publication.
