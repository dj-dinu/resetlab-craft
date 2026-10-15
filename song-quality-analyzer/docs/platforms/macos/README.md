# Spectracraft for Mac

**Public beta: 0.1.0-beta.1, published October 15, 2026.**

**[Download for Apple silicon Mac](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-beta.1/Spectracraft-0.1.0-beta.1-macos-arm64.zip)** · [Release notes, matching sources and checksums](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-beta.1)

Requires an M1 or newer Mac and macOS 15+. This beta is **ad-hoc signed and not notarized**. Intel Mac packages, older macOS and Linux are not qualified.

## Install and open

1. Download the **macos-arm64.zip** app asset. Most users do not need the source/dependency archives. No GitHub sign-in, Python or Homebrew is needed.
2. Extract it with Finder and open **Spectracraft.app**. You may move it to Applications. The app is directly inside this ZIP, without the old nested test kit.
3. If Apple blocks the first launch and you trust this download, choose **Done**, then **System Settings → Privacy & Security → Open Anyway** for Spectracraft, and confirm **Open**. Keep Gatekeeper enabled and follow administrator policy on managed devices. See [Apple's guidance](https://support.apple.com/en-us/102445).
4. Use **Add music** for a file/folder, then **Analyze selected tracks**. **Aa** adjusts text size; the sun/moon button changes appearance. Both choices persist locally.

Analysis stays local and leaves samples, filenames, tags, artwork and DJ collections unchanged. No accounts, analytics or music uploads are added. Reports retain relative filenames; review them before sharing.

## Test evidence and beta scope

Native macOS 15 ARM64 and Intel each pass 87 application tests and six-format checks. The ARM64 package passes canonical hash/self-test, source/frozen comparisons, duration integrity, acknowledged pause/resume, normal window launch/quit and all 19 Cocoa UI checks, including text persistence, 150%/420px layout, 103-track batching and paused-worker/server cleanup. [Native run](https://github.com/dj-dinu/resetlab-craft/actions/runs/38774791171).

The actual embedded runtime is Python 3.13.16, OpenSSL 3.5.9 and Expat 2.8.5; the manifest and numeric/readable bundle versions agree (build 1001). Public download bytes match the tested archive. Earlier positive volunteer feedback came from a MacBook Air M4, with 45/45 tracks and no errors; macOS 26.6.2 was reported, not independently verified.

Automation substitutes selected dialog paths. Actual pickers/save/drop gestures, clean-account installs, permissions denial, Retina/trackpad/display scaling, runtime network capture and storage/cloud/device cases still need broader feedback. The public unsigned route was explicitly chosen; Developer ID signing/notarization remain future work.

Report OS/chip, app version, action and observed behavior in [GitHub Issues](https://github.com/dj-dinu/resetlab-craft/issues). Keep private music, session links, credentials and absolute diagnostics out of public reports. Use the [volunteer checklist](VOLUNTEER_TEST.md) for detailed feedback and [release review](RELEASE_REVIEW.md) for evidence. Earlier workflow kits are historical artifacts; use the permanent Release download above.

For development, see [native build/testing](TESTING.md). For everyday use, see the [shared user guide](../../USER_GUIDE.md).
