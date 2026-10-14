# Generated canonical source

`scan_quality.py` is a byte-for-byte export of the sole maintained scanner,
not an independently developed classifier. `manifest.json` records its hash.
The app uses this snapshot when no developer override is configured.

Verify the snapshot from the app directory:

    python tools/export_canonical_source.py --check
    python canonical/scan_quality.py --self-test

Maintainers must enhance the original canonical tool in place, run its self-test
and relevant real-track regressions, then regenerate this asset using
`tools/export_canonical_source.py --scanner PATH --expected-sha256 REVIEWED_SHA`.
Never edit the generated copy or change thresholds in the UI/adapter.
Use `--full-spectrum` for all application grading. Bitrate is informational;
HQ requires at least 40% of the whole decoded duration at or above 20 kHz.

No native decoder binaries, private regression inputs, or music are included.
Project-owned scanner source is covered by the app's GPLv3-only license;
third-party decoder libraries retain their own terms.
