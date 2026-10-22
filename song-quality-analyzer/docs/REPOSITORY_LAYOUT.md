# Repository layout

ResetLab Craft is the suite. Bandprism is the implemented product in
`song-quality-analyzer/`; other tool names remain concepts.

```text
resetlab-craft/
├── README.md                     Suite, platform status and download links
├── LICENSE                       Suite source license scope
├── .github/workflows/            Native qualification workflows
├── research/                     Product research; no private test data
└── song-quality-analyzer/
    ├── README.md                 Bandprism entry point
    ├── run_desktop.py            Native desktop launcher and frozen worker
    ├── run_local.py              Developer browser launcher
    ├── Start Desktop Windows.cmd
    ├── Start Desktop macOS.command
    ├── music_library_lab/        Shared app, local server and interface
    ├── canonical/                Generated, hash-verified canonical engine
    ├── tests/                    App, security, sorting and Mac bridge tests
    ├── tools/                    Builds, fixtures and validation orchestration
    ├── requirements*.txt         Runtime/desktop/build dependency groups
    └── docs/
        ├── README.md             Documentation index
        ├── INSTALLATION.md       Platform selector and developer setup
        ├── platforms/
        │   ├── README.md         Platform status table
        │   ├── windows/          Windows install/beta guide
        │   ├── macos/            Mac status, testing, volunteer and release plan
        │   └── linux/            Deferred support status
        └── ...                   Shared rules, privacy, formats and roadmap
```

The old flat platform guide filenames forward to their current folders so
existing links still work. Launchers, shared code, the canonical scanner and
workflow working directories stay in their established locations. This avoids
separate Windows/Mac graders or duplicate copies of shared application code.

## Generated and private files

These are local working directories, not source folders or public downloads:

| Location | Purpose | Git status |
| --- | --- | --- |
| `.codex-remote-attachments/` at the suite root | User-supplied screenshots and attachments | Ignored; may contain private paths/music names |
| `.work/` at either root | Checkpoints, reports, synthetic fixtures and dependency materials | Ignored |
| `song-quality-analyzer/dist/` | Platform-specific built app folders | Ignored |
| `song-quality-analyzer/build/` | Build intermediates | Ignored |
| `song-quality-analyzer/.localdeps/`, `.venv/` | Local dependencies/runtime | Ignored |
| `song-quality-analyzer/local_settings.json` | Machine-specific scanner/decoder paths | Ignored |

Keep installed Windows and Mac archives as GitHub Release assets, with names
such as `Bandprism-<version>-windows-x64.zip` and
`Bandprism-<version>-macos-arm64.zip`. Supply matching source, dependency
sources/notices and checksums beside each published version. Those are naming
conventions for releases, not claims that every package is already available.

Never stage an entire private workspace. Review an explicit source-file list;
exclude music, local reports, session tokens, settings, diagnostic logs,
credentials and screenshots. The only maintained grading source is the
canonical scanner described in [canonical/README](../canonical/README.md).
