# Quick guide

## Analyze a folder or one file

1. Use **Add music**, then choose **Audio file** or **Music folder**. The desktop also has a native drop receiver for one file or folder; actual OS drag gestures remain part of beta qualification. In the development browser, paste a full path or type it and press Enter.
2. Selection loads metadata automatically. A file selection loads only that file; folders larger than 50 songs are supported. Existing HQ filenames are checked again during analysis.
3. Analyze selected tracks. They run in title A–Z order through automatic batches of 50; no further clicks are needed between batches.
4. Open View evidence to inspect qualifying seconds, the timeline and the spectrum.
5. Save the JSON report for the latest completed batch.

The folder summary accumulates measured grades across completed batches within this inventory. Detailed evidence/report export is retained for the latest completed batch to bound memory. Reading a folder or file again resets the summary. A single-file result is labeled as a file score.

**50 is the analysis batch size, not a selection or folder-size limit.** A 103-track selection runs as 50, 50 and 3 automatically. Up to 10,000 candidates are inventoried; incomplete inventories are marked. Use **Sort** for title A–Z, title Z–A or artist A–Z. Display sorting and grade filters preserve selections and the folder score; analysis order remains title A–Z.

During analysis a progress panel shows the current track, overall processed/selected counts, batch number, percentage and elapsed time. Progress advances when whole tracks finish; it is not a per-second decoding percentage or a completion-time estimate. The initial bar is indeterminate while the first track is processed. On very short windows the panel scrolls with the page so its controls remain reachable. Final source-file verification runs before results are accepted.

Use **Pause** to hold the current decoding position at a safe point, then **Resume** to continue. Wait for the Paused confirmation. Refreshing the browser reconnects to an active or paused run while the app/server stays open; closing the app ends processing. Processing uses the CPU, without GPU acceleration.

Use **Stop** to end the run. Completed batches stay in the folder summary and the latest completed batch can still be exported. The interrupted batch does not return partial grades; use **Select remaining** to retry unattempted tracks. A new run is a new analysis, rather than a saved continuation after closing the app.

## Understand the result

HQ meets the full-track 20 kHz coverage rule; MQ meets the 18 kHz rule; LQ meets neither. Bitrate is information only. The grades do not certify authenticity or subjective sound quality.

Folder score uses HQ = 100, MQ = 50, LQ = 0 across measured tracks. Errors/unmeasured files are excluded and counted, so a partial score must be read with its coverage. Use Show to filter All, HQ, MQ, LQ, Error or Unmeasured. Filters preserve selection and the score.

An error receives no grade. A reliable header/decoded-duration mismatch, unsupported stream, corruption or resource limit calls for review. A valid short edit is not automatically damaged. No analyzer can infer missing original content solely from a cleanly ending short file without a trustworthy declaration.

## Appearance and scrolling

The sun/moon button near the upper right switches Light/Dark and saves the choice locally. On first use the system appearance is followed until you choose one. Smooth scrolling is the preset; reduced motion, keyboard navigation, touch/fine gestures and nested/horizontal result scrolling keep native behavior.

## Your files and reports

The app reads songs without changing audio, names, tags, artwork, cues, grids or playlists. Reports remove machine-specific absolute/cache paths and free-form decoder errors. Relative filenames and technical results remain; review them before sharing. Private diagnostics and spectrum caches stay on this computer. New caches keep the latest three finished owned batches; export reports you want to keep. Active jobs, legacy/unmarked folders and unexpected content are preserved, so they can still take disk space. See [Privacy](PRIVACY.md).

If a decoder or folder is unavailable, check [Installation](INSTALLATION.md). If an error persists, save a sanitized report and describe the platform, format and action; keep private diagnostics/session links out of public issues.

Long song titles, artist names and filenames use a bounded single line with an ellipsis. Hover to read the full value. Full text remains in the accessible page and reports; the source tags/filenames are unchanged.
