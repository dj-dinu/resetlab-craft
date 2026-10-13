# Native beta test guide

Use this for the actual packaged Windows app and each advertised Mac architecture. The current Mac packages do not exist yet. Source/worker tests do not count as native install or dialog qualification.

## Clean installation

Use a normal user account on a machine without developer Python or DJ applications. Keep the complete Windows Spectracraft folder together. Record OS/architecture, app version, package hash, installed prerequisites and any launch/security messages. Report a block or failure; do not bypass security protections to obtain a pass.

## Tasks to observe without coaching

1. Choose one file, click Read folder or file, and analyze it. Confirm that only that file appears and its original bytes are unchanged.
2. Choose a folder with more than 50 candidates. Find the next batch and explain whether the displayed score covers the whole folder. Rescan and observe the reset.
3. Explain HQ/MQ/LQ, an existing HQ label, an ungraded error and the difference between spectral coverage and audible quality.
4. Find the spectrum, qualifying seconds and timeline; filter errors without changing selection or score.
5. Save a JSON report, cancel the save dialog, and choose an existing destination. The existing file must remain intact. Understand that export covers the latest completed batch.
6. Toggle the sun/moon button, restart, and navigate with the keyboard. Test actual mouse/trackpad scrolling and reduced motion.

Record completion, hesitation, confusing wording and failures. Ask the tester what they expected before explaining the feature. Use a small DJ/producer beta first; add features only when repeated feedback establishes a need.

## Safety, storage and shutdown

Use synthetic or shareable fixtures first. Hash the complete files before and after success, error and cancellation; include tags/artwork. Do not share private music or diagnostics publicly.

- Cancel inventory and analysis, retry, and close the actual window during each operation. Confirm that the server and decoder child processes exit. Backend shutdown with a real child passes locally; actual window-close behavior still needs this test.
- Disconnect internet and analyze files fully stored on disk. Capture traffic with a trusted OS tool and distinguish app requests from unrelated OS/vendor traffic. Folder/file metadata must not be uploaded by the app.
- Use a test USB drive and removable copies, then disconnect it during work. Test permissions, missing/moved files, low disk space, large/long content and sleep/resume. Failures must remain ungraded and preserve originals.
- Run repeated jobs. New marked caches retain three finished jobs; active, legacy and unexpected data remain protected. Export reports you want to keep. Measure disk growth and peak CPU/RAM; retained-job counts alone are not a byte cap.

## Acceptance before public launch

All advertised install/dialog/format/shutdown tasks must pass on each claimed platform. Fix preservation/privacy failures before launch. Resolve project/native dependency licensing, matching sources/notices, native security updates and final release-content scrub. Keep platform claims aligned with actual evidence and document known limits in the README.

Record results in [the qualification record](LOCAL_TEST_RESULTS.md); use [the launch checklist](LAUNCH_CHECKLIST.md). No beta messages, public repository or release have been sent or created by preparing this guide.
