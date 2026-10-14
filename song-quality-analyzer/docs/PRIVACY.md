# Privacy and local data

Spectracraft has no analytics, telemetry, accounts, advertising, remote music service, automatic uploader or automatic updater. The app code calls its own loopback API only. Interface scripts, fonts, images and styles are local. Native platform/browser components and dependency installation need their own platform qualification; this is not a promise that every OS service makes zero network requests.

## What the app reads

Only the user-selected folder or audio file is inventoried. A file selection does not enumerate or read its neighboring files. The app reads filenames, embedded artist/title/format metadata, file hashes and decoded audio samples to measure full tracks. It skips symbolic links/junctions and restricts analysis to selected ordinary files from the inventory. Existing music, tags, artwork and DJ collection data are not modified.

The canonical PyAV decoder permits file protocols and supported audio containers only. A direct decoder URL test made one loopback request before hardening and zero after it. The app's folder boundary already required local ordinary files; this restriction hardens the decoder itself. The tested disguised playlist was also rejected with zero requests. Local files on cloud/network mounts may be fetched by the OS/provider when the user selects them; use fully local files for offline operation.

## What stays on this computer

Current-session inventories, grades and evidence are held in memory. Private JSON diagnostics and spectrum arrays can remain on disk; appearance settings are saved locally. These are local processing records, not remotely collected telemetry. The caches contain metadata and derived spectral evidence, not copies of the selected song audio.

Development records/settings are under .work in the project. The native build keeps the established cache location: %LOCALAPPDATA%/SongQualityAnalyzer on Windows, or ~/Library/Caches/SongQualityAnalyzer on macOS. The historical directory name is retained to avoid losing data. New analysis records use analysis-cache-v1 beneath that location and retain the latest three finished, explicitly owned batch caches. Cleanup accepts only recognized generated JSON/NPZ content and ownership markers; music, exported reports, active jobs, legacy/unmarked folders, links/hard links and unexpected content are excluded. Interrupted/unrecognized/legacy caches may remain; there is no blanket disk-size cap. Existing private records are preserved.

## Reports and session access

JSON export/native save happens only when requested. Export strips absolute machine/cache paths and free-form decoder diagnostic strings. Relative filenames, artist/title and measurements may still identify music or edits; review before sharing. No report is automatically sent anywhere.

The server binds only to 127.0.0.1. Private API routes require a random per-session token and reject foreign origins/hosts. The token is delivered in the launch URL fragment, removed from the displayed URL and retained in browser session storage; it is not placed in request URLs. A no-referrer policy and no-store responses reduce incidental exposure. Native windows use private browser storage. Local same-user malware is outside this application's security boundary.

Keep launcher session links, local settings, private caches and real music out of GitHub. Public source packages must be scrubbed and dependency/runtime network behavior checked on clean native machines before release.
