# Native beta test guide

Use this for the actual packaged Windows app and each advertised Mac architecture. The current Mac packages do not exist yet. Source/worker tests do not count as native install or dialog qualification.

## Clean installation

Use a normal user account on a machine without developer Python or DJ applications. Keep the complete Windows Bandprism folder together. Record OS/architecture, app version, package hash, installed prerequisites and any launch/security messages. Report a block or failure; do not bypass security protections to obtain a pass.

## Tasks to observe without coaching

1. Use Add music → Audio file or Music folder and confirm metadata loads automatically. Cancel the picker and confirm the prior selection remains. Test dropping ONE file and ONE folder from Explorer/Finder; native gestures and folder paths still need actual OS qualification. Unsupported items, URLs, multiple drops and drops during analysis must be refused without replacing existing results. Analyze the file and confirm only it appears and its bytes are unchanged.
2. Choose a folder with 103 candidates. Confirm selected tracks run in title A–Z order as 50, 50 and 3 automatically. Pause during a long track, wait for confirmation, refresh while the app stays open, then resume. Stop after a completed batch; confirm completed results remain, export works and Select remaining selects the unfinished tracks. Explain the score's measured coverage, then rescan and observe the reset.
3. Explain HQ/MQ/LQ, an existing HQ label, an ungraded error and the difference between spectral coverage and audible quality.
4. Find the spectrum, qualifying seconds and timeline; filter and sort A–Z/Z–A without changing selected IDs, score or evidence. Inspect the sticky progress panel, current track, processed counts and elapsed time. A long first track should remain visibly busy before the count advances.
5. Save a JSON report, cancel the save dialog, and choose an existing destination. The existing file must remain intact. Understand that export covers the latest completed batch.
6. Toggle the sun/moon button, restart, and navigate with the keyboard. Test actual mouse/trackpad scrolling and reduced motion.
7. Resize the window and try half-screen placement (Win + Left/Right on Windows). Check at the machine's usual display scaling, and again at 125% or 150% when available. The minimum is 420 × 360 logical pixels. Check choose/analyze/filter/sort/save and Pause/Resume/Stop controls, long titles and expanded evidence; the results table can scroll horizontally inside its panel. Record the screen resolution, scale and any window-size limit. Browser viewport checks do not qualify native OS snapping.

Record completion, hesitation, confusing wording and failures. Ask the tester what they expected before explaining the feature. Use a small DJ/producer beta first; add features only when repeated feedback establishes a need.

## Safety, storage and shutdown

Use synthetic or shareable fixtures first. Hash the complete files before and after success, error and cancellation; include tags/artwork. Do not share private music or diagnostics publicly.

- Cancel inventory and analysis, retry, and close the actual window during each operation. Confirm that the server and decoder child processes exit. Backend shutdown with a real child passes locally; actual window-close behavior still needs this test.
- Disconnect internet and analyze files fully stored on disk. Capture traffic with a trusted OS tool and distinguish app requests from unrelated OS/vendor traffic. Folder/file metadata must not be uploaded by the app.
- Use a test USB drive and removable copies, then disconnect it during work. Test permissions, missing/moved files, low disk space, large/long content and sleep/resume. Failures must remain ungraded and preserve originals.
- Run repeated jobs. New marked caches retain three finished batches; active, legacy and unexpected data remain protected. Export reports you want to keep. Measure disk growth and peak CPU/RAM; retained-batch counts alone are not a byte cap.

## Acceptance before public launch

All advertised install/dialog/format/shutdown tasks must pass on each claimed platform. Fix preservation/privacy failures before launch. Resolve project/native dependency licensing, matching sources/notices, native security updates and final release-content scrub. Keep platform claims aligned with actual evidence and document known limits in the README.

Record results in [the qualification record](LOCAL_TEST_RESULTS.md); use [the launch checklist](LAUNCH_CHECKLIST.md). A private GitHub source preview exists; this guide does not qualify a public release or authorize distributing binaries.
