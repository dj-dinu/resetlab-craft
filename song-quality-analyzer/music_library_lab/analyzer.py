"""Run the one canonical scanner; this module contains no quality classifier."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import zipfile
from collections import deque
# Preload the Windows DLL runtime before HTTP/analysis threads start. Other
# platforms retain their established lazy import path.
if os.name == "nt":
    import numpy as _numpy_runtime
from .inventory import music_source, safe_path as _safe_path, regular_file as _regular
from .inventory import hash_file, SUPPORTED_EXTENSIONS

MAX_TRACKS_PER_RUN = 50


class AnalysisError(ValueError):
    pass


def analysis_folder(source: Path, selected: list[dict]) -> Path:
    source = music_source(str(source))
    if source.is_file():
        if len(selected) != 1 or selected[0].get("source_path") != source.name:
            raise AnalysisError("Select only the audio file that was read. Read a folder to analyze other tracks.")
        return source.parent
    return source


def file_hash(path: Path) -> str:
    return hash_file(path)


def spectrogram_data(record: dict) -> dict | None:
    """Downsample scanner-owned power arrays for display, never for grading."""
    if not record.get("spectrum_file"):
        return None
    import numpy as np

    with zipfile.ZipFile(record["spectrum_file"]) as archive:
        if sum(member.file_size for member in archive.infolist()) > 128 * 1024 * 1024:
            record["spectrogram_note"] = "This track's spectrum exceeds the local preview memory budget. Its full-duration grade is still reported."
            return None
    with np.load(record["spectrum_file"], allow_pickle=False) as data:
        power = data["power"]
        rate = int(data["sample_rate"])
        if power.ndim != 2 or not len(power):
            return None
        if "bin_start_seconds" in data and "bin_duration_seconds" in data:
            starts = data["bin_start_seconds"]
            durations = data["bin_duration_seconds"]
            if len(starts) != len(power) or len(durations) != len(power):
                raise AnalysisError("Spectrum timing does not match its power arrays.")
        else:
            bins = record.get("time_bins", [])
            represented = [item for item in bins if item["seconds"] * rate >= 2048]
            if len(represented) != len(power):
                raise AnalysisError("Legacy spectrum timing cannot be verified.")
            starts = np.array([item["start_seconds"] for item in represented])
            durations = np.array([item["seconds"] for item in represented])
        if (not np.isfinite(starts).all() or not np.isfinite(durations).all()
                or (starts < 0).any() or (durations <= 0).any()):
            raise AnalysisError("Spectrum timing is invalid.")
        # Max pooling retains visible high-frequency energy in the overview.
        ts = np.array_split(np.arange(len(power)), min(120, len(power)))
        fs = np.array_split(np.arange(power.shape[1]), min(128, power.shape[1]))
        time_reduced = np.stack([power[indices].max(axis=0) for indices in ts])
        reduced = np.stack([time_reduced[:, indices].max(axis=1) for indices in fs], axis=1)
        db = np.clip(10 * np.log10(np.maximum(reduced, 1e-15)), -110, 0)
        return {"width": len(ts), "height": len(fs), "values": db.round(1).ravel().tolist(),
                "max_frequency": rate / 2, "duration_seconds": record["duration_seconds"],
                "start_seconds": [float(starts[indices[0]]) for indices in ts],
                "seconds": [float(starts[indices[-1]] + durations[indices[-1]] - starts[indices[0]]) for indices in ts],
                "min_db": -110, "max_db": 0,
                "description": "Max-pooled overview of canonical half-second power spectra; display only."}


def _analyze_tracks(scanner: Path, root: Path, tracks: list[dict], output_dir: Path,
                    decoder: str = "", progress=None, cancel=None, paused=None) -> dict:
    if not scanner.is_file():
        raise AnalysisError("Configure the canonical scan_quality.py path before analyzing.")
    selected = [t for t in tracks if t.get("enabled", True)]
    if not selected:
        raise AnalysisError("Select at least one track.")
    root = analysis_folder(root, selected)
    output_dir.mkdir(parents=True, exist_ok=False)
    files = []
    for track in selected:
        path = _safe_path(root, track["source_path"])
        _regular(path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise AnalysisError("A selected file is not a supported audio-format candidate.")
        current = file_hash(path)
        if track.get("original_sha256") and current != track["original_sha256"]:
            raise AnalysisError("A selected file changed since inventory. Scan the folder again.")
        files.append((track, path, current))

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    dependencies = Path(__file__).resolve().parent.parent / ".localdeps"
    if dependencies.is_dir() and not getattr(sys, "frozen", False):
        env["PYTHONPATH"] = os.pathsep.join([str(dependencies), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    if decoder:
        env["SONG_AUDIT_MPG123_PATH"] = decoder
    # Keep the command line safely below Windows' limit, even for long paths.
    batches = []
    batch = []
    length = 0
    for entry in files:
        size = len(str(entry[1])) + 4
        if batch and (length + size > 18000 or len(batch) >= 80):
            batches.append(batch)
            batch, length = [], 0
        batch.append(entry)
        length += size
    if batch:
        batches.append(batch)

    output = []
    method = ""
    done = 0
    scanner_sha256 = file_hash(scanner)
    for index, batch in enumerate(batches):
        if cancel and cancel():
            raise InterruptedError("Analysis cancelled. Song files were not changed.")
        if file_hash(scanner) != scanner_sha256:
            raise AnalysisError("The canonical engine changed during this run. Discard results and retry with a stable engine.")
        destination = output_dir / f"batch-{index}.json"
        spectra = output_dir / f"spectra-{index}"
        spectra.mkdir()
        command = ([sys.executable, "--scanner-worker", "--full-spectrum"] if getattr(sys, "frozen", False)
                   else [sys.executable, "-B", str(scanner), "--full-spectrum"])
        command += [str(p) for _, p, _ in batch]
        command += ["--keep-input-order"]
        if paused is not None:
            command += ["--interactive-control"]
        command += ["--output", str(destination), "--spectra-dir", str(spectra)]
        startup = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        proc = subprocess.Popen(command, stdin=subprocess.PIPE if paused is not None else subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", env=env, **startup)
        stopped = threading.Event()

        def monitor():
            sent_pause = False
            while not stopped.is_set():
                if cancel and cancel() and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    return
                if paused is not None and proc.poll() is None:
                    wanted = bool(paused())
                    if wanted != sent_pause:
                        try:
                            proc.stdin.write(json.dumps({"action": "pause" if wanted else "resume"}) + "\n")
                            proc.stdin.flush()
                            sent_pause = wanted
                        except (BrokenPipeError, OSError, ValueError):
                            return
                if stopped.wait(.1):
                    return

        watcher = threading.Thread(target=monitor, daemon=True)
        watcher.start()
        log = deque(maxlen=20)
        try:
            if progress:
                progress({"done": done, "total": len(files),
                          "message": f"Measuring {files[done][1].name} · track {done + 1} of {len(files)}"})
            for line in proc.stdout:
                log.append(line.rstrip())
                if line.startswith("DONE ") and proc.stdin is not None:
                    stopped.set()
                    proc.stdin.close()
                elif line.startswith("CONTROL ") and progress:
                    control = json.loads(line[8:])
                    progress({"done": done, "total": len(files), "paused": bool(control.get("paused")),
                              "message": "Analysis paused. Resume to continue this track." if control.get("paused") else "Resuming full-track analysis…"})
                elif line.startswith("PROGRESS "):
                    done += 1
                    if progress:
                        progress({"done": done, "total": len(files),
                                  "message": (f"Measuring {files[done][1].name} · track {done + 1} of {len(files)}"
                                              if done < len(files) else "Decoded the selected tracks. Checking the results…")})
            status = proc.wait()
        finally:
            stopped.set()
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
            watcher.join(timeout=1)
            if proc.stdin is not None:
                proc.stdin.close()
            proc.stdout.close()
        if cancel and cancel():
            raise InterruptedError("Analysis cancelled. Song files were not changed.")
        if not destination.is_file():
            raise AnalysisError("The canonical scanner did not produce a report. " + "\n".join(list(log)[-5:]))
        if destination.stat().st_size > 64 * 1024 * 1024:
            raise AnalysisError("The report exceeds this local alpha's memory budget.")
        report = json.loads(destination.read_text(encoding="utf-8"))
        if method and report["method"] != method:
            raise AnalysisError("The scanner returned different measurement methods in one run. Discard results and retry.")
        method = report["method"]
        lookup = {os.path.normcase(str(path.resolve())): (track, path, expected) for track, path, expected in batch}
        seen = set()
        for record in report["records"]:
            key = os.path.normcase(str(Path(record["path"]).resolve()))
            if key not in lookup or key in seen:
                raise AnalysisError("Scanner output contains an unexpected or duplicate input.")
            seen.add(key)
            track, path, expected = lookup[key]
            if file_hash(path) != expected:
                raise AnalysisError("An input changed during analysis; discard this result and rescan.")
            row = dict(record, id=track["id"], source_path=track["source_path"], source_sha256=expected,
                       artist=track.get("artist", ""), title=track.get("title", path.stem))
            for field in ("codec", "codec_profile", "container", "channels", "sample_rate", "bit_depth", "encoded_bitrate"):
                if field not in row and field in track:
                    row[field] = track[field]
            if record.get("spectrum_file") and not Path(record["spectrum_file"]).resolve().is_relative_to(output_dir.resolve()):
                raise AnalysisError("Spectrum evidence is outside the analysis output folder.")
            row["spectrogram"] = spectrogram_data(record)
            if row["spectrogram"] is None and record.get("spectrum_evidence_unavailable_reason"):
                row["spectrogram_note"] = record["spectrum_evidence_unavailable_reason"]
            if row.get("status") != "analyzed":
                row["quality"] = None
                row["error"] = row.get("reason", "The decoder could not analyze this file.")
            output.append(row)
        if len(report["records"]) != len(batch) or status not in (0, 1):
            raise AnalysisError("The scanner did not finish the selected batch.")
    if file_hash(scanner) != scanner_sha256:
        raise AnalysisError("The canonical engine changed during this run. Discard results and retry with a stable engine.")
    combined = {"method": method, "scanner_sha256": scanner_sha256, "records": output,
                "counts": {grade: sum(r.get("quality") == grade for r in output) for grade in ("HQ", "MQ", "LQ")},
                "analyzed": sum(r.get("status") == "analyzed" for r in output),
                "errors": sum(r.get("status") != "analyzed" for r in output), "total": len(output),
                "audio_files_modified": False}
    (output_dir / "report.json").write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    return combined


def analyze_tracks(scanner: Path, root: Path, tracks: list[dict], output_dir: Path,
                   decoder: str = "", progress=None, cancel=None, paused=None) -> dict:
    """Verify all selected inputs on every exit, including failure/cancellation."""
    if not scanner.is_file():
        raise AnalysisError("Configure the canonical scan_quality.py path before analyzing.")
    selected = [t for t in tracks if t.get("enabled", True)]
    if not selected:
        raise AnalysisError("Select at least one track.")
    if len(selected) > MAX_TRACKS_PER_RUN:
        raise AnalysisError(f"This local alpha supports up to {MAX_TRACKS_PER_RUN} selected tracks per run.")
    source = root
    root = analysis_folder(source, selected)
    baselines = {}
    for track in selected:
        path = _safe_path(root, track["source_path"])
        _regular(path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise AnalysisError("A selected file is not a supported audio-format candidate.")
        key = os.path.normcase(str(path))
        if key in baselines:
            raise AnalysisError("The same input was selected more than once.")
        if progress:
            progress({"done": 0, "total": len(selected), "message": "Verifying selected source files"})
        baselines[key] = (path, hash_file(path, cancel=cancel))
    try:
        if paused is None:
            return _analyze_tracks(scanner, source, selected, output_dir, decoder, progress, cancel)
        return _analyze_tracks(scanner, source, selected, output_dir, decoder, progress, cancel, paused)
    finally:
        if progress:
            progress({"done": len(selected), "total": len(selected), "message": "Verifying that source files remain unchanged"})
        changed = []
        for path, expected in baselines.values():
            try:
                if file_hash(path) != expected:
                    changed.append(str(path))
            except (OSError, ValueError):
                changed.append(str(path))
        if changed:
            raise AnalysisError("An input changed during this run. Results cannot verify unchanged files; rescan the folder.")
