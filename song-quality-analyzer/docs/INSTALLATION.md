# Installation

Choose the [Windows public beta](platforms/windows/README.md) or the
[Apple silicon Mac candidate](platforms/macos/README.md). The Mac package is
currently a volunteer test build, with public release gates still open. Linux
is deferred. Run as a normal user; analysis does not need administrator access.

## Windows beta download

1. [Download the complete Windows ZIP](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-alpha.5/Spectracraft-0.1.0-alpha.5-windows-x64.zip).
2. Extract it into a writable folder with a short path. Keep `Spectracraft.exe`
   beside `_internal`; do not copy only the executable.
3. Open `Spectracraft.exe`. Use **Add music** for a folder or audio file, wait
   for metadata to load, then analyze. No developer Python installation is needed.

The build is unsigned and uses Microsoft Edge WebView2 Runtime. Follow your
device's security policy and report launch blocks. Review the
[beta notes](platforms/windows/README.md) and [release checksums](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-alpha.5).

## Mac test candidate

Use the [Mac overview](platforms/macos/README.md) for the test-kit download,
macOS/architecture scope, signing status and extraction steps. Python and
Homebrew are not needed to run the packaged app. Follow the
[volunteer checklist](platforms/macos/VOLUNTEER_TEST.md). A successful source
test or launch does not qualify Gatekeeper or every native interaction.

The current kit needs a bundled runtime security refresh before a public Mac
release; see the [ordered release plan](platforms/macos/RELEASE_PLAN.md).

## Current local Windows build

The latest local build is alpha.5 at `dist/alpha5/Spectracraft`. Close the
previous app before opening the new executable, and keep its complete
`_internal` folder beside it. Use the complete versioned alpha.5 folder.

1. Open the complete folder `dist/alpha5/Spectracraft` in the project workspace.
2. Keep Spectracraft.exe beside its _internal folder; do not copy only the executable.
3. Open Spectracraft.exe, use Add music to choose a folder or audio file, wait for metadata to load automatically, then analyze.

Alpha.3 applies the [updated 40% quality rule](QUALITY_RULES.md). Reanalyze to
replace an earlier measurement; existing saved reports and song tags stay as they were.

Alpha.5 adds automatic alphabetical batches, Pause/Resume and Stop while
retaining the 420 × 360 logical-pixel window minimum. On Windows,
try Win + Left or Win + Right for half-screen placement. The layout adapts
to narrow widths; move horizontally inside the results panel to reach all
columns. Actual native snapping and display-scale combinations still need
manual testing.

The bundle includes Python, the reviewed scanner and audio decoders. Windows needs the Microsoft Edge WebView2 Runtime used by the native window. Get missing prerequisites from the [official Microsoft source](https://developer.microsoft.com/en-us/microsoft-edge/webview2/). The current build is unsigned and native operation still needs manual qualification; a security block or launch failure belongs in the test record.

If the window cannot launch, the developer browser fallback below can help diagnose the app. It does not qualify the native installer.

## Developer setup

Python 3.12 is the existing qualification baseline. Use a maintained patched
runtime and record the actual bundled native-library versions; the old Mac kit
runtime is not the public-release target. From the project folder:

For a suite checkout, first enter `song-quality-analyzer`. This public source
checkout contains the exact generated canonical scanner. Installers/native
decoder binaries are supplied separately as reviewed release/test assets.
Native Mac source checks and an ARM64 package have been tested; public Mac
distribution remains pending.
Use a short Windows checkout path, such as `C:\Projects\ResetLabCraft`.
Deeply nested source checkouts can exceed Windows file-path limits when writing
analysis caches; comprehensive long-path qualification remains pending.

    python -m venv .venv

Windows:

    .venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
    .venv\Scripts\python.exe run_desktop.py

For macOS, follow the [native source and build instructions](platforms/macos/TESTING.md)
for the architecture-matching runtime, mpg123 and tested NumPy baseline.

The checkout includes `canonical/scan_quality.py` and its SHA-256 manifest.
Verify it with `python tools/export_canonical_source.py --check`. The app uses
that generated source by default. Maintainers may configure the sole maintained
original using the ignored `local_settings.json` field `scanner_path` or
`MUSIC_LIBRARY_SCANNER`; never substitute another classifier.

MP3 decoding also requires a matching platform/architecture libmpg123 library
from the [official mpg123 project](https://www.mpg123.de/download.shtml).
Set `SONG_AUDIT_MPG123_PATH` to its full library path, or set `decoder_path` in
the ignored `local_settings.json`. Do not copy decoders from commercial DJ apps.
WAV/AIFF/FLAC/AAC/ALAC use the installed PyAV dependency. Native library
materials accompany reviewed binary downloads; the Git source tree itself
does not contain those native libraries.

For the local browser fallback, install requirements.txt and run:

    python run_local.py

Open the session link printed by the launcher. It binds to 127.0.0.1; keep that session link private. Stop the terminal process to close the development server. Native app shutdown closes its own local server.

To build the Windows alpha:

    python -m pip install -r requirements-build.txt
    python tools/build_desktop.py --decoder PATH_TO_LIBMPG123_DLL

On Windows, the output is the complete `dist/Spectracraft` folder. The same
builder has a native Mac path; use the [ARM64 recipe](platforms/macos/TESTING.md)
for its `.app`, architecture checks and archive/extract validation. Build each
platform on its native OS; there is no qualified cross-compilation path.

## Platform decisions

Target Windows and macOS first. Native Mac source tests cover Intel/Apple
silicon; packaged qualification currently covers ARM64 only. Dialog, signing,
clean-account and broader device checks remain distinct release gates. Linux
adds a renderer and distribution-specific dependencies and is deferred. See
the [platform overview](platforms/README.md) and
[official pywebview requirements](https://pywebview.flowrl.com/guide/installation.html).

Installing dependencies/downloads uses the relevant vendor or package service. Analysis itself has no online account or upload flow. For offline testing, use files fully stored on the local disk.

For usage, see the [short guide](USER_GUIDE.md). For source tests:

    python -m unittest discover -s tests

Tests need local loopback sockets. Native OS dialogs and actual platform installs require the manual launch checklist as well.
