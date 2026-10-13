"""Local MP3 preview/apply/restore engine. Never decodes or re-encodes audio.

Complete originals, including ID3/artwork, are the restore source of truth.
An interrupted apply can be restored from its durable per-file journal.
Spectral grades must be provided by the separate canonical scanner adapter.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TCON, TXXX, TMOO


GROUPS = (
    "Deep & Soulful House", "Disco, Funky & Classic House",
    "Tech & Progressive House", "Hip-Hop", "Chill & Melodic House",
    "Chill & Melodic Electronic", "Trance & Hard Dance",
)
VOCAL_BUCKETS = ("English", "Instrumental", "Instrumental & Vocal Samples")
DEFAULT_BUCKET = "Instrumental & Vocal Samples"
RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$")
QUALITY_SUFFIX = re.compile(r"\s*[\[(](HQ|MQ|LQ)[\])]\s*$", re.I)
BAD_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)
PLAYLIST_EXTENSIONS = {".m3u", ".m3u8", ".pls"}


class CoreError(ValueError):
    """A safe refusal or recoverable transaction failure."""


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _linked(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _root(value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise CoreError("Choose an existing music folder.")
    given = Path(value).absolute()
    if not given.is_dir():
        raise CoreError("Music folder does not exist.")
    if any(_linked(p) for p in (given, *given.parents)):
        raise CoreError("Symbolic links and junctions are not supported as music roots.")
    root = given.resolve()
    if root == Path(root.anchor) or root == Path.home().resolve():
        raise CoreError("Choose a music subfolder, rather than a filesystem or home root.")
    if root.name.casefold() == "_organization":
        raise CoreError("Audit records cannot be selected as the music folder.")
    return root


def _identity(root: Path) -> list[int]:
    info = root.stat()
    return [info.st_dev, info.st_ino]


def _relative(value: str, *, audit: bool = False) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise CoreError("Invalid relative path.")
    if PureWindowsPath(value).is_absolute() or PureWindowsPath(value).drive:
        raise CoreError("Absolute and drive-qualified track paths are not allowed.")
    norm = value.replace("\\", "/")
    parts = norm.split("/")
    if norm.startswith("/") or any(p in {"", ".", ".."} for p in parts):
        raise CoreError("Unsafe relative path: " + value)
    for part in parts:
        _valid_component(part)
    if not audit and parts[0].casefold() == "_organization":
        raise CoreError("Music changes cannot target audit records.")
    return str(PurePosixPath(norm))


def _valid_component(value: str) -> None:
    if not value or BAD_FILENAME.search(value) or value.rstrip(" .") != value:
        raise CoreError("Invalid portable folder or file name: " + repr(value))
    if RESERVED.match(value) or len(value) > 240:
        raise CoreError("Reserved or overly long folder/file name: " + repr(value))


def _safe_path(root: Path, value: str, *, audit: bool = False) -> Path:
    relative = _relative(value, audit=audit)
    path = root.joinpath(*relative.split("/"))
    for part in (path, *path.parents):
        if part == root:
            break
        if part.exists() or part.is_symlink():
            if _linked(part):
                raise CoreError("A path traverses a symbolic link or junction: " + relative)
    if not path.resolve().is_relative_to(root):
        raise CoreError("A path leaves the selected music folder.")
    return path


def _regular(path: Path) -> None:
    info = path.stat(follow_symlinks=False)
    if _linked(path) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise CoreError("Only ordinary files with one hard link are supported: " + path.name)


def _walk(root: Path):
    for parent, dirs, files in os.walk(root, followlinks=False):
        directory = Path(parent)
        dirs[:] = sorted(d for d in dirs if d.casefold() != "_organization" and not _linked(directory / d))
        for name in sorted(files):
            yield directory / name


def _audio_hash(path: Path) -> str:
    """Hash the exact encoded payload, excluding leading ID3v2 and ID3v1.

    Other trailing bytes, including APE tags, stay in this hash. Any unintended
    edit to them therefore blocks a transaction as well as an audio edit.
    """
    size = path.stat().st_size
    start, end = 0, size
    with path.open("rb") as stream:
        header = stream.read(10)
        if header[:3] == b"ID3":
            if len(header) != 10 or any(x & 0x80 for x in header[6:10]):
                raise CoreError("Malformed ID3 header: " + path.name)
            tag_size = 0
            for byte in header[6:10]:
                tag_size = (tag_size << 7) | byte
            start = 10 + tag_size
            if header[3] == 4 and header[5] & 0x10:
                start += 10
        if size >= 128:
            stream.seek(size - 128)
            if stream.read(3) == b"TAG":
                end -= 128
        if start >= end:
            raise CoreError("The file has no encoded audio payload: " + path.name)
        stream.seek(start)
        digest = hashlib.sha256()
        remaining = end - start
        while remaining:
            block = stream.read(min(1024 * 1024, remaining))
            if not block:
                raise CoreError("Unexpected end of MP3 payload.")
            digest.update(block)
            remaining -= len(block)
    return digest.hexdigest()


def _inspect(path: Path) -> tuple[ID3, dict]:
    _regular(path)
    try:
        media = MP3(path)
        if media.info.length <= 0 or media.info.sample_rate <= 0:
            raise CoreError("No readable MPEG audio frames: " + path.name)
        try:
            tags = ID3(path, translate=False)
        except ID3NoHeaderError:
            tags = ID3()
        snapshot = {
            "id3_version": list(tags.version),
            "artist": _text(tags, "TPE1"), "title": _text(tags, "TIT2"),
            "genre": _text(tags, "TCON"), "moods": _moods(tags),
            "frames": {key: hashlib.sha256(repr(frame).encode("utf-8")).hexdigest()
                       for key, frame in sorted(tags.items())},
            "artwork": {frame.HashKey: hashlib.sha256(frame.data).hexdigest()
                        for frame in tags.getall("APIC")},
            "sample_rate": media.info.sample_rate,
            "duration_seconds": media.info.length,
            "encoded_bitrate": media.info.bitrate,
        }
        return tags, snapshot
    except CoreError:
        raise
    except Exception as exc:
        raise CoreError("Unreadable MP3: " + path.name + " (" + str(exc) + ")") from exc


def _text(tags: ID3, key: str) -> str:
    frame = tags.get(key)
    return "; ".join(str(x) for x in frame.text) if frame and hasattr(frame, "text") else ""


def _moods(tags: ID3) -> str:
    return _text(tags, "TMOO") or _text(tags, "TXXX:MOOD") or _text(tags, "TXXX:Mood")


def _quality(tags: ID3, title: str, filename: str) -> str:
    for text in (title, Path(filename).stem):
        match = QUALITY_SUFFIX.search(text)
        if match:
            return match.group(1).upper()
    value = _text(tags, "TXXX:Quality") or _text(tags, "TXXX:QUALITY")
    return value.upper() if value.upper() in {"HQ", "MQ", "LQ"} else ""


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("_", " ")).strip()


def _title(value: str, artist: str, quality: str) -> str:
    value = _clean_text(value)
    if value.lower().endswith(".mp3"):
        value = value[:-4].rstrip()
    prefix = artist + " - "
    if artist and value.casefold().startswith(prefix.casefold()):
        value = value[len(prefix):].strip()
    value = QUALITY_SUFFIX.sub("", value).strip()
    return value + (" (" + quality + ")" if quality else "")


def _filename(value: str) -> str:
    value = BAD_FILENAME.sub("-", value).strip(" .")
    value = re.sub(r"\s+", " ", value)
    _valid_component(value)
    return value


def _group(genre: str, bucket: str) -> str:
    if genre in GROUPS:
        return genre
    value = genre.casefold().replace("-", " ")
    if re.search(r"\b(trance|hardstyle|hard dance)\b", value):
        return "Trance & Hard Dance"
    if re.search(r"\b(hip hop|hiphop|rap)\b", value):
        return "Hip-Hop"
    if re.search(r"\b(deep|soulful)\b", value) and "house" in value:
        return "Deep & Soulful House"
    if re.search(r"\b(disco|funky|french|classic house|nu disco)\b", value):
        return "Disco, Funky & Classic House"
    if re.search(r"\b(tech house|progressive house|indie tech)\b", value):
        return "Tech & Progressive House"
    if re.search(r"\b(melodic|organic|chill)\b", value) and "house" in value:
        return "Chill & Melodic House" if bucket == "Instrumental" else "Chill & Melodic Electronic"
    if re.search(r"\b(chill|electronica|downtempo|melodic electronic)\b", value):
        return "Chill & Melodic Electronic"
    return "Needs Review"


def scan_library(root: str) -> dict:
    """Read a library. No file, tag, playlist, or audit record is changed."""
    folder = _root(root)
    tracks, warnings = [], []
    for path in _walk(folder):
        if path.suffix.casefold() != ".mp3":
            continue
        relative = path.relative_to(folder).as_posix()
        track = {"id": hashlib.sha256(relative.encode()).hexdigest()[:20],
                 "source_path": relative, "artist": "", "title": path.stem,
                 "genre": "", "moods": "", "vocal_bucket": DEFAULT_BUCKET,
                 "group": "Needs Review", "quality": "", "enabled": False,
                 "issues": [], "evidence": []}
        try:
            _safe_path(folder, relative)
            tags, snapshot = _inspect(path)
            artist = _clean_text(snapshot["artist"])
            quality = _quality(tags, snapshot["title"], path.name)
            title = _title(snapshot["title"] or path.stem, artist, quality)
            explicit_bucket = _text(tags, "TXXX:MUSIC_LIBRARY_VOCAL_BUCKET")
            bucket = explicit_bucket or DEFAULT_BUCKET
            _valid_component(bucket)
            if not explicit_bucket:
                track["issues"].append("Vocal content is unverified; review the vocal bucket.")
            else:
                track["evidence"].append("Vocal bucket is from a previously confirmed app tag.")
            genre = snapshot["genre"]
            group = _group(genre, bucket)
            if group == "Needs Review":
                track["issues"].append("A supported broad musical group cannot be established from the genre tag.")
            if not artist:
                track["issues"].append("Missing artist tag. Enter an artist before applying.")
            if quality:
                track["evidence"].append("Existing quality label retained; no new spectral audit has been performed.")
            track.update(artist=artist, title=title, genre=genre,
                         moods=snapshot["moods"], vocal_bucket=bucket, group=group,
                         quality=quality, enabled=True,
                         original_sha256=_sha(path), audio_sha256=_audio_hash(path),
                         original_metadata=snapshot)
            if genre:
                track["evidence"].append("Musical grouping is proposed from the existing detailed genre tag.")
            if _text(tags, "TLAN"):
                track["evidence"].append("TLAN is present but does not confirm the sung/spoken language.")
        except (CoreError, OSError) as exc:
            track["issues"].append(str(exc))
        tracks.append(track)
    if not tracks:
        warnings.append("No MP3 files were found. This local prototype supports MP3 only.")
    return {"root": str(folder), "tracks": tracks, "warnings": warnings}


def _field(track: dict, key: str, *, empty: bool = True) -> str:
    value = track.get(key, "")
    if not isinstance(value, str) or len(value) > 1000 or "\x00" in value:
        raise CoreError("Invalid " + key + " field.")
    value = _clean_text(value)
    if not empty and not value:
        raise CoreError("Enter an " + key + " before applying.")
    return value


def _metadata(track: dict) -> dict:
    artist = _field(track, "artist", empty=False)
    title = _field(track, "title", empty=False)
    quality = _field(track, "quality").upper()
    if quality not in {"", "HQ", "MQ", "LQ"}:
        raise CoreError("Quality must be empty, HQ, MQ, or LQ.")
    # Canonical audit evidence is attached by the adapter; there is no bitrate rule.
    original_quality = ""
    snapshot = track.get("original_metadata", {})
    match = QUALITY_SUFFIX.search(snapshot.get("title", ""))
    if match:
        original_quality = match.group(1).upper()
    if not original_quality:
        match = QUALITY_SUFFIX.search(Path(track.get("source_path", "")).stem)
        if match:
            original_quality = match.group(1).upper()
    if quality != original_quality and quality:
        evidence = track.get("quality_evidence")
        if not isinstance(evidence, dict) or evidence.get("mode") != "full-spectrum" or evidence.get("grade") != quality:
            raise CoreError("New quality labels require a canonical full-spectrum audit result.")
        if evidence.get("source_sha256") != track.get("original_sha256"):
            raise CoreError("Quality evidence belongs to a different source file.")
    group = _field(track, "group", empty=False)
    if group not in {*GROUPS, "Needs Review"}:
        raise CoreError("Choose one of the established broad musical groups.")
    bucket = _field(track, "vocal_bucket", empty=False)
    _valid_component(bucket)
    return {"artist": artist, "title": _title(title, artist, quality),
            "genre": _field(track, "genre"), "moods": _field(track, "moods"),
            "vocal_bucket": bucket, "group": group, "quality": quality}


def preview_plan(root: str, tracks: list[dict]) -> dict:
    folder = _root(root)
    entries, warnings, seen_sources = [], [], set()
    if not isinstance(tracks, list) or len(tracks) > 100000:
        raise CoreError("Invalid track list.")
    for track in sorted(tracks, key=lambda t: str(t.get("source_path", "")).casefold()):
        selected = track.get("enabled", False) is True
        entry = {"id": track.get("id", ""), "old_path": track.get("source_path", ""),
                 "new_path": track.get("source_path", ""), "selected": selected,
                 "issues": []}
        try:
            source = _safe_path(folder, entry["old_path"])
            if source.suffix.casefold() != ".mp3":
                raise CoreError("Only MP3 files can be changed.")
            key = entry["old_path"].casefold()
            if key in seen_sources:
                raise CoreError("The same source track occurs more than once.")
            seen_sources.add(key)
            if not selected:
                entries.append(entry)
                continue
            _, snapshot = _inspect(source)
            original_sha = _sha(source)
            if track.get("original_sha256") != original_sha:
                raise CoreError("Source changed since scanning; scan the folder again.")
            metadata = _metadata({**track, "original_metadata": snapshot})
            filename = _filename(metadata["artist"] + " - " + metadata["title"] + ".mp3")
            pieces = (["Needs Review"] if metadata["group"] == "Needs Review"
                      else [metadata["vocal_bucket"], metadata["group"]])
            destination = "/".join([*pieces, filename])
            _safe_path(folder, destination)
            entry.update(new_path=destination, metadata=metadata,
                         original_sha256=original_sha, audio_sha256=_audio_hash(source),
                         original_metadata=snapshot,
                         quality_evidence=track.get("quality_evidence"),
                         source_size=source.stat().st_size)
        except (CoreError, OSError) as exc:
            entry["issues"].append(str(exc))
            if selected:
                warnings.append(entry["old_path"] + ": " + str(exc))
        entries.append(entry)
    selected_entries = [e for e in entries if e["selected"]]
    destinations = {}
    for entry in selected_entries:
        if entry["issues"]:
            continue
        key = entry["new_path"].casefold()
        if key in destinations:
            issue = "Two selected tracks have the same destination name (case-insensitive)."
            entry["issues"].append(issue)
            destinations[key]["issues"].append(issue)
        destinations[key] = entry
        if entry["new_path"] != entry["old_path"]:
            destination = _safe_path(folder, entry["new_path"])
            if _case_exists(folder, entry["new_path"]):
                entry["issues"].append("Destination already exists; overwriting and move cycles are refused.")
            if destination.parent.exists() and not destination.parent.is_dir():
                entry["issues"].append("Destination parent is not a folder.")
    for entry in selected_entries:
        for issue in entry["issues"]:
            message = entry["old_path"] + ": " + issue
            if message not in warnings:
                warnings.append(message)
    return {"root": str(folder), "root_identity": _identity(folder), "entries": entries,
            "warnings": warnings, "can_apply": bool(selected_entries) and not warnings,
            "schema": 1}


def _case_exists(root: Path, relative: str) -> bool:
    current = root
    for part in relative.split("/"):
        if not current.is_dir():
            return current.exists()
        matches = [p for p in current.iterdir() if p.name.casefold() == part.casefold()]
        if not matches:
            return False
        current = matches[0]
    return current.exists() or current.is_symlink()


def _save_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    _sync_dir(path.parent)


def _sync_dir(path: Path) -> None:
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _progress(callback, phase: str, current: int, total: int, message: str) -> None:
    if callback:
        callback({"phase": phase, "current": current, "total": total, "message": message})


def _cancel(callback) -> None:
    if callback and callback():
        raise CoreError("Operation cancelled.")


def _mutate(path: Path, metadata: dict, original: dict) -> dict:
    tags, _ = _inspect(path)
    version = original["id3_version"][1]
    version = version if version in {3, 4} else 4
    changed_keys = {"TIT2", "TPE1", "TCON", "TXXX:MUSIC_LIBRARY_VOCAL_BUCKET", "TXXX:MUSIC_LIBRARY_GROUP"}
    encoding = 1 if version == 3 else 3
    for key, frame, value in (("TPE1", TPE1, metadata["artist"]),
                              ("TIT2", TIT2, metadata["title"]),
                              ("TCON", TCON, metadata["genre"])):
        # Unedited fields are kept byte-semantically, including their encoding.
        if _text(tags, key) != value:
            tags.delall(key)
            if value:
                tags.add(frame(encoding=encoding, text=[value]))
    if _moods(tags) != metadata["moods"]:
        changed_keys.update({"TMOO", "TXXX:MOOD", "TXXX:Mood"})
        mood_key = "TMOO" if "TMOO" in tags and version == 4 else "TXXX:MOOD"
        for key in ("TMOO", "TXXX:MOOD", "TXXX:Mood"):
            tags.delall(key)
        if metadata["moods"]:
            if mood_key == "TMOO":
                tags.add(TMOO(encoding=encoding, text=[metadata["moods"]]))
            else:
                tags.add(TXXX(encoding=encoding, desc="MOOD", text=[metadata["moods"]]))
    for desc, value in (("MUSIC_LIBRARY_VOCAL_BUCKET", metadata["vocal_bucket"]),
                        ("MUSIC_LIBRARY_GROUP", metadata["group"])):
        tags.delall("TXXX:" + desc)
        tags.add(TXXX(encoding=encoding, desc=desc, text=[value]))
    tags.save(path, v1=1, v2_version=version, v23_sep=None)
    _, after = _inspect(path)
    if after["artwork"] != original["artwork"]:
        raise CoreError("Artwork verification failed while staging: " + path.name)
    untouched_before = {k: v for k, v in original["frames"].items() if k not in changed_keys}
    untouched_after = {k: v for k, v in after["frames"].items() if k not in changed_keys}
    if untouched_before != untouched_after:
        raise CoreError("An unrelated metadata frame changed while staging: " + path.name)
    if after["artist"] != metadata["artist"] or after["title"] != metadata["title"] or after["genre"] != metadata["genre"]:
        raise CoreError("Edited tags did not round-trip correctly: " + path.name)
    return {"unchanged_frame_count": len(untouched_before), "artwork_preserved": True,
            "id3_version_before": original["id3_version"], "id3_version_after": after["id3_version"]}


def _playlist_changes(root: Path, entries: list[dict]) -> tuple[list[dict], list[str]]:
    paths = {str(_safe_path(root, e["old_path"])): _safe_path(root, e["new_path"])
             for e in entries if e["old_path"] != e["new_path"]}
    changed, warnings = [], []
    if not paths:
        return changed, warnings
    for path in _walk(root):
        if path.suffix.casefold() not in PLAYLIST_EXTENSIONS:
            continue
        relative = path.relative_to(root).as_posix()
        _safe_path(root, relative)
        _regular(path)
        raw = path.read_bytes()
        encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
        try:
            content = raw.decode(encoding)
        except UnicodeDecodeError:
            warnings.append("Playlist encoding is unrecognized; its bytes are preserved: " + relative)
            continue
        result = []
        for line in content.splitlines(keepends=True):
            ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else "\r" if line.endswith("\r") else ""
            bare = line[:-len(ending)] if ending else line
            prefix, value = "", bare
            if path.suffix.casefold() == ".pls":
                match = re.match(r"^(File[0-9]+=)(.*)$", bare, re.I)
                if not match:
                    result.append(line)
                    continue
                prefix, value = match.groups()
            if not value or value.lstrip().startswith("#"):
                result.append(line)
                continue
            leading = value[:len(value) - len(value.lstrip())]
            trailing = value[len(value.rstrip()):]
            reference = value.strip()
            reference_path = Path(reference.replace("\\", os.sep))
            absolute = reference_path.is_absolute()
            candidate = reference_path if absolute else path.parent / reference_path
            replacement = paths.get(str(candidate.resolve()))
            if replacement is None:
                result.append(line)
                continue
            new_reference = str(replacement) if absolute else os.path.relpath(replacement, path.parent)
            new_reference = new_reference.replace("\\", "/")
            if "\\" in reference and "/" not in reference:
                new_reference = new_reference.replace("/", "\\")
            result.append(prefix + leading + new_reference + trailing + ending)
        updated = "".join(result).encode(encoding)
        if updated != raw:
            changed.append({"path": relative, "original_sha256": hashlib.sha256(raw).hexdigest(),
                            "updated_sha256": hashlib.sha256(updated).hexdigest(), "bytes": updated})
    return changed, warnings


def _validate_plan(plan: dict) -> tuple[Path, list[dict]]:
    if not isinstance(plan, dict) or plan.get("schema") != 1 or plan.get("can_apply") is not True:
        raise CoreError("Create a valid preview before applying changes.")
    root = _root(plan.get("root", ""))
    if plan.get("root_identity") != _identity(root):
        raise CoreError("The selected root folder changed since preview.")
    entries = [e for e in plan.get("entries", []) if e.get("selected") is True]
    if not entries:
        raise CoreError("Select at least one track.")
    tracks = []
    for entry in entries:
        source = _safe_path(root, entry["old_path"])
        _regular(source)
        if _sha(source) != entry.get("original_sha256"):
            raise CoreError("Source changed since preview: " + entry["old_path"])
        tracks.append({**entry["metadata"], "source_path": entry["old_path"], "id": entry["id"],
                       "enabled": True, "original_sha256": entry["original_sha256"],
                       "quality_evidence": entry.get("quality_evidence")})
    rechecked = preview_plan(str(root), tracks)
    if not rechecked["can_apply"]:
        raise CoreError("; ".join(rechecked["warnings"]))
    for original, checked in zip(entries, rechecked["entries"]):
        if original["old_path"] != checked["old_path"] or original["new_path"] != checked["new_path"] or original["metadata"] != checked["metadata"]:
            raise CoreError("Preview was altered; generate a fresh preview before applying.")
    return root, rechecked["entries"]


def _publish(source: Path, destination: Path) -> None:
    """Publish without replacement on Windows and POSIX, on this root's volume."""
    os.link(source, destination)
    source.unlink()
    _sync_dir(destination.parent)


def apply_plan(plan: dict, progress: Callable | None = None, cancel: Callable | None = None) -> dict:
    root, entries = _validate_plan(plan)
    _cancel(cancel)
    playlists, playlist_warnings = _playlist_changes(root, entries)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    run_relative = "_Organization/runs/" + run_id
    run_dir = _safe_path(root, run_relative, audit=True)
    run_dir.mkdir(parents=True, exist_ok=False)
    stage_dir = run_dir / "stage"
    stage_dir.mkdir()
    manifest_path = run_dir / "manifest.json"
    backup = run_dir / "originals.zip"
    manifest = {"schema": 1, "run_id": run_id, "root": str(root), "root_identity": _identity(root),
                "created_utc": datetime.now(timezone.utc).isoformat(), "state": "backing_up",
                "entries": entries, "playlists": [{k: v for k, v in p.items() if k != "bytes"} for p in playlists],
                "warnings": playlist_warnings, "changed": 0}
    _save_json(manifest_path, manifest)
    try:
        with zipfile.ZipFile(backup, "x", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for index, entry in enumerate(entries, 1):
                _cancel(cancel)
                source = _safe_path(root, entry["old_path"])
                _regular(source)
                archive.write(source, entry["old_path"])
                _progress(progress, "backup", index, len(entries), entry["old_path"])
            for playlist in playlists:
                archive.write(_safe_path(root, playlist["path"]), playlist["path"])
        with backup.open("r+b") as stream:
            os.fsync(stream.fileno())
        _verify_backup(backup, manifest)
        manifest["backup_sha256"] = _sha(backup)
        manifest["state"] = "staging"
        _save_json(manifest_path, manifest)
        for index, entry in enumerate(entries, 1):
            _cancel(cancel)
            source = _safe_path(root, entry["old_path"])
            if _sha(source) != entry["original_sha256"]:
                raise CoreError("Source changed during preparation: " + entry["old_path"])
            staged = stage_dir / (str(index) + ".mp3")
            shutil.copy2(source, staged)
            entry["metadata_audit"] = _mutate(staged, entry["metadata"], entry["original_metadata"])
            if _audio_hash(staged) != entry["audio_sha256"]:
                raise CoreError("Encoded audio verification failed: " + entry["old_path"])
            entry["staged_sha256"] = _sha(staged)
            entry["stage_name"] = staged.name
            entry["state"] = "prepared"
            with staged.open("r+b") as stream:
                os.fsync(stream.fileno())
            _save_json(manifest_path, manifest)
            _progress(progress, "stage", index, len(entries), entry["old_path"])
        for index, playlist in enumerate(playlists):
            path = _safe_path(root, playlist["path"])
            if _sha(path) != playlist["original_sha256"]:
                raise CoreError("Playlist changed during preparation: " + playlist["path"])
            staged = stage_dir / ("playlist-" + str(index))
            with staged.open("xb") as stream:
                stream.write(playlist["bytes"])
                stream.flush()
                os.fsync(stream.fileno())
            manifest["playlists"][index]["stage_name"] = staged.name
            manifest["playlists"][index]["state"] = "prepared"
        # Revalidate ALL inputs after staging, before the first source changes.
        _validate_plan(plan)
        manifest["state"] = "applying"
        _save_json(manifest_path, manifest)
        for index, entry in enumerate(entries, 1):
            _cancel(cancel)
            source = _safe_path(root, entry["old_path"])
            destination = _safe_path(root, entry["new_path"])
            _regular(source)
            if _sha(source) != entry["original_sha256"]:
                raise CoreError("Source changed before commit: " + entry["old_path"])
            if entry["new_path"] != entry["old_path"] and _case_exists(root, entry["new_path"]):
                raise CoreError("A destination was created after preview: " + entry["new_path"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            staged = stage_dir / entry["stage_name"]
            if _sha(staged) != entry["staged_sha256"]:
                raise CoreError("Staged file changed before commit.")
            entry["state"] = "committing"
            _save_json(manifest_path, manifest)
            if source == destination:
                os.replace(staged, destination)
                _sync_dir(destination.parent)
            else:
                _publish(staged, destination)
                entry["state"] = "destination_written"
                _save_json(manifest_path, manifest)
                if _sha(source) != entry["original_sha256"]:
                    raise CoreError("Source changed during commit: " + entry["old_path"])
                source.unlink()
                _sync_dir(source.parent)
            entry["state"] = "applied"
            manifest["changed"] = index
            _save_json(manifest_path, manifest)
            _progress(progress, "apply", index, len(entries), entry["new_path"])
        for playlist in manifest["playlists"]:
            _cancel(cancel)
            target = _safe_path(root, playlist["path"])
            _regular(target)
            if _sha(target) != playlist["original_sha256"]:
                raise CoreError("Playlist changed before commit: " + playlist["path"])
            playlist["state"] = "committing"
            _save_json(manifest_path, manifest)
            os.replace(stage_dir / playlist["stage_name"], target)
            _sync_dir(target.parent)
            playlist["state"] = "applied"
            _save_json(manifest_path, manifest)
        manifest["state"] = "complete"
        _save_json(manifest_path, manifest)
        return {"run_id": run_id, "root": str(root), "changed": len(entries),
                "manifest": str(manifest_path), "backup": str(backup), "warnings": playlist_warnings}
    except Exception as exc:
        manifest["error"] = str(exc)
        if manifest["state"] in {"applying", "restoring"}:
            manifest["state"] = "recovery_required"
            _save_json(manifest_path, manifest)
            try:
                restore_run(str(root), run_id)
                raise CoreError("Apply stopped; originals were restored. " + str(exc)) from exc
            except CoreError as restore_error:
                if str(restore_error).startswith("Apply stopped; originals were restored."):
                    raise
                raise CoreError("Apply stopped. Recovery is required for run " + run_id + ": " + str(restore_error)) from exc
        manifest["state"] = "failed_preparation"
        _save_json(manifest_path, manifest)
        raise CoreError("Preparation stopped; songs were not changed. " + str(exc)) from exc


def _archive_hash(archive: zipfile.ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with archive.open(name) as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_backup(backup: Path, manifest: dict) -> None:
    _regular(backup)
    with zipfile.ZipFile(backup) as archive:
        expected = {entry["old_path"]: entry["original_sha256"] for entry in manifest["entries"]}
        expected.update({playlist["path"]: playlist["original_sha256"] for playlist in manifest["playlists"]})
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != set(expected):
            raise CoreError("Backup file inventory does not match the manifest.")
        for name, digest in expected.items():
            _relative(name)
            if _archive_hash(archive, name) != digest:
                raise CoreError("Backup integrity failed: " + name)


def _load_run(root: str, run_id: str) -> tuple[Path, Path, dict]:
    folder = _root(root)
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise CoreError("Invalid run identifier.")
    run_dir = _safe_path(folder, "_Organization/runs/" + run_id, audit=True)
    manifest_path = run_dir / "manifest.json"
    _regular(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoreError("The run manifest is unreadable.") from exc
    if manifest.get("schema") != 1 or manifest.get("run_id") != run_id or manifest.get("root") != str(folder) or manifest.get("root_identity") != _identity(folder):
        raise CoreError("The run belongs to another or replaced music folder.")
    sources, destinations = set(), set()
    for entry in manifest.get("entries", []):
        old = _relative(entry["old_path"])
        new = _relative(entry["new_path"])
        _safe_path(folder, old)
        _safe_path(folder, new)
        if old.casefold() in sources or new.casefold() in destinations:
            raise CoreError("Duplicate paths in run manifest.")
        sources.add(old.casefold())
        destinations.add(new.casefold())
    for playlist in manifest.get("playlists", []):
        _safe_path(folder, playlist["path"])
        if playlist["path"].casefold() in sources | destinations:
            raise CoreError("A playlist overlaps a track path.")
    return folder, run_dir, manifest


def restore_run(root: str, run_id: str, progress: Callable | None = None, cancel: Callable | None = None) -> dict:
    folder, run_dir, manifest = _load_run(root, run_id)
    if manifest.get("state") == "restored":
        return {"run_id": run_id, "root": str(folder), "changed": 0,
                "manifest": str(run_dir / "manifest.json"), "backup": str(run_dir / "originals.zip")}
    backup = run_dir / "originals.zip"
    _verify_backup(backup, manifest)
    if manifest.get("backup_sha256") and _sha(backup) != manifest["backup_sha256"]:
        raise CoreError("The backup archive changed after preparation.")
    entries = manifest["entries"]
    # Refuse externally changed files before restoring ANY original.
    for entry in entries:
        old = _safe_path(folder, entry["old_path"])
        new = _safe_path(folder, entry["new_path"])
        expected = {entry["original_sha256"]}
        if old == new and entry.get("staged_sha256"):
            expected.add(entry["staged_sha256"])
        if old.exists():
            _regular(old)
            if _sha(old) not in expected:
                raise CoreError("Restore would overwrite an externally changed source: " + entry["old_path"])
        if new != old and new.exists():
            _regular(new)
            if not entry.get("staged_sha256") or _sha(new) != entry["staged_sha256"]:
                raise CoreError("Restore would remove an externally changed destination: " + entry["new_path"])
    for playlist in manifest["playlists"]:
        path = _safe_path(folder, playlist["path"])
        if path.exists():
            _regular(path)
            if _sha(path) not in {playlist["original_sha256"], playlist["updated_sha256"]}:
                raise CoreError("Restore would overwrite an externally changed playlist: " + playlist["path"])
    _cancel(cancel)
    manifest["state"] = "restoring"
    _save_json(run_dir / "manifest.json", manifest)
    restore_stage = run_dir / "restore-stage"
    restore_stage.mkdir(exist_ok=True)
    changed = 0
    try:
        with zipfile.ZipFile(backup) as archive:
            for index, entry in enumerate(entries, 1):
                _cancel(cancel)
                old = _safe_path(folder, entry["old_path"])
                new = _safe_path(folder, entry["new_path"])
                needs_restore = not old.exists() or _sha(old) != entry["original_sha256"]
                if needs_restore:
                    staged = restore_stage / (str(index) + ".mp3")
                    with archive.open(entry["old_path"]) as source, staged.open("wb") as target:
                        shutil.copyfileobj(source, target)
                        target.flush()
                        os.fsync(target.fileno())
                    if _sha(staged) != entry["original_sha256"]:
                        raise CoreError("Restore staging integrity failed.")
                    old.parent.mkdir(parents=True, exist_ok=True)
                    if old.exists():
                        if old != new or _sha(old) != entry.get("staged_sha256"):
                            raise CoreError("A source changed while restoring: " + entry["old_path"])
                        os.replace(staged, old)
                        _sync_dir(old.parent)
                    else:
                        _publish(staged, old)
                    changed += 1
                if new != old and new.exists():
                    if _sha(new) != entry.get("staged_sha256"):
                        raise CoreError("A destination changed while restoring: " + entry["new_path"])
                    new.unlink()
                    _sync_dir(new.parent)
                entry["state"] = "restored"
                _save_json(run_dir / "manifest.json", manifest)
                _progress(progress, "restore", index, len(entries), entry["old_path"])
            for index, playlist in enumerate(manifest["playlists"]):
                _cancel(cancel)
                path = _safe_path(folder, playlist["path"])
                if not path.exists() or _sha(path) != playlist["original_sha256"]:
                    staged = restore_stage / ("playlist-" + str(index))
                    with archive.open(playlist["path"]) as source, staged.open("wb") as target:
                        shutil.copyfileobj(source, target)
                        target.flush()
                        os.fsync(target.fileno())
                    if _sha(staged) != playlist["original_sha256"]:
                        raise CoreError("Playlist restore staging integrity failed.")
                    if path.exists():
                        if _sha(path) != playlist["updated_sha256"]:
                            raise CoreError("A playlist changed while restoring.")
                        os.replace(staged, path)
                    else:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        _publish(staged, path)
                    _sync_dir(path.parent)
                playlist["state"] = "restored"
                _save_json(run_dir / "manifest.json", manifest)
        manifest["state"] = "restored"
        manifest["restored_utc"] = datetime.now(timezone.utc).isoformat()
        _save_json(run_dir / "manifest.json", manifest)
        return {"run_id": run_id, "root": str(folder), "changed": changed,
                "manifest": str(run_dir / "manifest.json"), "backup": str(backup)}
    except Exception as exc:
        manifest["state"] = "recovery_required"
        manifest["restore_error"] = str(exc)
        _save_json(run_dir / "manifest.json", manifest)
        raise CoreError("Restore stopped safely; resume this run after resolving the issue. " + str(exc)) from exc


def list_runs(root: str) -> list[dict]:
    folder = _root(root)
    runs = _safe_path(folder, "_Organization/runs", audit=True)
    if not runs.exists():
        return []
    output = []
    for directory in sorted(runs.iterdir(), reverse=True):
        if not directory.is_dir() or not RUN_ID.fullmatch(directory.name):
            continue
        try:
            _, _, manifest = _load_run(str(folder), directory.name)
            output.append({"run_id": directory.name, "state": manifest["state"],
                           "created_utc": manifest["created_utc"], "changed": manifest.get("changed", 0),
                           "track_count": len(manifest["entries"]),
                           "manifest": str(directory / "manifest.json"),
                           "backup": str(directory / "originals.zip"),
                           "can_restore": manifest["state"] != "restored" and bool(manifest.get("backup_sha256")),
                           "error": manifest.get("error", manifest.get("restore_error", ""))})
        except (CoreError, OSError, KeyError) as exc:
            output.append({"run_id": directory.name, "state": "invalid_manifest", "can_restore": False, "error": str(exc)})
    return output
