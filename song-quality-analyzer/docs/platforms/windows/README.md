# Bandprism for Windows

**[Download beta.2 — Windows x64 EXE](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-beta.2/Bandprism-0.1.0-beta.2-windows-x64.exe)** ·
[Release, matching sources and checksums](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-beta.2)

## Install and start

1. Download the EXE from the official GitHub release.
2. Open it as a normal user. No installer, Python, separate `_internal` folder or
   DLL-unblocking step is needed for the beta.1 loader issue.
3. Microsoft Edge WebView2 Runtime is required. Choose **Add music**, then analyze.

Bandprism is the new name of Spectracraft, under ResetLab Craft. The Windows
package now embeds its runtime in one executable. Its normal bootloader unpacks
private temporary runtime files and cleans them on exit. This avoids propagating
the ZIP's Internet-zone marker onto .NET DLLs. The downloaded EXE's marker is
retained. No Defender, SmartScreen, registry or machine-wide trust setting is changed.

The beta remains unsigned. Publisher/reputation warnings and managed-device
restrictions are separate from the fixed .NET DLL-loading failure. Follow your
device's security policy. First launch can take a little longer while the runtime
is unpacked. Do not run the app as administrator.

## Older Spectracraft beta.1

Beta.1's folder ZIP can fail with `Failed to resolve Python.Runtime.Loader.Initialize`
when Windows propagates its download marker to managed DLLs. That was reproduced
locally and resolved by explicitly trusting the original ZIP through Properties
and extracting it into a fresh folder. Beta.2 replaces that packaging route;
existing beta.1 downloads are not patched or silently rewritten.

## Checks and limits

The release gate runs the full application suite, canonical self-test, six-format
source/frozen comparison, duration-integrity and pause/resume checks. A separate
gate marks an owned copy of the exact candidate EXE as Internet-zone3, opens the
actual native window/bridge, verifies clean shutdown, and checks that its executable
bytes and marker stay unchanged. See the attached workflow evidence for the
specific commit and artifact hashes. A controlled marker test does not qualify
every browser, antivirus product, network drive or administrator policy.

Use [GitHub Issues](https://github.com/dj-dinu/resetlab-craft/issues) for failures:
include app/Windows version, action and error text. Do not share private music,
session links or diagnostic credentials. [User guide](../../USER_GUIDE.md) ·
[Privacy](../../PRIVACY.md) · [Installation](../../INSTALLATION.md).
