# macOS qualification

Mac is not a released platform yet. The native test workflow targets macOS15
Intel(x64) and Apple silicon(arm64) on standard GitHub runners. It verifies the
same canonical scanner, application suite, synthetic six-format read-only
analysis, source hashes and pause/resume acknowledgments. Cocoa backend import
is checked; passing automation does not establish an interactive GUI or .app
package. No private music or settings are uploaded.

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

Use the [beta guide](BETA_TEST_GUIDE.md) for file/folder dialogs, Finder drops,
report save/cancel/existing destinations, Pause/Resume/Stop and closing while
paused, light/dark appearance, trackpad/Retina resizing and offline traffic.
Include percent signs, decomposed Unicode, denied folder permissions, iCloud
placeholders and removable drives. Links/aliases are intentionally refused.
Hash sources before/after. Use synthetic or shareable tracks first.

The current packaging recipe is Windows-only. A Mac .app/installer, bundled
dylib discovery, signing/notarization and clean-user launch need a separate
native build and qualification. Do not advertise a downloadable Mac release
based only on a passing source workflow.

Runner/dependency references: [GitHub standard runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[pywebview installation](https://pywebview.flowrl.com/guide/installation.html),
[Homebrew mpg123](https://formulae.brew.sh/formula/mpg123).
