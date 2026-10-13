# Local qualification record

Private source preview: a source-only checkout without private settings ran
76 application tests (75 passed, one POSIX case skipped on Windows). Its
generated canonical source passed SHA-256 verification and `--self-test`.
With the documented platform decoder configured, two owned synthetic MP3s
analyzed successfully and their hashes stayed unchanged. An initially deep
staging path exceeded Windows cache-file path limits; a short checkout passed.
Use a short checkout as documented in installation; comprehensive long-path
and native platform qualification remains pending.

October 12, 2026: **Spectracraft by ResetLab Craft is a local Windows alpha. A public release is not yet qualified.** These are executed checks, not a claim that all files, machines or platforms are safe. Private test payloads, paths and music stay out of public source packages.

## Current checks

| Check | Executed result | Scope |
| --- | --- | --- |
| Application Python suite | 76 run / 75 passed / 1 skipped on Windows | Backend, inventory, adapter, authenticated API, preferences, report redaction and mocked native bridge. The POSIX-native filename case is skipped on Windows. Mocked dialogs do not qualify actual OS dialogs. |
| Canonical edge/format fixtures | 58 passed after decoder hardening | Lossless wrappers, independently decoded AAC PCM, silence/quiet/short tails, coverage boundaries, rates/channels, inverse-phase stereo, changing-format rejection and evidence/report limits. |
| Canonical integrity fixtures | 16 passed | Structural duration declarations, misleading metadata, damaged MP4 and unverifiable raw-stream expected length. |
| Explicit canonical CLI self-test | Passed | Known cutoffs, silence and the original 30% coverage rule. |
| Current versus historical real HQ/MQ/LQ | Passed | Every returned result field, time bin and retained power value is exact; whole-file input hashes are unchanged. The historical backup is a comparison reference, not a maintained scanner. |
| Current adapter integration/demo | Passed | Real references match, spectrum evidence is available, an existing HQ label is reanalyzed, and sources remain unchanged. |
| Internal decoder network probe | Direct URL: 1 loopback request before restriction; 0 after. Disguised playlist: 0 before and after. | Owned synthetic fixture and test server only. The app's selected ordinary-file boundary already excluded URL inputs. This hardens the decoder itself. |
| New security regressions | Passed in the 76-test suite | Non-ASCII invalid token fails closed; private read routes need authentication; foreign/null origins are denied; response policies restrict exposure; static failures omit private installation paths. |
| New branded Windows worker | Passed: self-test, six codecs and three real references | Nine input records match canonical metrics, bins, powers, codec metadata and source hashes in an isolated Python environment. No missing canonical imports. Actual GUI was not opened. |
| Packaged duration example | Passed | A 240-second header with 60 seconds of audio remains ungraded; a valid 60-second edit is HQ. |
| Browser adversarial metadata/paths | Five synthetic inputs: 3 HQ / 1 LQ / 1 expected ungraded error; score 75 across four measured tracks | HTML-like title rendered literally with no injected image/script/iframe. Unicode, a 100-character filename and duplicate basenames in separate folders work. All five source hashes unchanged. This does not qualify Windows paths beyond native OS limits. |
| Grade filter with new controls | Passed | Error filter shows 1 of 5 while preserving score 75 and all five selections. Grade filters remain available. |
| Sun/moon and Smooth preset | Passed in browser | Keyboard Enter toggles appearance; dark mode persists across reload; Smooth is restored; removed preference dropdowns are absent. Focused scrolling checks cover reduced motion and native gesture/keyboard/nested-overflow handling. Physical devices remain unqualified. |
| Responsive/source-to-package checks | Passed | 1280×840 and 489×840 browser views have no document horizontal overflow. Current packaged static assets match source byte-for-byte; the R signal native icon is generated from the shared SVG. |

Current canonical source SHA-256: `7408713ec47389f52f221940c7feeb523f302cd5114186958f36b84ab77fd3cf`. The decoder change adds file-protocol and supported-demuxer allowlists only; spectral rules and duration grading remain unchanged. Build snapshots are mechanically generated and hash-verified.

Current private Windows bundle: `dist/Spectracraft/Spectracraft.exe`; **221,029,784 bytes for the complete folder bundle**, including `_internal`. The rebuilt worker passes the nine-input regression, self-test and duration cases. All packaged static assets match source. A successful frozen worker does not qualify the native window or installation.

## Folder/file, cache and extended runtime update

- A single-file input reads exactly one ordinary file and retains separate authorization from its parent/siblings. HQ WAV, MQ AIFF and LQ FLAC single-file integrations pass with unchanged hashes and sanitized exports. A file in the home root is allowed without permitting a recursive home-folder inventory.
- Browser single-file analysis gives one HQ result and a file score of 100. An inaccessible new path preserves the previous completed result/report and disables analysis of the mismatched path. Switching back to a folder returns five fixtures with 3 HQ / 1 LQ / 1 expected error and score 75; source hashes match.
- New owned cache retention keeps three finished jobs. Six focused safety tests pass after the final cleanup refinement, including active/legacy/export/music preservation, tampered/hard-linked markers and a music file arriving during cleanup. Active/legacy/unrecognized data are protected rather than automatically purged; no total disk-byte cap is claimed.
- An actual 10,001-candidate inventory retains 10,000 with an explicit partial warning (15.812 seconds on this host). A 20-minute, 32 kHz mono silent file completes LQ analysis in 1.657 seconds with all 1,200 decoded/silent seconds represented; its graph exceeds the 32 MiB budget and is omitted while full grading continues.
- Closing the backend session during a real canonical worker cancels the job, stops the server and reaps the child in 0.344 seconds, with its source unchanged. This is backend shutdown evidence, not an actual OS window-close test.
- The installed runtime/build traversal finds 19 Python packages and no missing required dependencies. The executed OSV query has no matching Python advisories; native-library security and distribution obligations remain open. See [dependency review](DEPENDENCY_REVIEW.md).

These host timings are observations, not performance promises for other machines. The [native beta guide](BETA_TEST_GUIDE.md) records the remaining clean-install, dialog, storage and device checks.

## Earlier evidence retained

- The 42-input adapter fixture batch produced 36 valid analyses and six expected ungraded failures. This is separate from the 58 canonical fixtures and 76 application tests.
- The mixed-format browser batch completed nine inputs: 3 HQ / 2 MQ / 3 LQ / 1 expected error. Export parsed correctly and all source hashes matched; tested absolute/cache/private-username data was absent.
- One hundred generated tracks completed in two batches: 36 HQ / 30 MQ / 34 LQ, folder score 51. First batch was explicitly partial at 50/100. All grade/error/unmeasured filter counts matched; cancellation preserved the completed summary/latest report, and rescan reset it. An all-HQ folder scored 100.
- Thirty representative text contrast pairs met 4.5:1; coverage bars met 3:1; spectrum stops increase in luminance and match the legend. This is not a full accessibility audit.
- Earlier browser cancellation/retry and JSON source-preservation checks passed. They do not qualify native shutdown, removable storage or a clean machine.

## Platform and release gaps

| Platform/check | Actual status |
| --- | --- |
| Native Windows window, choose/save dialogs, cancel and close during work | Not manually qualified. |
| Clean Windows machine without developer Python/DJ software | Not tested. |
| Native macOS Intel / Apple Silicon package | Neither built nor tested natively. Qualify each architecture advertised. |
| Linux | Deferred and untested. |
| Offline/outbound capture for actual native runtimes | Pending. App source has no telemetry/upload service; finite decoder probes do not certify every OS component. |
| Multi-hour/large-library peak resources; slow, removable, cloud or restricted storage; disk full | Broad qualification pending. |
| Private disk-cache ownership, retention and safe cleanup | New marked caches retain three finished jobs. Six safety tests pass, including arriving audio, hard-linked/tampered markers, active jobs, exports and legacy data. Abandoned/legacy/unrecognized data and total disk pressure still need review. |
| Project/dependency licensing, source package, security version review, signing and final content scrub | GPLv3-only selected for project-owned source; ownership/dependency/source/signing review remains pending. |
| DJ/producer beta without coaching | Pending. |

## Bounds and interpretation

Analysis is read-only, limited to 50 selected tracks. Inventory caps are 10,000 audio candidates / 100,000 visited entries with explicit incomplete warnings. Three completed jobs and three inventories are retained in memory. Canonical limits are 24 hours / 172,800 bins per track, 250,000 report bins per batch, 8–192 kHz and up to eight channels; these are limits, not qualification of every variant.

The default retained-spectrum budget is 32 MiB. Exceeding only the evidence budget omits the graph with a reason while complete grading continues. Processing failures receive no partial grade. Folder score is HQ 100 / MQ 50 / LQ 0 averaged across measured tracks, with excluded counts visible. A raw stream ending cleanly cannot reveal an unknown intended original length.

Music, tags, artwork and DJ collections remain unchanged. Public/native reports omit recorded machine/cache paths and free-form local diagnostics but retain relative filenames and metadata; they are sanitized, not anonymous. See [Privacy](PRIVACY.md), [Security](SECURITY.md), [launch checklist](LAUNCH_CHECKLIST.md) and [release gates](RELEASE_GATES.md).

GPLv3-only source licensing and reuse/branding policy applied locally; license text is bundled and served only through the fixed license route. The title/artist/filename list uses bounded ellipsis, preserving full DOM text and hover attributes. A 150-character Unicode title clips to 260px while retaining full text and original source hash; no document horizontal overflow. This is a display change only.
