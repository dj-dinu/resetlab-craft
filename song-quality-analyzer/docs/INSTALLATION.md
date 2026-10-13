# Installation

Spectracraft is a local alpha. There is no public download or qualified Mac/Linux package yet. Run as a normal user; administrator access is not needed for analyzing songs.

## Current local Windows build

1. Open the complete folder dist/Spectracraft in the project workspace.
2. Keep Spectracraft.exe beside its _internal folder; do not copy only the executable.
3. Open Spectracraft.exe, choose a music folder or one audio file, click Read folder or file, then analyze.

The bundle includes Python, the reviewed scanner and audio decoders. Windows needs the Microsoft Edge WebView2 Runtime used by the native window. Get missing prerequisites from the [official Microsoft source](https://developer.microsoft.com/en-us/microsoft-edge/webview2/). The current build is unsigned and native operation still needs manual qualification; a security block or launch failure belongs in the test record.

If the window cannot launch, the developer browser fallback below can help diagnose the app. It does not qualify the native installer.

## Developer setup

Use Python 3.12, the tested development version. From the project folder:

For a suite checkout, first enter `song-quality-analyzer`. This private source
preview contains the exact generated canonical scanner, but no installers or
native decoder binaries. Windows is the initial beta target; Mac remains untested.
Use a short Windows checkout path, such as `C:\Projects\ResetLabCraft`.
Deeply nested source checkouts can exceed Windows file-path limits when writing
analysis caches; comprehensive long-path qualification remains pending.

    python -m venv .venv

Windows:

    .venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
    .venv\Scripts\python.exe run_desktop.py

macOS developer entry point, untested natively:

    .venv/bin/python -m pip install -r requirements-desktop.txt
    .venv/bin/python run_desktop.py

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
redistribution remains pending, so this repository contains source only.

For the local browser fallback, install requirements.txt and run:

    python run_local.py

Open the session link printed by the launcher. It binds to 127.0.0.1; keep that session link private. Stop the terminal process to close the development server. Native app shutdown closes its own local server.

To build the Windows alpha:

    python -m pip install -r requirements-build.txt
    python tools/build_desktop.py --decoder PATH_TO_LIBMPG123_DLL

The output is the complete dist/Spectracraft folder. This recipe does not build a Mac package.

## Platform decisions

Target Windows and macOS first. macOS needs separate native Intel/Apple Silicon installation, decoder, dialog, signing and resource checks. Linux adds a GTK or Qt renderer and distribution-specific dependencies; evaluate it after the first two platforms are stable. See the [official pywebview platform requirements](https://pywebview.flowrl.com/guide/installation.html).

Installing dependencies/downloads uses the relevant vendor or package service. Analysis itself has no online account or upload flow. For offline testing, use files fully stored on the local disk.

For usage, see the [short guide](USER_GUIDE.md). For source tests:

    python -m unittest discover -s tests

Tests need local loopback sockets. Native OS dialogs and actual platform installs require the manual launch checklist as well.
