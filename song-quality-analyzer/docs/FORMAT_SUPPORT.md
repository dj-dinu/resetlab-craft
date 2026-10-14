# Audio format support and qualification

Updated October 11, 2026. The current local alpha has multi-format decoding in the **one canonical full-spectrum scanner**. The table distinguishes implemented codec scope from public platform qualification.

## Current local scope

| Format | Candidate extensions | Canonical decoder and limits | Qualification |
| --- | --- | --- | --- |
| MP3 | `.mp3` | Reviewed libmpg123 path; actual MPEG metadata is reported. Midstream native-format changes are rejected without a partial grade. | Real HQ/MQ/LQ regressions match exactly on Windows. Packaged/clean-machine and native macOS checks remain pending. |
| WAV | `.wav`, `.wave` | PyAV; actual PCM codecs in WAV, including tested integer and float variants. The extension does not authorize every compressed WAV encoding. | Synthetic Windows PCM fixture coverage passed; final package/platform matrix pending. |
| AIFF | `.aif`, `.aiff` | PyAV; actual PCM codecs in AIFF. Unsupported compressed variants are rejected. | Synthetic Windows PCM fixture coverage passed; native macOS/package matrix pending. |
| FLAC | `.flac` | PyAV; actual FLAC in a FLAC container. Native samples/rate are retained for analysis. | Equivalent lossless PCM fixture coverage passed; package/platform matrix pending. |
| AAC | `.aac`, `.m4a`, audio-only `.mp4` | PyAV; actual AAC in ADTS AAC or MP4/M4A. Exactly one audio stream; ordinary video is rejected. Attached cover-art streams may be accepted. | Synthetic AAC/container and independently decoded-PCM checks passed; all profiles and target packages are not blanket-qualified. |
| ALAC / Apple Lossless | `.m4a`, audio-only `.mp4` | PyAV; actual ALAC in MP4/M4A, identified separately from AAC. | Equivalent lossless PCM fixture coverage passed; package/platform matrix pending. |

PyAV is pinned to **19.0.0**, whose installed package metadata requires **Python >=3.12**. The source app reports configured/available decoders. Missing decoders, unsupported codecs, encrypted files, multiple audio streams or ordinary video-bearing files must produce an explicit failure rather than a credible grade.

Ogg Vorbis, Opus, DRM-protected files, streaming-service caches and codecs outside the implemented scope are not advertised support. Candidate extension matching is inventory discovery; the canonical decoder verifies the actual stream.

The target format set is useful in DJ workflows, but successful analysis is not a playback-compatibility promise for every device. Manufacturer/software examples include [Serato's supported file types](https://support.serato.com/hc/en-us/articles/204177974-Serato-DJ-Pro-Supported-File-Types) and the [CDJ-3000 launch specifications](https://www.pioneerdj.com/en/news/2020/cdj-3000-professional-dj-multi-player/). Consult the current manual for the exact player, firmware and software mode.

## One rule across formats

Decoders supply native-rate PCM to the reviewed spectral measurement. They do not grade audio independently. HQ requires qualifying measurable signal at or above 20 kHz for at least 40% of the full decoded duration; otherwise MQ requires at least 40% at or above 18 kHz; otherwise LQ. All existing signal/activity thresholds, duration weighting and channel-power rules remain.

Bitrate, container, codec, sample rate, bit depth and a lossless label are informational. FLAC/ALAC can preserve a previously band-limited or lossy source. Spectral coverage does not establish original bitrate, source authenticity, mastering quality or audible superiority.

Do not upsample to manufacture coverage. Low native rates retain their canonical grade with frequency-ceiling context. Decoded float output is not a lossy source's original bit depth; a bit-depth field is reported only when meaningful source PCM/lossless information is available. Sources are never transcoded, overwritten or retagged.

## Evidence and implementation bounds

The canonical update passed 58 synthetic edge/format cases, its self-test, and exact real MP3 HQ/MQ/LQ metrics/time-bin/power regressions. The fixtures include equivalent 16/24-bit lossless wrappers, AAC compared with its independently decoded PCM, float PCM, silence/short/quiet cases, near-40% boundaries, native-rate/channel cases, inverse-phase stereo, changing-format rejection, evidence budgets and tail timing. See [local test results](LOCAL_TEST_RESULTS.md); fixture coverage is distinct from Python unit counts and installed-platform qualification.

Implementation bounds are 8–192 kHz, at most eight channels, 24 hours/172,800 bins per track and 250,000 report time bins per canonical batch. Accepting a bound does not mean every codec/profile/layout has been tested. The default 32 MiB retained spectrum budget can omit the graph while the full grade continues. Resource-limit failures never become partial HQ/MQ/LQ results.

## Qualification required per advertised format

- Preserve the canonical self-test and exact real MP3 regressions whenever decoding changes.
- Verify equivalent lossless PCM, and compare lossy formats with their independently decoded PCM using documented delay/padding behavior.
- Cover supported profiles, channels, native rates, silence/quiet/short inputs, corruption/truncation, encryption, misleading extensions and midstream changes.
- Verify mixed-format inventory, Unicode/native paths, slow/disconnected storage, cancellation, app close, very long files and disk/memory limits.
- Verify source SHA-256 on success, failure and cancellation, including tags/artwork; inspect codec metadata, evidence timing and sanitized exports.
- Execute the final installed app natively on each claimed Windows/macOS architecture, record decoder versions, and satisfy each binary's redistribution/license requirements.

A public format/platform claim requires these package-level checks. The current developer-machine alpha and private bundle do not replace them.
