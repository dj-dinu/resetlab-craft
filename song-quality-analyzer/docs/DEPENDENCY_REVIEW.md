# Dependency review

## Bandprism beta.2 candidate — October 21, 2026

The candidate pins Pillow 13.0.0 for icon creation. The release gate found 28
applicable advisories for the earlier 12.3.0 build dependency; their affected
ranges end at 13.0.0. The exact-version OSV query for 13.0.0 returned no matches.
See an [upstream advisory record](https://osv.dev/vulnerability/GHSA-22hg-r758-rrw9).
The gate still blocks unresolved package advisories, including build tools;
each native candidate generates its own inventory before packaging. This is a
bounded advisory check, not a guarantee against undisclosed vulnerabilities.

## Current public beta — October 15, 2026

[Beta.1](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-beta.1)
is public for Windows x64 and Apple silicon/macOS 15+. Both embedded runtimes
were refreshed and verified: Python 3.13.16, OpenSSL 3.5.9 and Expat 2.8.5.
Native package/source checks passed, public download hashes match, and matching
platform source materials/notices are published alongside the apps. The bounded
package advisory lookup found no matches; it does not cover every native risk.

The owner chose to continue the unsigned/ad-hoc Mac beta without enrolling in
the Apple Developer Program for now. Notarization is deferred, not a requirement
for this beta's availability. The [Mac guide](platforms/macos/README.md) explains
the first-launch notice and optional download check. Remaining native/manual
qualification limits are disclosed in the release notes.

## Historical inventory and findings

Local evidence, updated October 14, 2026. This is an inventory, source/notice preparation and bounded advisory lookup, not a universal security certification.

## Windows beta materials

The beta preparation collected 17 decoder/upstream source archives, the pinned
PyAV FFmpeg 9.0.2-1 build recipe and patches, and exact source distributions
for 14 installed Python/runtime/build packages. Pinned upstream SHA-256 values
were verified where supplied. Libiconv 1.19 source and the matching MSYS2
recipe/patches were collected. GCC runtime exception and winpthreads notices
are included alongside Python, NumPy/OpenBLAS, mpg123, PyAV, WebView2 and the
remaining package notices. The project license does not replace those terms.

The FFmpeg build reports LGPLv3-or-later, but its upstream patch changes the
configure classification of x264/x265 and the bundle includes those GPL
libraries. Do not describe the entire native bundle as BSD or LGPL based only
on one returned license string. The public candidate preserves third-party
licenses and provides their source/build materials; project-owned source
remains GPL-3.0-only. The upstream [build recipe](https://github.com/PyAV-Org/pyav-ffmpeg/tree/9.0.2-1)
and [FFmpeg distribution guidance](https://ffmpeg.org/legal.html) explain the
relevant build and source boundaries.

These additions do not change the tested analyzer code or native libraries.
The published beta is unsigned, Windows x64 only, and broader native security/install
qualification remains part of beta testing. Publication and downloadable
asset hashes must be verified before announcing the release.

## Mac candidate review — October 14

The Mac kit contains matching project source, 23 source archives/receipts,
native source/build materials and notices. Its 79 listed checksums were
reverified. This is separate from the older Windows advisory result below.

The exact Mac build uses Python 3.12.10, OpenSSL 3.0.16, Expat 2.7.1, NumPy
2.3.5, Mutagen 1.47.0, PyAV 19.0.0, pywebview 6.2.1, FFmpeg 9.0.2 and mpg123
1.33.7. A fresh OSV query for its 20 recorded PyPI package/version pairs found
zero advisory matches. Only public names/versions were submitted; native
libraries and the interpreter are outside that result.

**Public Mac gate: refresh the bundled runtime.** Python/OpenSSL/Expat lack
later upstream security fixes. No Bandprism exploit was demonstrated, but
the current inventory is not security-complete. Use an updated supported
runtime with patched embedded libraries, then rerun source/frozen/UI and exact
regression checks and regenerate corresponding sources/checksums. See
[Python's Expat fix](https://www.python.org/downloads/release/python-31212/) and
[OpenSSL advisories](https://www.openssl-library.org/news/vulnerabilities-3.0/index.html).

PyAV 19.0.1 fixes a stream reference cycle; consider it during that rebuild
and check large-batch memory. This was not a matched security advisory.
See the [upstream release](https://github.com/PyAV-Org/PyAV/releases/tag/v19.0.1).
The [Mac release review](platforms/macos/RELEASE_REVIEW.md) records actual scope
and open native/signing/manual checks. Do not mark all native review flags
complete based on a package lookup or the presence of source materials.

## Earlier advisory inventory

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
