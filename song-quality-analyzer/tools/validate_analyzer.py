"""Read-only integration validation against canonical regression references."""
from pathlib import Path
import json
import sys
import uuid

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / ".localdeps"))

from music_library_lab.analyzer import analyze_tracks, file_hash
from music_library_lab.demo import create_demo
from music_library_lab.inventory import scan_library


def main():
    settings = json.loads((PROJECT / "local_settings.json").read_text(encoding="utf-8"))
    reference = json.loads((PROJECT / ".work/scanner-portability-validation.json").read_text(encoding="utf-8"))
    expected = reference["records"]
    paths = [Path(r["path"]) for r in expected]
    # Only a common root is used; no song is copied into the project.
    import os
    root = Path(os.path.commonpath([str(p.parent) for p in paths]))
    tracks = [{"id": str(i), "source_path": str(p.relative_to(root)), "enabled": True,
               "original_sha256": file_hash(p)} for i, p in enumerate(paths)]
    result = analyze_tracks(Path(settings["scanner_path"]), root, tracks,
                            PROJECT / ".work" / ("integration-" + uuid.uuid4().hex), settings["decoder_path"])
    lookup = {str(Path(r["path"]).resolve()).casefold(): r for r in result["records"]}
    checks = []
    for old in expected:
        r = lookup[str(Path(old["path"]).resolve()).casefold()]
        for key in ("quality", "coverage_20khz", "coverage_15khz", "duration_seconds"):
            assert r[key] == old[key], (key, r[key], old[key])
        assert r["source_sha256"] == old["source_sha256"]
        assert r["spectrogram"] and r["time_bins"]
        checks.append({"quality": r["quality"], "source_unchanged": True,
                       "exact_metrics_match": True, "spectrogram": True})
    demo = create_demo(PROJECT / ".demo-library")
    inventory = scan_library(str(demo))
    demo_before = {t["id"]: file_hash(demo / t["source_path"]) for t in inventory["tracks"]}
    demo_result = analyze_tracks(Path(settings["scanner_path"]), demo, inventory["tracks"],
                                 PROJECT / ".work" / ("demo-validation-" + uuid.uuid4().hex), settings["decoder_path"])
    assert demo_result["total"] == 2 and demo_result["analyzed"] == 2
    assert all(r["quality"] == "LQ" for r in demo_result["records"])
    assert any("(HQ)" in r["source_path"] for r in demo_result["records"])
    assert all(file_hash(demo / t["source_path"]) == demo_before[t["id"]] for t in inventory["tracks"])
    payload = {"real_track_regressions": checks, "official_decoder": "mpg123 1.33.7 x86-64",
               "demo_hq_label_reanalyzed": True, "demo_files_unchanged": True,
               "macos_native_test": "pending"}
    (PROJECT / ".work/analyzer-validation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
