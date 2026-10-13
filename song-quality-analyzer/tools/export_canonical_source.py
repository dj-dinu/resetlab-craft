"""Generate or verify the exact canonical source snapshot, without grading code.

Only enhance the maintained canonical scanner. Regenerate this release asset
after its self-test and relevant regressions pass; never edit the copy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DESTINATION = PROJECT / "canonical"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scanner", type=Path, help="The sole maintained canonical source")
    parser.add_argument("--expected-sha256", help="Reviewed SHA-256 of that source")
    parser.add_argument("--check", action="store_true", help="Verify the existing generated snapshot")
    args = parser.parse_args()
    target = DESTINATION / "scan_quality.py"
    manifest_path = DESTINATION / "manifest.json"
    if args.check:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("file") != "scan_quality.py" or digest(target.read_bytes()) != manifest.get("sha256"):
            raise SystemExit("Canonical source snapshot verification failed.")
        if args.scanner and args.scanner.read_bytes() != target.read_bytes():
            raise SystemExit("Snapshot differs from the maintained canonical source.")
    else:
        if not args.scanner or not args.expected_sha256:
            parser.error("Generation requires --scanner and its reviewed --expected-sha256.")
        source = args.scanner.read_bytes()
        if digest(source) != args.expected_sha256:
            raise SystemExit("Maintained source differs from the reviewed SHA-256; validate before exporting.")
        DESTINATION.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source)
        if target.read_bytes() != source:
            raise SystemExit("Generated source snapshot differs from the maintained source.")
        manifest = {"file": "scan_quality.py", "sha256": digest(source),
                    "maintenance": "Generated exact source asset; do not edit independently.",
                    "grading_mode": "--full-spectrum", "license": "GPL-3.0-only"}
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verified": True, "sha256": manifest["sha256"]}))


if __name__ == "__main__":
    main()
