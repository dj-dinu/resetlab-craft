# Bandprism for Mac

**Public beta: 0.1.0-beta.2.**

**[Download for Apple silicon Mac](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-beta.2/Bandprism-0.1.0-beta.2-macos-arm64.zip)** · [Release notes, matching sources and checksums](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-beta.2)

Requires an M1 or newer Mac and macOS 15+. This beta is **ad-hoc signed and not notarized**. Intel Mac packages, older macOS and Linux are not qualified.

We are distributing this community beta without the Apple Developer Program.
An Apple developer membership is not required to download or use it.

## Install and open

1. Download the **macos-arm64.zip** app asset. Most users do not need the source/dependency archives. No GitHub sign-in, Python or Homebrew is needed.
2. Extract it with Finder and open **Bandprism.app**. You may move it to Applications. The app is directly inside this ZIP, without the old nested test kit.
3. If Apple blocks the first launch and you trust this download, choose **Done**, then **System Settings → Privacy & Security → Open Anyway** for Bandprism, and confirm **Open**. Keep Gatekeeper enabled and follow administrator policy on managed devices. See [Apple's guidance](https://support.apple.com/en-us/102445).
4. Use **Add music** for a file/folder, then **Analyze selected tracks**. **Aa** adjusts text size; the sun/moon button changes appearance. Both choices persist locally.

### What the first-launch warning means

The “developer cannot be verified” or “Apple could not verify it is free of malware”
notice is expected for this beta: Apple has not verified its developer identity
or notarized the app. That notice alone is not a malware-detection result, and
it is not a guarantee that the app is safe. Read the source, test scope and
download information before deciding whether to open it.

Use only the versioned [GitHub release](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-beta.2).
The per-app Open Anyway exception above leaves Mac security enabled. If the
alert instead reports detected malware, says the app will damage your computer,
or says it is damaged, stop and report the exact message. See
[Apple's explanation of these different alerts](https://support.apple.com/en-us/102445).

### Optional: check your downloaded ZIP

In Terminal, run this for the original filename in Downloads:

```sh
shasum -a 256 "$HOME/Downloads/Bandprism-0.1.0-beta.2-macos-arm64.zip"
```

Compare the result with this release's `SHA256SUMS-macos-arm64.txt`.
Do not use a beta.1 checksum for a renamed beta.2 archive. If your browser changed
the filename, adjust the command. A matching hash verifies published bytes,
not the absence of malware.

Analysis stays local and leaves samples, filenames, tags, artwork and DJ collections unchanged. No accounts, analytics or music uploads are added. Reports retain relative filenames; review them before sharing.

## Test evidence and beta scope

Formerly Spectracraft. The new bundle is `Bandprism.app`; keep old reports as-is.

Beta.2 runs its own ARM64 package and Cocoa UI qualification on the exact
candidate commit. Earlier87-test/six-format/19-UI-check evidence and positive
MacBook Air M4 volunteer feedback apply to Spectracraft beta.1, not automatically
to a renamed binary. See the current release's workflow evidence and manifests
for passed checks, build1002 and exact archive hashes. The Mac packaging and
per-app unverified-developer warning remain unchanged.

Automation substitutes selected dialog paths. Actual pickers/save/drop gestures, clean-account installs, permissions denial, Retina/trackpad/display scaling, runtime network capture and storage/cloud/device cases still need broader feedback. The public unsigned route was explicitly chosen; Developer ID signing/notarization remain future work.

Report OS/chip, app version, action and observed behavior in [GitHub Issues](https://github.com/dj-dinu/resetlab-craft/issues). Keep private music, session links, credentials and absolute diagnostics out of public reports. Use the [volunteer checklist](VOLUNTEER_TEST.md) for detailed feedback and [release review](RELEASE_REVIEW.md) for evidence. Earlier workflow kits are historical artifacts; use the permanent Release download above.

For development, see [native build/testing](TESTING.md). For everyday use, see the [shared user guide](../../USER_GUIDE.md).
