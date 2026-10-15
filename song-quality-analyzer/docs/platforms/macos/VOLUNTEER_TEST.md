# Apple silicon volunteer test

This checklist covers the normal app package. Record its version and test scope.

Allow about 20 minutes on an M1 or newer Mac with macOS 15 or later. Use an
ordinary account without installing Python or Homebrew. Start with copies of
audio you may share; audio, tags and artwork should remain unchanged.

Use only a normal `Spectracraft.app` package from the maintainer. The separate
CI app containing the UI driver is not a volunteer or public download. Record
the ZIP SHA-256, app version, macOS version and Mac chip in your notes.
Extract `Synthetic-audio-tests.zip` to start with the included generated audio.
`Formats café % audio` tests six formats; `Batch 103 café % తెలుగు` tests
automatic batching; `Pause and close` supplies a longer track for controls.

1. Download and extract the ZIP with Finder, move the app to Applications and
   open it normally. Record any security prompt and its exact wording. Test
   builds are ad-hoc signed; Gatekeeper approval is not established. Do not
   disable Gatekeeper globally. Report a blocked launch before proceeding.
2. Add one file and then a folder through the native pickers. Cancel both and
   confirm the previous selection stays intact. Try Finder drops of a file and
   a folder into the app. Include percent signs, Telugu/non-Latin text, emoji,
   accented/decomposed Unicode and a long filename.
3. Analyze MP3, WAV, AIFF, FLAC, AAC and ALAC if available. Inspect grades,
   duration and evidence. Corrupted/unsupported files should show an error
   without preventing other files finishing.
4. Analyze at least 103 tracks. Confirm title A–Z, automatic batches of 50/50/3,
   progress and the folder summary. Pause, wait for acknowledgment, resume and
   Stop. Completed batches should remain available. Close while paused and
   confirm no decoder process remains in Activity Monitor.
5. Resize to half the screen and a narrow window. Try trackpad scrolling,
   light/dark mode, Retina, reduced motion and increased text size. Controls
   should remain reachable and long titles should reveal their full name.
6. Save a JSON report, cancel the save dialog and choose an existing filename.
   Existing files should be preserved. Exports should omit absolute library
   and cache paths.
7. Repeat a small analysis with Wi-Fi disconnected. Try denied permissions,
   an unavailable external drive and an iCloud file not downloaded. Record
   the errors without changing broad system permissions to pass.
8. Compare original files before/after, including tags/artwork. In Terminal,
   `shasum -a 256 "/path/to/track.mp3"` records a hash. Restart and check saved
   appearance and ordinary launch behavior.

## Return this result

```text
Build/version and ZIP SHA-256:
Mac chip / macOS version:
First launch / security prompt:
File/folder picker and cancellation: PASS / FAIL
Finder file/folder drops: PASS / FAIL
Formats / errors / evidence: PASS / FAIL
103-track batching / progress: PASS / FAIL
Pause / Resume / Stop / close while paused: PASS / FAIL
Resize / trackpad / appearance: PASS / FAIL
Report save / cancel / existing-file protection: PASS / FAIL
Offline / permissions / external-drive behavior: PASS / FAIL
Source hashes unchanged: YES / NO
Issue, expected behavior, actual behavior and reproduction steps:
```

Hide private filenames/paths in screenshots. Share audio or reports only if
you intend to disclose their contents; no music upload is needed to report an
interface issue. Do not include session tokens or credentials.
