# Canonical scanner integration

Historical migration record. Subsequent Windows real-track/independent-decoder validation passed; current multi-format and bundle status is recorded in [local test results](LOCAL_TEST_RESULTS.md). Pending statements below describe the initial patch stage, not the current complete qualification record. Native macOS and public-release qualification remain pending.

This records the initial MP3 portability patch. The later
[multi-format analysis patch](MULTIFORMAT_ANALYSIS.md) supersedes its local DJ
software fallback paths and its external-source packaging limitation: the
canonical worker can be included mechanically in the desktop build after the
reviewed public portability patch, while retaining one maintained source.

The local prototype invokes the established canonical `scan_quality.py`; it
does not reimplement spectrum grading or create another scanner. The canonical
source remains outside the prototype. `tools/patch_canonical_scanner.py` is a
one-time local migration helper bound to the exact reviewed source SHA256.
Its machine-specific path and real-track reports are local development data,
not material for a public repository.

## Necessary change

Before the portability patch, importing the scanner immediately loaded a DLL
from an installed Windows Rekordbox folder. Therefore even `--self-test` and
help could not run on a clean computer or a Mac. The legacy sampled decoder
also embedded Node and DJ.Studio paths. These are concrete portability defects.

The candidate makes libmpg123 initialization lazy and discovers a library
only when MP3 decoding is requested. Resolution is:

1. `SONG_AUDIT_MPG123_PATH` when explicitly set. A broken explicit path is an
   error, not a reason to silently use a different installed library.
2. Library files in `lib/` beside the canonical scanner, or beside the scanner.
3. `ctypes.util.find_library('mpg123')`, common macOS library locations, and OS
   library names.
4. The pre-existing local Rekordbox DLL as an optional Windows compatibility
   fallback. This fallback is not a public distribution source.

Use a libmpg123 build matching the OS and Python process architecture. For
example, an Apple Silicon build requires an arm64 library; an Intel Mac build
requires an x86_64 library. Missing-library errors tell the user which variable
to set. Full-spectrum mode does not require Node or DJ.Studio.

Legacy sampled mode accepts `SONG_AUDIT_NODE` and
`SONG_AUDIT_DECODER_ADDON`, retaining optional local fallbacks for established
use. It does not qualify for the user's full-duration HQ/MQ/LQ organization
workflow. The app must call `--full-spectrum` and leave `--skip-hq` off unless
the user explicitly selects skipping.

## Decoder ABI

mpg123's standard seek/length and reader callbacks use C `off_t`, whose width
depends on the build. The patch uses the existing `_64` wrapper family when
all four required symbols are present, binding offsets as `int64_t`. Otherwise
it retains the original Windows 32-bit ABI and the standard macOS 64-bit ABI.
The read callback remains `ssize_t`, and sample-rate parameters remain `long`.

These are documented by mpg123:

- [Header/ABI notes](https://www.mpg123.de/api/group__mpg123__h.shtml)
- [Reader callback API](https://www.mpg123.de/api/group__mpg123__lowio.shtml)
- [Seek API](https://www.mpg123.de/api/group__mpg123__seek.shtml)

## Validation

The helper's `--check` verifies the original file SHA and parses both source
versions. AST checks require the full-spectrum power, metrics, grade,
self-test, and CLI functions to remain identical. `--validate` executes the
candidate in memory and runs the canonical self-test without loading a native
decoder. It must keep `MPG` unset throughout that self-test.

For native regressions, pass repeated `--track` inputs with
`--compare-baseline`. This runs original and candidate canonical functions and
requires exact equality for sample rate, decoded duration, both coverage
percentages, qualifying seconds, and every time bin. It hashes each original
track before and after analysis. `--report` saves the validation results to an
existing local artifact directory.

`--apply` runs validation before modification, rechecks the source, writes and
verifies separate original scanner and notes backups, and atomically replaces
the scanner. No music files are renamed, retagged, moved, or deleted.

Windows real-track regression still needs a native decoder execution. On this
machine a restricted execution sandbox returned Windows error 623 while
loading the existing DLL, so that native regression must run through the
approved command path. A native macOS install/scan test remains a release gate;
this code review and Windows validation cannot demonstrate that Mac runtime.

All full-spectrum thresholds and HQ/MQ/LQ boundaries are unchanged: HQ requires
at least 30% of the full decoded duration near 20 kHz; MQ otherwise requires
at least 30% near 18 kHz; LQ otherwise. Encoded bitrate never determines a
grade. Quiet sections remain in the denominator.

## Before public distribution

Use properly sourced libmpg123 packages and review redistribution notices.
Do not copy native binaries from commercial DJ software. Confirm a Windows
and a macOS installation that succeeds with no DJ applications installed.
For the authorized private GitHub source preview, the project now includes a
byte-for-byte generated scanner asset and SHA-256 manifest in `canonical/`.
The original remains the sole maintained source. Regenerate the asset after
validation; never edit or develop a second classifier. No native decoder
binaries are included. Public binary distribution and native Mac qualification
remain pending.
