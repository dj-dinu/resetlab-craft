# Local security review

Alpha.2 drop paths pass the same ordinary-file/folder boundary as picker paths. Only one source is accepted; URLs, links, unsupported files and busy-operation drops are refused. No file bytes are uploaded. The pinned pywebview 6.2.1 adapter uses native event dispatch and `run_js` to retain the existing CSP without `eval` or `unsafe-eval`. It relies on pywebview internals for path resolution; requalify it before upgrades. Actual OS gestures remain unqualified. The in-app demo endpoint/default path were removed.

Status updated October 14, 2026: Windows 0.1.0-alpha.5 is a public early beta
with disclosed gaps. The Mac candidate remains under qualification. The
underlying boundary review began October 12; it is evidence of specific
controls, not a guarantee that arbitrary hostile files or every platform are safe.

Native Mac testing found pywebview-generated wrappers incompatible with the
strict WKWebView CSP. The scoped adapter uses ordinary closures and native
completion results, permits only five public bridge methods and the document
drop event, and refuses private attribute traversal. Protocol checks execute
with dynamic code generation disabled. CSP and local-origin checks remain.
See [Mac testing](platforms/macos/TESTING.md).

The exact Mac candidate needs a bundled Python/OpenSSL/Expat security refresh;
the fresh 20-package OSV no-match result does not cover those native components.
No app exploit was demonstrated. See the [dependency review](DEPENDENCY_REVIEW.md)
and [Mac release plan](platforms/macos/RELEASE_PLAN.md).

## Boundaries checked

- Loopback-only listener; strict expected Host and Origin; no cross-origin API permission; random session token checked using constant-time byte comparison. Malformed non-ASCII tokens fail closed.
- Private read routes and mutation/job routes require authentication. Only explicit static assets are served; settings, traversal paths, music and cache files are not a file-serving route.
- CSP restricts scripts/images/connections/forms to the app, forbids frames/objects, and sets no-referrer, no-store and nosniff headers. Camera, microphone, geolocation and payment permissions are disabled through response policy where the engine supports it.
- Client metadata is rendered through textContent. Decoder execution uses an argument list, not a shell. NumPy evidence loading disables pickle and applies size/timing checks.
- Ordinary-file/path/symlink checks, source hashes, inventory selection validation, batch/resource bounds and cancellation protect the read-only workflow. No organizer modification routes are exposed.
- Explicit file selection inventories only that file and requires exactly its filename for analysis; it cannot authorize siblings or a parent-folder scan. New cache cleanup verifies ownership, containment and recognized generated files, excludes links/hard links/music/exports, and removes only an inspected file list rather than recursively deleting newly arriving content.
- Private GET resource failures use generic messages instead of leaking installation paths. HTTP connections have a 15-second timeout for incomplete reads.
- Public/native report output uses an allowlist and redaction. Private diagnostic records remain local; exports retain relative filenames and are not anonymous.
- The single canonical decoder now restricts PyAV/FFmpeg to file protocols and supported audio demuxers before parsing. The internal direct-URL test was blocked without changing spectral thresholds, full-duration math or source files.

Protocol controls follow the [FFmpeg protocol documentation](https://ffmpeg.org/ffmpeg-protocols.html) and [format context allowlists](https://www.ffmpeg.org/doxygen/8.1/structAVFormatContext.html). Platform renderer requirements are documented by [pywebview](https://pywebview.flowrl.com/guide/installation.html).

## Continued beta and Mac release qualification

Broaden actual native install/dialog/cancellation/shutdown checks; perform an
outbound-network capture on clean machines with local audio; audit native
versions/security fixes and corresponding source obligations; and profile
storage/resource edge cases. Report redaction and bounded cache safety have
specific automated coverage; do not generalize it to every machine. GPLv3-only
is selected for project-owned code. Scrub each final release asset and verify
its source correspondence, signature status and download hashes.

The executed Python dependency lookup returned no advisory matches across 19 installed packages. Native libraries remain a separate review; see [dependency review](DEPENDENCY_REVIEW.md). The 10,001-candidate inventory, 20-minute analysis and real-child backend shutdown checks pass. Six cache safety tests pass; active/legacy/unrecognized data are preserved and disk footprint is not capped by bytes. Use the [native beta guide](BETA_TEST_GUIDE.md) for the remaining manual qualification.

Media decoding uses native libraries. Keep them updated and do not claim every adversarial input is qualified from a finite fixture set. Linux has no qualified release yet.

For a suspected issue, preserve a minimal synthetic reproduction and contact the project owner privately before sharing tokens, private paths, music or full diagnostics. Configure a private vulnerability-reporting channel before public launch.
