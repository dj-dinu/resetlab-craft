# Installation

Bandprism beta.2 is the renamed analyzer (formerly Spectracraft).
Run as a normal user. No Python installation, app account or subscription is
needed for the packaged app. Linux and Intel Mac packages are not released.

## Windows x64

1. [Download Bandprism.exe](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-beta.2/Bandprism-0.1.0-beta.2-windows-x64.exe) from the [versioned release](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-beta.2).
2. Open the EXE. Everything is included; there is no separate `_internal` folder
   to extract or unblock. Microsoft Edge WebView2 Runtime is required.
3. Use **Add music** for a folder or audio file, then analyze selected tracks.

The build is unsigned, so Windows may still display publisher/reputation warnings.
Follow your device policy; this packaging change does not disable security
protections or remove the download marker. On managed devices, administrator
policy may prevent unsigned software from running.

If you downloaded an older **Spectracraft beta.1 ZIP**, its
[legacy startup workaround](platforms/windows/README.md#older-spectracraft-beta1)
still applies. Download beta.2 for the packaging fix instead.

## Apple silicon Mac

1. [Download the Mac ZIP](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-beta.2/Bandprism-0.1.0-beta.2-macos-arm64.zip); extract it with Finder.
2. Open `Bandprism.app` on an M1 or newer Mac with macOS 15+.
3. The build is ad-hoc signed and not notarized. If Apple cannot verify it, follow
   the [per-app first-launch guide](platforms/macos/README.md). Keep Gatekeeper enabled.

Review the release's SHA256SUMS file to check the exact download bytes.
A matching checksum verifies the published bytes, not the absence of malware.

## Developer setup

Python 3.13.16 is the beta.1 baseline. Actual embedded OpenSSL 3.5.9 and
Expat 2.8.5 are verified against the package manifest. Use the matching patched
runtime for release reproduction; older Python 3.12 results are historical. From the project folder:

For a suite checkout, first enter `song-quality-analyzer`. This public source
checkout contains the exact generated canonical scanner. Installers/native
decoder binaries are supplied separately as reviewed release/test assets.
Native Mac source checks and the public ARM64 package have been tested;
remaining manual qualification is disclosed in the Mac guide.
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

On Windows, the output is the complete `dist/Bandprism` folder. The same
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
