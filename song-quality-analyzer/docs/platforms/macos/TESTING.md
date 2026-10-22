# macOS qualification

The unsigned Apple silicon public beta is available; see the [Mac guide](README.md). Source/backend qualification passed on native
macOS 15 Intel and Apple silicon runners. The extended workflow builds an ARM64
`.app`, archives and extracts it with `ditto` to preserve executable bits and
symlinks, and checks the extracted package. The current deployment target is
macOS 15 or later. Older systems and Intel packages require separate qualification.

## Packaged qualification

- Exact canonical engine hash/self-test and application/JavaScript tests.
- Generated WAV, AIFF, FLAC, ALAC, AAC and MP3 inputs with unchanged hashes.
- Normal ARM64 bundle: native executable/decoder slices, ad-hoc signature,
  frozen worker self-test, exact source/package metrics, time bins and spectrum
  previews, and acknowledged Pause/Resume without Python/Homebrew on PATH.
- Normal extracted app: visible Cocoa window and native application quit.
- Separate instrumented test bundle: actual WKWebView controls, folder inventory,
  progress, results, grade filter, evidence, report export, alphabetical automatic
  batches of 50/50/3, Pause/Resume, Stop, half-screen resize, appearance and close
  with a paused decoder.

Native testing found that pywebview 6.2.1's generated API functions were blocked
by WKWebView's CSP enforcement. The Mac adapter uses normal closures and native
JavaScript completion values for the five approved bridge methods. The strict
CSP, local-origin guards and argument/result protocol remain in place. The
bridge protocol is also tested with dynamic code generation disabled.

The build-only UI driver is enabled by `--ui-test-driver` for a separate CI app.
It is absent from the normal app. File/folder/save dialog selections are
substituted to test the actual bridge and page controls; this does not qualify
the native dialog windows themselves. Evidence uses
only generated audio. No session tokens, private settings or music are uploaded.

Release branches/manual qualification upload public beta candidate assets only after package/UI tests and matching
native dependency source checks pass. It contains the normal app ZIP, current
project source, exact Python package sources, native source/build materials,
notices, hashes and the volunteer guide. A changed FFmpeg/mpg123 version stops
assembly until its matching materials are reviewed. The instrumented app is
never uploaded. No signing credentials are configured; builds are ad-hoc signed
and not notarized. Qualification artifacts alone do not publish a release. The public beta is a separate GitHub prerelease.
Use [the volunteer checklist](VOLUNTEER_TEST.md) for Finder drops, native
pickers, TCC, Gatekeeper, Retina/trackpad behavior and clean-user installation.

## Reproduce the Apple silicon build

After the source setup below, from `song-quality-analyzer`:

```sh
.venv/bin/python -m pip install -r requirements-build.txt numpy==2.3.5
.venv/bin/python tools/build_desktop.py --scanner canonical/scan_quality.py \
  --decoder "$SONG_AUDIT_MPG123_PATH" --dist-dir dist/macos-arm64
.venv/bin/python tools/validate_platform_smoke.py \
  --bundle dist/macos-arm64/Bandprism.app --report .work/macos-frozen.json
.venv/bin/python tools/build_desktop.py --scanner canonical/scan_quality.py \
  --decoder "$SONG_AUDIT_MPG123_PATH" --dist-dir dist/macos-ui-test --ui-test-driver
.venv/bin/python tools/validate_macos_gui.py --bundle dist/macos-arm64/Bandprism.app \
  --ui-test-bundle dist/macos-ui-test/Bandprism.app --output .work/mac-gui-evidence
```

Build on native ARM64 macOS. Python and Homebrew are build/test requirements;
the packaged app contains its own runtime and decoder.

## Run from source on a Mac

Use a native Python3.12 installation matching the Mac architecture. From the
`song-quality-analyzer` folder:

    python3.12 -m venv .venv
    .venv/bin/python -m pip install -r requirements-desktop.txt numpy==2.3.5
    brew install mpg123
    export SONG_AUDIT_MPG123_PATH="$(brew --prefix mpg123)/lib/libmpg123.0.dylib"
    .venv/bin/python tools/export_canonical_source.py --check
    .venv/bin/python canonical/scan_quality.py --self-test
    .venv/bin/python tools/validate_platform_smoke.py --report .work/macos-smoke.json
    sh "Start Desktop macOS.command"

The source ZIP may not preserve executable bits; `sh` works without them.
Alternatively `chmod +x "Start Desktop macOS.command"` before opening it.
Plain pywebview6.2.1 installs its Darwin PyObjC dependencies; no Cocoa extra is
required. libmpg123 must match the Python process architecture.

## Native checks still required

Use the [beta guide](../../BETA_TEST_GUIDE.md) for file/folder dialogs, Finder drops,
report save/cancel/existing destinations, Pause/Resume/Stop and closing while
paused, light/dark appearance, trackpad/Retina resizing and offline traffic.
Include percent signs, decomposed Unicode, denied folder permissions, iCloud
placeholders and removable drives. Links/aliases are intentionally refused.
Hash sources before/after. Use synthetic or shareable tracks first.

Do not advertise a public Mac release based only on automation. Preserve the
distinction between source tests, an ordinary packaged launch, the instrumented
UI flow and a volunteer's downloaded-package qualification.

Runner/dependency references: [GitHub standard runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[pywebview installation](https://pywebview.flowrl.com/guide/installation.html),
[Homebrew mpg123](https://formulae.brew.sh/formula/mpg123).
