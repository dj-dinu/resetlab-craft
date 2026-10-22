# Bandprism: users, benefits and release scope

Updated October 11, 2026. This brief distinguishes the current local alpha from proposed additions. The alpha is a read-only Windows multi-format analyzer using the one canonical engine for MP3, WAV, AIFF, FLAC, AAC and ALAC. A native desktop shell and browser fallback are implemented; a private Windows bundle is being tested. Clean-machine Windows, native macOS and public-package qualification remain pending.

## Product promise

Help people find audio files worth a closer check, understand the measured evidence, and keep a report before a gig, delivery or archive review.

The central question is: **“Does this file contain the frequency coverage I expected, and where should I investigate?”** It can guide listening and follow-up. It cannot establish that a master sounds good, that a source is authentic, or that a player will accept the file.

The user's canonical method remains the one grading engine: HQ requires measurable signal at or above 20 kHz for at least 40% of the complete decoded duration; MQ otherwise requires at least 40% at or above 15 kHz; LQ is the fallback. Encoded bitrate and file format are informational. Keep the existing absolute/relative signal thresholds and channel-power policy. No second scanner or format-specific grading shortcut is authorized by this brief.

Call the displayed result **spectral coverage grade**. Put the measured percentages and evidence beside HQ/MQ/LQ. Successfully decoded narrow-band audio and failed analysis must remain distinct: the former may receive LQ under the rule; the latter receives no grade.

## DJ workflows

| Situation | What the app helps the DJ do | Useful outcome and limit |
| --- | --- | --- |
| Newly downloaded crate | Analyze a batch and inspect lower-coverage files first. | Spend listening time on files that deserve attention. A low result does not establish a bad purchase or illegitimate source. |
| Preparing an upcoming set | Review the selected local files before rehearsal or a gig. | Keep a findings list for follow-up. Decoding successfully in this app does not certify a CDJ, controller or software configuration. |
| Files named HQ, 320, lossless or master | Reanalyze the audio and distinguish the existing label from the measured result. | Avoid relying on a filename or tag as evidence. Never silently rename or retag the file. |
| Two downloads or editions of the same song | Inspect each file's coverage, native format and evidence. | Make an informed listening comparison. The edition with the highest cutoff need not be the preferred master. |
| Radio, extended and DJ edits | See how introductions, breakdowns and outros affect full-duration coverage. | Explain differences between versions without declaring the longer edit worse. Dedicated time-aligned A/B comparison is a later feature. |
| Mashup or edit assembled from different sources | Review the timeline for sections with changing high-frequency coverage. | Find places to audition. A passing overall grade can coexist with long sections that do not qualify. |
| Long recorded set | Inspect evidence over time and identify unexpected transitions in bandwidth. | A useful future workflow, contingent on bounded scan-time memory and long-track tests. It does not assess transitions or mixing skill. |
| Old collection or vinyl transfers | Organize the review by measured characteristics and explicit errors. | Vintage recordings and noise can affect the rule; context and listening remain necessary. |
| Collaborator or venue follow-up | Share a readable report with method, duration and measured coverage. | Describe a concern with evidence. A public/share export must remove personal folder paths. |

The analyzer preserves the complete input file. It does not edit Rekordbox/Serato collections, cues, grids, playlists or DJ notes. Library integration would require a separate supported workflow and is outside this release.

## Producer, engineer and sample-user workflows

| Situation | What the app helps the user do | Useful outcome and limit |
| --- | --- | --- |
| Final export sanity check | Inspect actual codec, native sample rate, channels, duration and spectrum against the intended delivery. | Notice an unexpected export or bandwidth change before sending it. Available metadata is shown; missing or unverified information stays explicit. |
| Successive bounces of the same material | Review measurements from each version. | Investigate an unexpected difference. Mix changes, gain, silence, duration and encoding can legitimately change results. |
| Incoming remix or collaboration files | Inspect technical characteristics before importing every file into a DAW. | Decide which files need clarification. The app does not prove ownership, provenance or stem authenticity. |
| Preview versus full-resolution delivery | Inspect each file separately and document its characteristics. | Confirm what was received; do not expect lossy and lossless exports to produce identical measurements. |
| Stems and isolated instruments | View technical metadata and spectrum with explicit context. | A bass stem, kick or vocal may correctly receive LQ while being suitable for production. Whole-song grades have limited value for these assets. |
| Loops and one-shots | Inspect available bandwidth and duration. | Very short clips need a limited-measurement explanation. A clip shorter than the FFT window is not comparable to a complete song. |
| Archive and reference-library review | Inventory different versions and preserve reports. | Record technical properties without changing sources. No automatic deletion or “best version” replacement. |

The benefit for producers is **technical inspection before opening every file in a DAW**. Loudness, true peak, clipping, dynamic range, phase compatibility and mastering approval require separately validated measurements; they are not implied by HQ.

## Other useful audiences

- Collectors can review suspicious labels and compare editions with evidence while preserving originals.
- Educators can demonstrate bandwidth, lossy/lossless containers and the effect of quiet sections using clearly identified synthetic examples.
- Small labels or collaborators can use reports to discuss received files. Reports are observations, not certification of a delivery contract or recording quality.
- Music listeners can inspect their local library without creating an account or uploading audio.

These are proposed product uses. Manufacturer format-support lists establish compatibility examples, not market-share or demand evidence. Validate demand with users before expanding beyond the core workflow.

## What keeps the app simple

The main path remains **select → analyze → inspect → export**.

1. Select a music folder through the native shell's ordinary picker or the browser fallback's path field. Inventory is asynchronous and cancellable, records skipped counts/warnings and declares incomplete limits. The alpha caps analysis at 50 selected tracks; file-level selection is within the inventory rather than a separate native file picker.
2. Analyze with visible progress, cancellation and retry. Inventory/hash reads and decoding remain local and read-only. Preserve all input bytes and qualify the final packaged shell, including shutdown behavior.
3. Show a compact results table: file/title, spectral grade, 20/15 kHz coverage and status. Open details for the timeline, spectrogram, qualifying seconds, full duration, codec, sample rate and channels. Show bit depth only when it is meaningful and actually known; a decoder's float output is not proof of a lossy file's original bit depth.
4. Save the current JSON evidence report using a native save dialog or browser download. It removes recorded machine-specific/cache paths and private diagnostics while retaining relative filenames. Human-readable HTML/CSV export remains proposed; JSON is not described as a polished readable report.

All/HQ/MQ/LQ/Error/Unmeasured filters and cumulative folder scores are implemented. The equally weighted score uses HQ100/MQ50/LQ0, excludes ungraded/unmeasured tracks, and marks partial results. See FOLDER_SUMMARY_AND_INTEGRITY.md for batch and integrity behavior. Context messages should explain a measurement, rather than instruct the user to replace a track automatically. Missing artist/genre tags must not stop audio analysis.

The canonical implementation now covers MP3, WAV, AIFF, FLAC, AAC and ALAC, subject to the [format qualification matrix](FORMAT_SUPPORT.md). Actual codecs/profiles are checked; a container extension alone is insufficient. Native rate/channel bounds and synthetic cases do not qualify every layout or final platform package.

## Edge cases that shape the product

The detailed [edge-case matrix](EDGE_CASES.md) records resolved implementation mechanisms, executed evidence and remaining qualification, including open disk-cache retention. The most important interpretation cases are:

| Case | Product behavior |
| --- | --- |
| Intentional filtering, lo-fi, vintage audio or a bass/vocal stem | Preserve the measured grade and explain that limited high-frequency content may be intentional. |
| Hiss, distortion or artificial high-frequency energy qualifies HQ | Show coverage evidence. Make no authenticity or perceived-quality claim. |
| Only 40% of a mixed-source edit qualifies | The overall grade follows the existing rule; the timeline exposes the other sections. HQ does not promise uniform coverage. |
| Silence, fades or a long quiet introduction | Include the entire decoded duration, as required. Show qualifying seconds and the denominator. |
| A very quiet export | Explain that the canonical absolute activity/signal thresholds can affect coverage. Do not secretly normalize or redefine the measurement. |
| A low native sample rate | Explain the frequency ceiling beside the grade. For example, 32 kHz audio cannot represent the 18/20 kHz target bands. Do not upsample to manufacture eligibility. |
| A result immediately below 40% | Grade using unrounded values and show sufficient precision or “just below 40%,” so the display does not contradict the grade. |
| Empty audio, unsupported encoding, corruption or interrupted decoding | Return an explicit failure/unsupported/incomplete status with no credible completed grade. Decoder recovery needs documented qualification. |
| A source changes, disappears or is replaced during the run | Discard stale results, preserve the source and offer a rescan. |

Lossless compression preserves the PCM supplied to its encoder; it does not establish the source's earlier history. Consequently, a limited-band source stored in FLAC can remain limited-band. [Official FLAC features](https://www.xiph.org/flac/features.html).

The sample-rate limitation follows the Nyquist frequency, half the sample rate. The exact canonical target bands are around the stated frequencies; tests must cover fully and partially representable bands without adding a new grading rule. [Audacity digital-audio fundamentals](https://manual.audacityteam.org/man/digital_audio.html).

## Release priorities

### P0: trust and correctness

- Preserve the one canonical engine and existing HQ/MQ/LQ regressions while adding full-track decoding for each advertised format.
- Clearly distinguish measured coverage, existing labels, failures and incomplete work. Keep the whole-duration denominator and unrounded boundary decisions.
- Preserve originals, metadata and artwork on success, failure, cancellation and app shutdown. Maintain source-identity and complete-file hash checks.
- Make read-only analysis independent of manager-only genre/language tags and portable renaming restrictions. Accept valid native paths while enforcing source containment and tested link behavior.
- Detect codec/sample-rate/channel changes within a stream, unsupported variants and insufficient evidence. Preserve accurate evidence timing, including short tails.
- Bound work and resource use before a long scan can exhaust memory or disk. A displayed-spectrum cap alone is insufficient.
- Provide a sanitized share export and honest scope statements for every advertised platform and format.

### P1: an easy daily workflow

- Native file/folder selection, useful discovery progress, complete skipped/error counts and batch filters.
- Clear cancel/retry/close/sleep behavior, slow-drive handling and actionable decoder/permission/disk-full errors.
- Readable report export, clear cache size/location and an explicit cache-cleanup policy that never targets music.
- Legible evidence at ordinary laptop sizes, keyboard operation, text labels alongside colors, and preserved results after non-destructive navigation.

### P2: expand only after user evidence

- Dedicated two-file comparison, aligned evidence and optional timestamp auditioning.
- Saved analysis reuse with trustworthy input/engine/method identity and complete invalidation rules.
- Separately validated loudness/clipping measurements if producers show a clear need.
- Additional Vorbis/Opus variants and other platforms, each with independent qualification.

Keep genre organization, renaming/retagging, DAW plugins, automatic repair/mastering, streaming-service access, universal player certification and authenticity accusations outside v1. They expand the product or require evidence the current method does not provide.

## Evidence required before launch

Technical checks: every advertised codec/profile and native platform; equivalent lossless PCM; lossy independently decoded PCM; threshold boundaries; silence/quiet/short/native-rate/channel fixtures; malformed/truncated/changing-format streams; mixed folders; valid Unicode/native filenames; removable/slow storage; very long files; cancellation/shutdown; disk/memory budgets; report privacy; and complete source preservation. See [release gates](RELEASE_GATES.md) and [edge cases](EDGE_CASES.md).

Product checks: observe DJs completing a crate review and producers completing an export check without coaching. They should understand what triggered a review, find the relevant evidence, export a usable report and correctly explain why HQ is not a sound-quality certificate. Record completion, confusion, waiting time and actionable follow-up rather than treating the count of LQ files as a success metric.

Post-release demonstrations can show a real batch review, an existing HQ label being rechecked, or two versions' evidence. Use verified behavior and clearly identified demo assets. App downloads and relevant brand leads are separate marketing outcomes.

## A suitable public description

“Review your music files locally. See full-track spectral coverage, inspect the evidence, and export a report before a gig or delivery.”

This documentation update records current implementation and the remaining roadmap. It does not change song files, tags or grading rules. The lightweight UI uses native anchor scrolling, restrained section reveals, visible keyboard focus and reduced-motion support; those choices keep the main workflow clear without a heavy animation dependency.
