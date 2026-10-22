# Analyzer use cases and edge cases

Updated October 14, 2026. This checklist distinguishes implemented behavior,
executed evidence and pending platform qualification. MP3, WAV, AIFF, FLAC, AAC
and ALAC use the one canonical scanner. Analysis is read-only and automatically
continues in alphabetical batches of 50; 50 is not a selection limit. The manager
is on hold. See [platform status](platforms/README.md) and the
[current review](platforms/macos/RELEASE_REVIEW.md); dated results below retain
their original test counts.

## Fixed grading and interpretation rules

HQ requires qualifying measurable signal at or above 20 kHz for at least 40% of the complete decoded duration, including quiet sections. Otherwise MQ requires at least 40% at or above 15 kHz; otherwise LQ. The canonical signal/activity thresholds, half-second bins, duration weighting and mean channel-power policy remain unchanged.

Bitrate, codec/container, extension, sample rate, bit depth and lossless compression do not determine the grade. A successfully decoded silent, very short or intentionally band-limited source can receive LQ. A decode/resource failure has no completed grade. Noise can qualify high-frequency coverage without demonstrating good sound.

These results do not establish authenticity, original bitrate, mastering quality, player compatibility or audible superiority. Context and listening remain necessary.

## Useful workflows

| Situation | Benefit | Boundary |
| --- | --- | --- |
| DJ reviews newly acquired tracks or an existing HQ label | Inspect unexpected bandwidth and compare the filename claim with a fresh measurement. | A finding is a review prompt, not automatic rejection or retagging. |
| DJ prepares a set folder | Analyze privately and keep a findings report. | Decoding here does not certify a particular player/firmware. |
| Producer inspects an export or collaborator delivery | View actual codec/rate/channels, duration and spectrum before opening every file in a DAW. | No loudness, true-peak, clipping, dynamics or mastering approval is implied. |
| Producer reviews a stem, one-shot or filtered loop | Document available bandwidth with duration/context. | Whole-song spectral grades have limited meaning for narrow-band or very short assets. |
| Collector compares edits, editions or vintage transfers | Inspect each file's evidence while preserving originals. | Highest cutoff need not mean the preferred master; noise and quiet sections matter. |
| Collaborator shares findings | Save measured results with machine-specific paths removed. | Relative filenames remain; a report is not anonymous or an authenticity certificate. |

## Current evidence

The alpha.3 canonical update passed 58 synthetic edge/format cases, 16 integrity cases and its explicit self-test. Four real MP3s were rescanned with unchanged source hashes. The rebuilt worker matches canonical metrics, time bins and retained spectra across six codecs and real HQ/MQ/LQ references. The app Python suite ran 80 tests: 79 passed and one POSIX-native filename test skipped on Windows. Mocked native bridge tests do not qualify actual dialogs. The earlier adapter analyzed 36 of 42 fixture inputs; six expected failures remained ungraded. Fixture and unit counts are different.

Earlier browser cancellation/retry, mixed-format and metadata/path evidence remains useful, but its recorded grades were measured under the old rule. Alpha.3 browser/native-shell, native macOS and clean-machine package qualification remain pending in [local test results](LOCAL_TEST_RESULTS.md).

## The eight previously observed gaps

“Resolved in implementation” means the cited code addresses the original mechanism. It does not declare every related native-platform/stress case qualified.

| Earlier finding | Current code/evidence | Status and remaining qualification |
| --- | --- | --- |
| 1. Manager naming/tag rules affected read-only analysis | `inventory.py:safe_path()` uses native path semantics; `inspect_metadata()` and `scan_library()` do not require genre/vocal tags. The adapter imports analyzer-only inventory safeguards. Hard-linked ordinary files remain read-only with hash guards. | Original coupling resolved in implementation. Native POSIX/macOS Unicode, case-volume and literal-backslash/colon filename execution remains pending; the Windows suite skips its POSIX-only case. |
| 2. Very short clips had no explanatory context | Canonical `_FullSpectrumAccumulator.finish()` records very-short, sub-FFT tail, silence/quiet and frequency-ceiling context while preserving the grade. Expanded evidence renders unique canonical context and unavailable-spectrum reasons safely. Short/context fixtures passed. | Engine/UI context implemented. Actual native accessibility and user interpretation checks still need review. |
| 3. Preview limits did not bound retained spectra during scanning | Canonical `_FullSpectrumAccumulator.add()` budgets retained arrays before allocation/copy, clears evidence when the budget is exceeded and continues full grading. Per-track and aggregate report-bin caps also apply. The zero-evidence-budget and report-limit cases passed. | Original retained-spectrum allocation gap addressed. Multi-hour peak memory, decoder-frame/native-package and disk-stress qualification remains pending. |
| 4. Inventory lacked progress, cancellation, bounds and access warnings | `inventory.py:scan_library()` has cancellable traversal/hash reads, `os.walk(onerror=...)`, skipped counts, bounded warnings and 10,000-candidate/100,000-entry caps. `server.py` runs inventory as a cancellable scan job. | Implemented; current unit coverage passes. Full refreshed browser/native cancellation and slow/removable/cloud storage qualification remains pending. |
| 5. Public exports retained absolute/cache paths | `server.py:sanitize_report()` uses allowed fields, removes recorded absolute/cache locations and substitutes generic failure text. Native saves use this same public export. Relative filenames remain. | Original export mechanism corrected and covered locally. Final downloaded/native-saved artifact review and metadata/privacy adversarial cases remain release gates. |
| 6. Disk cache and inventories grew across runs | `State` now retains at most three inventories and three completed in-memory jobs. New owned caches keep three finished jobs; active, legacy/unmarked and unexpected data remain preserved. | **New cache retention implemented and tested; broad disk-pressure qualification remains open.** Ownership/schema guards exclude music and exports; active, legacy and unexpected data remain preserved. |
| 7. MPEG format changes were not inspected | Canonical `_analyze_mpg123_full()` re-reads new-format events and rejects native rate/channel/encoding changes. `_analyze_pyav_full()` rejects changed native rate/channel/layout/sample format. Actual changing-rate MP3/AAC fixtures passed. | Original mechanism addressed without a partial grade. Broader pathological streams, profile changes and installed decoders still need qualification. |
| 8. Spectrum display stretched evidence over an omitted tail | Canonical evidence records per-power-row starts/durations. `spectrogram_data()` validates timing; the UI positions columns against full duration and leaves missing tail blank. CLI/NPZ tail-alignment fixtures passed. | Original timing mechanism corrected. Final browser/native plot assertions and relevant short-tail user examples remain qualification work. |

## P0: correctness, preservation and privacy

| Case | Expected behavior | Current state / next evidence |
| --- | --- | --- |
| File changes, disappears or disconnects during reading/analysis | Reject stale input, discard unverifiable results and offer a rescan. Preserve all source bytes. | Hash/identity guards and local regressions pass. Add removable-drive, final-shell and package cases. |
| Audio, tags, artwork, cues, grids, playlists and DJ notes | No source or DJ collection modification. | Read-only routes and whole-file preservation checks exist. Repeat through final installed packages. |
| Corrupt, empty, unsupported, encrypted or undecodable input | Explicit ungraded failure; other valid files keep their own results. | Implemented codec/error behavior and synthetic cases pass. Full damaged/truncated/profile matrix pending. |
| Existing HQ/MQ/LQ differs from measurement | Recheck selected audio; distinguish existing label from measured result. | Synthetic existing-HQ demo and real MP3 references pass. |
| Just below, exactly at, just above 40% | Grade with original unrounded values; display precision/context without rounding up a contradictory claim. | Canonical boundary fixtures pass; UI uses extra precision or “<40%.” End-to-end boundary presentation checks remain useful. |
| Native rate cannot represent a target | Keep the rule, explain the frequency ceiling, never upsample. | Native-rate/context logic and synthetic cases pass; complete codec/rate matrix pending. |
| Target band meets Nyquist | Evaluate the canonical available-band policy without redefining it. | Code uses available bins around the target; target-center and partial-band variants need explicit coverage in the release matrix. |
| Channel layouts and rates differ | Preserve mean channel power; reject unsupported changes rather than silently resample/downmix. | Mono/stereo/inverse-phase fixture evidence exists. At most eight channels is a bound, not qualification of every layout. |
| Container extension hides a different codec | Inventory candidates, then verify actual stream/codec. | AAC versus ALAC and PCM/lossless handling implemented. Unsupported variants remain ungraded. |
| Decoder tolerates truncation | Do not equate some decoded audio with verified complete delivery. | Structural declared-versus-decoded duration checks pass; material differences remain ungraded. Cleanly ending raw streams without a reliable declaration remain unverifiable. Broader warnings/recovery cases need qualification. |
| Intentional low-pass, vintage audio, noise or ultrasonic content | Show evidence and context; avoid authenticity/perceptual claims. | LQ/rate context is present; additional user interpretation examples pending. |
| Shared report | Remove recorded machine/cache paths while keeping useful relative references. | Sanitizer and native save path implemented; review final artifacts and don't promise anonymity. |

## P1: usability and scale

| Case | Expected behavior | Current state / next evidence |
| --- | --- | --- |
| Silence, quiet or very short input | Canonical grade with limited-evidence context. | Engine context, fixtures and expanded UI context implemented; user comprehension/native accessibility needs review. |
| Long quiet intro/outro or final partial window | Include full duration; show qualifying seconds and real evidence timing. | Weighted rules and tail timing fixtures pass. Extended real-file examples pending. |
| Large recursive folder | Progress/cancel, explicit incomplete limits and skipped reasons. | Async bounded inventory implemented. Native UI, slow-drive and larger-memory observations pending. |
| Permissions, links, AppleDouble and audit folders | Preserve sources; show skipped/error counts/reasons. | Inventory returns counts/warnings and excludes links/sidecars/`_Organization`. Target-platform permission cases remain pending. |
| Long mix / oversized evidence | Bound retained evidence and report work; explain unavailable graph; no partial grade for processing limits. | Canonical limits implemented; multi-hour peak-resource qualification remains pending. |
| Repeated jobs / cache pressure | Bound memory and define safe disk retention. | Three jobs/inventories and three finished owned caches retained; active/legacy/unrecognized caches remain protected. Total disk pressure and explicit size reporting still need qualification. |
| Cancel, retry, close, sleep/resume | Settle job state, restore controls and reap decoding work. | Browser basics previously passed; async scan/actual shell/shutdown/sleep package checks remain pending. |
| Missing tags, oversized artwork, HTML-like text | Continue actual audio analysis when metadata is unavailable; safe text rendering; preserve metadata. | Metadata preview has limits/fallback. Browser HTML-like title renders literally with no injected elements; Unicode, a 100-character filename and duplicate basenames pass with hashes unchanged. Broader damaged/large metadata and native long-path cases remain pending. |
| USB/NAS/cloud placeholder/locked file | Explain I/O failures without implying unavailable bytes were verified. | Source guards and progress implemented; platform storage matrix pending. |
| Missing engine/decoder, disk full or invalid cache | Actionable error, no false complete report, sources untouched. | Partial local coverage; installed-package/disk-error matrix pending. |
| Duplicate content / equal names in different directories | Keep each native path distinct; no automatic merging or replacement. | Implemented read-only identity behavior. Dedicated comparison remains future work. |
| Reduced motion, keyboard and laptop-sized evidence | Native scrolling, visible focus, accessible labels, restrained motion and bounded plots. | Lightweight UI and refreshed browser fixture flow work; native accessibility/platform review pending. |

## Bounds to disclose

- Analysis selection: 50 tracks/run.
- Inventory: 10,000 candidate audio files / 100,000 visited entries; bounded warning list, explicit truncation and skipped counts.
- Canonical analysis: 8–192 kHz, at most eight channels, 24 hours / 172,800 bins per track, 250,000 report time bins per batch.
- Retained spectrum: 32 MiB default budget; evidence may be unavailable while complete grading continues. Processing/report-limit failures are ungraded.
- Adapter preview archive loading: 128 MiB uncompressed bound; incoming report file: 64 MiB bound; graph overview: at most 120×128 cells.
- In-memory retention: three completed jobs and three inventories. New owned caches retain three finished jobs; active/legacy/unrecognized caches may remain.

## Fixture and release matrix

Keep fixtures for coverage boundaries/duration-weighted tails; silence/absolute/relative thresholds; low/native/high rates and partially available bands; mono/stereo/asymmetric channels; quiet sections/noise/intentional filtering; corruption/truncation/misleading extensions; supported profiles; changing streams; equivalent lossless wrappers and independently decoded lossy PCM.

Any decoder or measurement change must preserve the canonical self-test, real HQ/MQ/LQ metrics and every bin/power regression. Installed Windows/macOS qualification is required for each advertised format/profile/architecture; source presence and a synthetic pass do not establish that qualification.

## Deferred additions

Comparison/aligned evidence, optional auditioning, search and readable CSV/HTML reports can follow verified user demand. Loudness/true peak/clipping/dynamics require separate specifications and validation. Library management, retagging, repair/mastering and streaming integrations remain outside analyzer v1.

See [format support](FORMAT_SUPPORT.md), [product brief](PRODUCT_BRIEF.md), [local test results](LOCAL_TEST_RESULTS.md) and [release gates](RELEASE_GATES.md).

## October12 update

The100-track two-batch folder score and all grade/error/unmeasured filters are verified. Cancellation retains the completed score/report. Duration-integrity checks now keep materially mismatched structural declarations and decoded audio ungraded. The240-second header/60-second decoded example fails safely; a valid60-second HQ edit passes. Canonical16 integrity checks and58 format checks pass. The private Windows worker matches six codecs and real references exactly, including evidence and source hashes. Actual native GUI, clean Windows and macOS remain pending. See FOLDER_SUMMARY_AND_INTEGRITY.md and LOCAL_TEST_RESULTS.md for details.
