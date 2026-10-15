# ResetLab Craft

An audio workshop for DJs and producers. ResetLab Craft is the parent brand for a family of focused local music tools. Spectracraft's Windows and Apple silicon public beta is available.

**[Windows x64](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-beta.1/Spectracraft-0.1.0-beta.1-windows-x64.zip)** · **[Mac Apple silicon](https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-beta.1/Spectracraft-0.1.0-beta.1-macos-arm64.zip)** · [Beta.1 release notes, sources and checksums](https://github.com/dj-dinu/resetlab-craft/releases/tag/v0.1.0-beta.1)

Windows: extract the complete ZIP and open `Spectracraft.exe`, keeping `_internal` beside it. Mac: extract with Finder and open `Spectracraft.app` on an M1 or newer Mac with macOS 15+. Both are unsigned early betas; Mac is ad-hoc signed and not notarized. See the platform guides for first-launch instructions.

| Platform | Status | Start here |
| --- | --- | --- |
| Windows x64 | Public beta available | [Download and installation](song-quality-analyzer/docs/platforms/windows/README.md) |
| Mac Apple silicon | Unsigned public beta available, macOS 15+ | [Download and installation](song-quality-analyzer/docs/platforms/macos/README.md) |
| Mac Intel | Native source tests passed; no app package qualified | [Native test scope](song-quality-analyzer/docs/platforms/macos/TESTING.md) |
| Linux | Deferred; no package | [Linux status](song-quality-analyzer/docs/platforms/linux/README.md) |

**[Spectracraft](song-quality-analyzer/README.md)** is the first implemented tool: inspect full-track spectral coverage, review folder scores and keep evidence without altering music. See the [documentation index](song-quality-analyzer/docs/README.md) and [repository map](song-quality-analyzer/docs/REPOSITORY_LAYOUT.md) for shared source, platform guides, tests and build outputs.

| Tool | Purpose | Status |
| --- | --- | --- |
| Spectracraft | Spectral inspection, folder summaries and integrity checks | Windows and Apple silicon public beta |
| Keycraft | Musical key, BPM and harmonic-mixing assistance | Future concept |
| Stemcraft | Reuse versioned separated stems where supported | Feasibility research |
| Setcraft | Suggest the next song, transition cue points and optional wordplay links | Future concept |
| Cratecraft | Review and organize a library while preserving DJ metadata | Deferred |

See the [suite roadmap](song-quality-analyzer/docs/SUITE_ROADMAP.md), [brand direction](song-quality-analyzer/docs/BRAND.md) and [release gates](song-quality-analyzer/docs/RELEASE_GATES.md). A paid website and convenient updates are saved future ideas; current work is the local analyzer and its open-source release preparation.

## License

Current project-owned Spectracraft source is licensed under [GNU GPLv3 only](LICENSE). Reuse, modification and commercial redistribution are allowed under its conditions. See [reuse and branding](song-quality-analyzer/docs/REUSE_AND_BRANDING.md). Third-party dependencies retain their own terms. Future tools remain concepts and will have their license scope stated when implemented.
