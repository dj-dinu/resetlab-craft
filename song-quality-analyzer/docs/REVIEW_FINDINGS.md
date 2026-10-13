# Analyzer implementation review

Historical snapshot review. The findings below motivated subsequent safety and UI changes; they must not be read as a list of all current open defects. Current mechanisms, evidence and remaining release work are recorded in [edge-case dispositions](EDGE_CASES.md), [local test results](LOCAL_TEST_RESULTS.md) and [release gates](RELEASE_GATES.md). Final native-package and target-platform qualification remains pending.

Reviewed `music_library_lab/analyzer.py`, `server.py`, and the related browser request/response code on 2026-10-11. This is a source review; it does not claim macOS runtime or decoder regression coverage. No private music was modified.

## Changes required before qualification

1. **Do not case-fold resolved paths on case-sensitive filesystems.** In `analyzer.py` the input lookup and record lookup call `.casefold()`. Two distinct files named `Song.mp3` and `song.mp3` on a case-sensitive macOS/Linux volume become one key. Both reports can then receive the latter file's ID, path, and fingerprint, with the former file's measured grade. Use `os.path.normcase(str(resolved_path))`, which folds paths on Windows and preserves case on POSIX. Reject duplicate scanner record keys and require the exact selected input set, rather than only matching record counts.

2. **Verify every selected input hash on every exit.** The adapter checks inventory hashes before starting, but checks post-run hashes only while reading successful report records. Cancellation, a missing/malformed report, a scanner failure, or an omitted record can bypass that check. The browser nevertheless says originals are unchanged. Wrap the execution and report handling in an integrity `finally` that rechecks every captured source path, including previously completed batches. If any file changed or disappeared, fail the run and do not publish results or an unchanged assurance. The hash check must complete before a terminal job status is exposed. Record the canonical scanner fingerprint at startup and verify it at the end as well, so a run cannot silently combine two scanner revisions.

3. **Bound evidence, logs, and retained results.** Each successful record holds up to 46,080 Python float objects for the overview, plus one dictionary per half-second bin. Thousands of tracks, repeated runs, or a very long track can exhaust memory. `state.jobs` retains all results indefinitely and subprocess logs also grow without a bound. For the small beta, enforce a documented selection/result size budget and cap log history. Longer term, serve per-track display evidence on demand while exporting reports from disk. Validate NPZ member uncompressed sizes and array dimensions before allocating arrays; reject or omit oversized display evidence without inventing another quality grade.

4. **Keep request payloads compact.** `app.js` posts full inventory objects to `/api/audit`, while the server uses only `id` and `enabled`. Original frame metadata and review text can push a large collection beyond the 4 MiB request limit. Send selected `{id, enabled: true}` rows only; resolve all paths/fingerprints from the server-held inventory.

5. **Do not hold the shared job lock while sending responses.** Job/report GET handlers serialize and write the complete report while holding `state.lock`. Large responses or a slow connection can block cancellation, progress updates, and other requests. Capture the needed immutable response reference/snapshot under the lock, then send after releasing it.

6. **Terminate and reap a subprocess on exceptional adapter exits.** The subprocess-loop `finally` closes stdout and stops its cancellation watcher, but does not terminate/wait for a still-running child if progress callbacks or stdout iteration raise. Ensure any live process is terminated, then wait with a bounded timeout and kill if necessary. Resolve cancellation under the job lock before marking a run complete, or explicitly treat a request arriving after the terminal result as already completed. Recheck cancellation after report processing and before publishing the combined report.

## Path and eligibility details

- The source inventory rejects file links and hard links, but `/api/audit` can turn any submitted inventory row back on regardless of its original disabled state. The adapter itself resolves paths and checks containment but does not reject links that point elsewhere *inside* the root. Keep an immutable `analyzable` flag in the server inventory, or repeat the inventory's ordinary-file checks at audit launch. This avoids bypassing the scanner's original refusal through selection controls.
- The server resolves an entered root before calling the inventory function, so the inventory cannot detect that the original user path traversed a symlink/junction. If linked roots are unsupported, validate the original path before resolution.
- `_Organization` exclusion in the adapter uses an exact case match while the inventory uses case-insensitive matching. Use the same exclusion and relative-path validation in both. Inventory-held IDs currently prevent an ordinary browser request from adding arbitrary backup paths, but direct adapter calls should retain the same invariant.
- Missing files fail before launching the scanner. Valid files with missing artist tags remain eligible for read-only analysis, which is appropriate. Existing HQ labels are included; the command does not pass `--skip-hq`.

## Confirmed design properties

- Quality grades come only from the configured canonical scanner invoked with `--full-spectrum`. Display pooling does not recompute grades, and bitrate is not used as a classifier.
- The server binds to `127.0.0.1`, requires the exact loopback Host, rejects a foreign Origin, and requires an unpredictable session token for API requests. The token is in the launch URL fragment and is removed from the visible URL by browser code. Static resources do not disclose the token.
- No organize, rename, retag, apply, or restore endpoint is exposed. The import from the organizer core is limited to read-only inventory. `/api/demo` creates only the separately designated synthetic demo collection.
- Arbitrary static-file paths are not served. JSON text is rendered through DOM text content. Responses include no-store, nosniff, referrer and content-security headers.
- No competing quality scanner was introduced by this review.

## Targeted verification to add

- Distinct case-sensitive file paths retain distinct IDs, fingerprints, and results.
- Duplicate/missing/unexpected output records are rejected.
- Source deletion/content change is detected after success, cancellation, and scanner/report exceptions.
- Cancellation stops and reaps the process, releases the busy flag, and cannot publish a stale success.
- Bad Host/Origin/token and every library mutation route are refused.
- Disabled linked/corrupt inventory entries cannot bypass audit eligibility through a forged selected row.
- Size limits fail clearly and permit another job; compact selections work with a larger inventory.

These findings describe the reviewed snapshot. Update their disposition after implementing and testing fixes; they are not an assertion that all findings remain open in later revisions.
