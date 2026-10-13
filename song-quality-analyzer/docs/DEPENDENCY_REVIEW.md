# Dependency review

Local evidence, October 12, 2026. This is an inventory and bounded advisory lookup, not complete native security or redistribution qualification.

The installed runtime/build dependency traversal found 19 Python packages, no missing required packages, and no matching advisories in the executed public OSV batch lookup. Only public package names/versions were sent; no music, filenames, settings or session tokens were sent. Unreported vulnerabilities and native DLLs are outside that result. See the [OSV API](https://google.github.io/osv.dev/api/).

| Component | Observed version |
| --- | --- |
| Python | 3.12.14 |
| NumPy / Mutagen | 2.3.5 / 1.47.0 |
| PyAV / pywebview | 19.0.0 / 6.2.1 |
| PyInstaller / Pillow (build tools) | 6.22.3 / 12.3.0 |
| libmpg123 | 1.33.7 |
| FFmpeg runtime | 9.0.2, as returned by the loaded library |

The loaded FFmpeg codec library reports LGPL version 3 or later. Its configuration and every vendored DLL's SHA-256 are recorded privately. Optional video libraries are present even though the app analyzes audio only; their individual licenses and exact corresponding sources still need review. Do not infer the entire bundle's license from the codec library's returned string.

FFmpeg's [official distribution checklist](https://ffmpeg.org/legal.html) calls for reviewing the build options, linking, matching sources/build instructions and notices. PyAV's [installation documentation](https://pyav.basswood.io/docs/stable/overview/installation.html) confirms that its binary wheels bundle FFmpeg. A Python package license alone does not settle the native binaries' redistribution obligations.

Before publication, review the exact native builds and security advisories, complete notices/source/build materials and review the selected GPLv3 license and code ownership. If a smaller audio-only decoder build is selected, repeat canonical self-test, format/integrity fixtures and exact real HQ/MQ/LQ regression checks. Keep the same canonical scanner; this review does not create a second classifier or change grading.
