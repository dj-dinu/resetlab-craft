# Local multi-format analysis

Current rule: HQ requires >=40% at or above 20 kHz; MQ otherwise >=40% at or above 15 kHz; LQ otherwise. The earlier 30% / +/-200 Hz results below are historical; reanalyze old reports under the new rule.

The applied local patch extends the same canonical scanner. It never implements
another grader, modifies source music, or assigns quality based on bitrate or
lossless encoding. Its spectral-power and metric functions, 30% HQ/MQ
boundaries, absolute/relative signal thresholds, and quiet-section denominator
remain unchanged.

MP3 continues through libmpg123. WAV/WAVE, AIFF/AIF, FLAC, ADTS AAC, and
AAC/ALAC in M4A or audio-only MP4 use PyAV 19.0.0 binary wheels. PyAV's official
distribution supplies its FFmpeg libraries for Windows and macOS. The tested
Python runtime is 3.12.14; PyAV 19 requires Python 3.12 or newer.

- [PyAV installation](https://pyav.basswood.io/docs/stable/overview/installation.html)
- [Audio frames and sample formats](https://pyav.basswood.io/docs/stable/api/audio.html)
- [Container streams and decoding](https://pyav.basswood.io/docs/stable/api/container.html)

The new decoder reads the actual codec/profile/container, iterates decoded
frames, and converts their sample representation without changing native
sample rate or channel layout. It averages power across channels using the
existing canonical calculation, so inverse-phase stereo is not canceled by
a mono downmix. AAC labels are calculated from decoded native PCM, including
the decoded duration actually available to the reader.

Actual codec metadata distinguishes AAC from ALAC inside M4A. The MP3 path
examines validated initial MPEG frame headers, distinguishing MPEG layers 1,
2, and 3; first-frame bitrate is explicitly informational and is not presented
as a VBR track's average bitrate. Bit depth is included only when the native
decoder establishes it for PCM or a lossless codec; decoded AAC representation
does not establish original source bit depth. Encoded bitrate comes only from
the audio codec context when known, excludes container/artwork overhead, and
never promotes or demotes a grade.

Video-bearing files, multiple audio streams, unsupported actual codecs,
DRM/encrypted content, and changes to native sample rate/channel/sample-format
fail explicitly. Attached cover artwork is allowed and never decoded as audio.
The implementation bounds are 8–192 kHz and up to eight channels. Synthetic
fixtures cover selected rates/layouts; these bounds do not qualify every
codec/profile/channel combination or installed platform. A decoder error
produces no partial grade.

Decoded duration is bounded at 24 hours and 172,800 half-second bins. Spectrum
retention defaults to a 32 MiB evidence budget, including an allowance for the
final contiguous matrix copy and row bookkeeping. Before keeping a power row,
the scanner checks this budget. If it runs out, the scanner discards spectrum
evidence, explains the unavailable preview, and continues measuring the entire
track. A memory-limited preview never changes a full-duration label. The
optional CLI budget is 0–256 MiB. Grade reports and time bins remain bounded
by the explicit duration/bin limits. The CLI additionally permits at most
250,000 retained time bins across one batch. If a track would exceed that
aggregate budget, that track and all remaining inputs receive explicit
`analysis_limit` records without grades and a request to scan smaller batches.
Every selected input still has a report record.

Each spectrum row has an explicit start and duration in the NPZ file. A tail
shorter than 2,048 samples remains in the full-track denominator but has no
spectral row; the UI must not stretch prior evidence to cover that tail. Context
also explains short tracks, silence/quiet sections, and a native frequency
ceiling below 20 kHz. Non-finite PCM or power fails instead of silently appearing
as an LQ result.

At unusual rates such as 39,900 Hz, some of the 19.8–20.2 kHz band exists below
the native Nyquist ceiling. The unchanged canonical metric also requires the
20 kHz target itself not to exceed that ceiling. The 39,900 Hz fixture therefore
has zero qualifying 20 kHz coverage and receives MQ from its measurable 15 kHz
signal; context describes the native limit without claiming a general fidelity
conclusion.

Public portability removes personal collection defaults. Legacy sampled scans
require `SONG_AUDIT_LEGACY_ROOT`; the old optional test uses
`SONG_AUDIT_TEST_MP3`. Node/addon and libmpg123 resolve from documented settings,
OS lookup, or permitted bundled files, without installed DJ software fallbacks.
The full-spectrum CLI still requires explicit input paths.

The local migration helper verifies the canonical SHA, checks the unchanged
math functions via AST, tests a candidate entirely in memory, and only applies
through its reviewed `--apply` mode with verified original-source/notes backups.
Synthetic fixtures live in the project's ignored `.work` folder. Their tests
cover all three spectral labels across four lossless encodings, AAC against
its decoded-PCM reference, threshold bursts, low/native sample rates, silence,
quiet/short tails, mono and inverse-phase stereo, evidence limits, invalid
files, video/attached cover art, non-finite PCM, and native format changes.

Real HQ/MQ/LQ MP3 regressions require exact equality for duration, both coverage
percentages, qualifying seconds, sample rate, every time bin, and retained
spectrum arrays, with source file hashes unchanged. These Windows results
do not substitute for native macOS installation and runtime tests. AAC LC is
covered by the synthetic encoding tests; other AAC profiles require additional
native fixtures before being described as separately validated.

The current local update passed 58 synthetic edge/format cases, the canonical self-test and exact real MP3 metrics/every-bin/power regressions with source hashes unchanged. These fixture cases are distinct from the app's Python unit count. See [local test results](LOCAL_TEST_RESULTS.md) for actual browser, native-shell, private Windows-bundle and remaining platform qualification.
