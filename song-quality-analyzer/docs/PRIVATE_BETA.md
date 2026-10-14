# Private beta preparation

This repository is a source preview for Spectracraft, the first ResetLab Craft
tool. It is not a qualified public download. Source is GPLv3-only; private
hosting controls repository access and does not add restrictions to the GPL.

The checkout contains the analyzer, generated canonical source and its manifest,
UI, tests and guides. Native decoder binaries, installers, private music,
artwork, local settings, cache reports and session credentials are excluded.
Follow [installation](INSTALLATION.md) to run from source.
Use a short Windows checkout path. A deeply nested source staging path exposed
Windows path-limit failures while writing cache markers; this is a known
source-preview limitation and remains part of platform qualification.

Before distributing a packaged Windows beta, complete its native clean-install,
window/dialog/cancellation/shutdown and network checks, and resolve the native
dependency licenses, notices and corresponding-source requirements. The existing
Windows worker passed its tests; that does not qualify the desktop window.
Neither Mac architecture has been built or tested. See [release gates](RELEASE_GATES.md).

Then invite a small Windows DJ/producer group to follow the
[beta test guide](BETA_TEST_GUIDE.md). Record OS, app version, reproducible steps,
expected/actual behavior, and sanitized screenshots when useful. Do not request
testers' music or publish their raw diagnostic reports. Add Mac testers after
native builds exist. Public launch and Instagram demos follow useful beta fixes.
