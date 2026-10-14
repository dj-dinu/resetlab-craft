# Spectracraft Windows public beta

Release candidate: **0.1.0-alpha.5**, Windows x64, portable ZIP.
The user approved proceeding with a Windows public beta on October 14, 2026,
after reporting that beta testing looked good. Publication is pending release
asset preparation and GitHub publishing access; this document does not claim
that downloads are already live.

## Install and start

1. When published, download the Windows ZIP from
   [GitHub Releases](https://github.com/dj-dinu/resetlab-craft/releases).
2. Extract the complete ZIP into a writable folder with a short path.
   Keep `Spectracraft.exe` beside its `_internal` folder.
3. Open `Spectracraft.exe` as a normal user. The app needs the
   [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/).
4. Use **Add music** to choose a folder or audio file. Metadata loads automatically.
5. Choose **Analyze selected tracks**. Selected songs run in title A–Z order
   through automatic batches of 50. Use Pause/Resume or Stop when needed.
6. Inspect evidence and save the latest completed batch's JSON report.

The beta is unsigned. Windows may display publisher/reputation messages;
review the source and published checksums, and follow your device's security
policy. Report a launch block rather than disabling security protections.
No administrator access, developer Python, app account or subscription is
needed for normal use of the portable build.

## Included behavior

- MP3, WAV, AIFF, FLAC, AAC and ALAC with actual codec/container validation.
- Full-duration spectral grades: HQ >=40% at or above 20 kHz; otherwise MQ
  >=40% at or above 18 kHz; otherwise LQ. Bitrate is informational.
- Folder spectral-grade score, grade filters, title/artist sorting and evidence.
- Automatic batches, overall progress and Pause/Resume. Stop retains completed
  batches; interrupted batches return no partial grades and can be selected again.
- Dark/light appearance, smooth scrolling and tidy long-title display.
- Local analysis that preserves audio, names, tags, artwork and DJ collections.

## Known limits and validation

Processing uses CPU, without GPU acceleration. Inventory is bounded to 10,000
candidates and 100,000 visited entries. Detailed evidence and JSON export cover
the latest completed batch; the folder summary includes all completed batches
in the current inventory. Closing the app ends processing; there is no saved
cross-launch continuation. A graph may be omitted for an evidence-budget limit
while full grading continues. Storage/cache limits are described in the
[user guide](USER_GUIDE.md).

Spectral coverage is not proof of listening quality, authenticity, original
bitrate or a complete intended original recording. Noise can produce high
frequency energy; a vintage master may have limited bandwidth and sound right.

Executed checks: 83 application tests passed with one POSIX case skipped on
Windows; 58 format/edge cases and 16 integrity cases passed; source and packaged
worker comparisons and real-track Pause/Resume/Stop checks passed; a 103-track
browser run completed as 50/50/3, with preserved file hashes and sanitized export.
See [local test results](LOCAL_TEST_RESULTS.md) for scope.

User testing is positive. Clean-machine installation, native dialogs/drop,
display-scale combinations, actual window shutdown and offline runtime traffic
capture still need broader beta feedback. Neither Mac architecture nor Linux
is an advertised beta platform. This is not a stable-release or universal
security certification.

## Feedback and reuse

Use [GitHub Issues](https://github.com/dj-dinu/resetlab-craft/issues) for a
reproduction, app version, Windows version, format and expected/actual result.
Use a synthetic or shareable sample. Reports retain relative filenames; review
them before sharing. Never post session links, private music or local diagnostics.
For sensitive findings, arrange a private channel with the owner before sharing.

Project-owned source is GPL-3.0-only; third-party components retain their own
terms. A downloadable build must ship notices and matching source/build
materials alongside it. See [reuse and branding](REUSE_AND_BRANDING.md),
[dependency review](DEPENDENCY_REVIEW.md) and [privacy](PRIVACY.md).
