# Quick guide

## Analyze a folder or one file

1. Use Choose folder or Choose file in the desktop app. In the development browser, paste the full path to either.
2. Click Read folder or file. A file selection reads only that file; a folder lets you select up to 50 tracks. Existing HQ filenames are checked again.
3. Analyze selected tracks. Wait for the complete result or use Cancel.
4. Open View evidence to inspect qualifying seconds, the timeline and the spectrum.
5. Save the JSON report for the latest completed batch.

For larger folders, use Select next batch. The folder summary accumulates measured grades within this inventory. Detailed evidence/report export is retained for the latest batch to bound memory. Reading a folder or file again resets the summary. A single-file result is labeled as a file score.

## Understand the result

HQ meets the full-track 20 kHz coverage rule; MQ meets the 18 kHz rule; LQ meets neither. Bitrate is information only. The grades do not certify authenticity or subjective sound quality.

Folder score uses HQ = 100, MQ = 50, LQ = 0 across measured tracks. Errors/unmeasured files are excluded and counted, so a partial score must be read with its coverage. Use Show to filter All, HQ, MQ, LQ, Error or Unmeasured. Filters preserve selection and the score.

An error receives no grade. A reliable header/decoded-duration mismatch, unsupported stream, corruption or resource limit calls for review. A valid short edit is not automatically damaged. No analyzer can infer missing original content solely from a cleanly ending short file without a trustworthy declaration.

## Appearance and scrolling

The sun/moon button near the upper right switches Light/Dark and saves the choice locally. On first use the system appearance is followed until you choose one. Smooth scrolling is the preset; reduced motion, keyboard navigation, touch/fine gestures and nested/horizontal result scrolling keep native behavior.

## Your files and reports

The app reads songs without changing audio, names, tags, artwork, cues, grids or playlists. Reports remove machine-specific absolute/cache paths and free-form decoder errors. Relative filenames and technical results remain; review them before sharing. Private diagnostics and spectrum caches stay on this computer. New caches keep the latest three finished owned analyses; export reports you want to keep. Active jobs, legacy/unmarked folders and unexpected content are preserved, so they can still take disk space. See [Privacy](PRIVACY.md).

If a decoder or folder is unavailable, check [Installation](INSTALLATION.md). If an error persists, save a sanitized report and describe the platform, format and action; keep private diagnostics/session links out of public issues.

Long song titles, artist names and filenames use a bounded single line with an ellipsis. Hover to read the full value. Full text remains in the accessible page and reports; the source tags/filenames are unchanged.
