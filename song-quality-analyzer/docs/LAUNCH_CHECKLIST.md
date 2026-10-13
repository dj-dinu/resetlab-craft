# First-launch checklist

Aim for a trustworthy, simple first experience. Passing unit tests alone does not qualify a public release.

## Automated/local edge cases

| Case | Expected result / evidence |
| --- | --- |
| Low bitrate with high-frequency coverage, lossless filtered audio, existing HQ label | Canonical spectral rules decide the grade; filenames/bitrate do not. Covered by format/real regressions. |
| Silence, quiet sections, short tails, boundary just below 30%, phase-inverted stereo | Full duration and reviewed mean channel-power policy retained. Covered by synthetic checks. |
| Four-minute header with one-minute decoded audio / valid short edit | First ungraded integrity error; second analyzed normally. Covered by duration and packaged-worker checks. |
| Unsupported codec/container, video, multiple streams, DRM markers, corrupted/truncated files | No completed grade; actionable failure. Tested variants are narrower than every possible profile. |
| Large folder / more than 50 tracks / partial inventory / multi-batch summary | Caps and partial labels visible; selection/filter/score/report behavior remains clear. Browser 100-track check passed. |
| Cancel and retry, close during work, changed input file | Cancellation and hash boundaries covered locally; actual native close/reaping still pending. |
| Unusual filenames, Unicode, long paths, collisions, symlinks/junctions | Path/selection boundaries covered; POSIX-native name case skipped on Windows and needs native execution. |
| Malicious metadata / private diagnostics / foreign Host or Origin / invalid token | Render as text; deny unauthorized requests; exported report omits absolute/cache paths. New security checks cover malformed token and generic static failures. |
| Internal decoder URL / disguised playlist | No network fetch with restricted decoder; test server receives zero requests. |
| Evidence/resource limit / repeated jobs / reduced motion | No partial grade; graph availability explained; memory retention bounded; scrolling behavior checked. Six owned-cache safety tests and 10,001-candidate/20-minute/backend-shutdown checks pass. Broad native/I/O/peak-resource qualification remains open. |

## Native platform checks still required

For Windows and each advertised Mac architecture, use a machine without developer Python or DJ applications:

1. Install/open the actual package as a normal user; document prerequisites and platform messages.
2. Choose a folder through the native dialog; run all advertised codec/profile fixtures and verify whole-file hashes.
3. Save a report through the native dialog; cancel the dialog and test an existing destination without overwriting it.
4. Cancel folder reading and analysis, retry, close during each operation, and confirm child decoders/loopback server exit.
5. Disconnect internet and complete a locally stored folder scan; capture outbound traffic with a trusted OS tool and check app/runtime behavior.
6. Test slow/removable/cloud/network storage, permissions, missing/moved files, low disk space, multi-hour content and repeated large runs; measure peak CPU/RAM/disk and cache growth.
7. Check keyboard-only use, reduced motion, both appearances, screen-reader labels and actual mouse/trackpad scrolling.

No Mac native test has occurred on the Windows development machine. Linux is a later qualification target, not an advertised supported platform.

## Small user beta before launch

Observe DJs/producers choosing a folder, understanding a partial score and ungraded error, finding evidence and saving a report without coaching. Record where they hesitate and fix the workflow. Confirm that they understand spectral coverage as one piece of evidence rather than a fidelity certificate.

Release only reviewed source/synthetic fixtures/permitted dependencies. Exclude local settings, tokens, real music, private caches, patch helpers and screenshots containing private paths. Resolve license/signing/name/handle checks and prepare a private security-reporting channel. GitHub remains unpublished until this gate is satisfied.
