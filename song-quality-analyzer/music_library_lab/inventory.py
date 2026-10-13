"""Read-only native-path inventory, independent of manager naming/tag rules.

Metadata and encoded bitrate are descriptive only. The canonical scanner is the
only component allowed to produce measured HQ/MQ/LQ results.
"""
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
import re
import stat
import time
import uuid

from mutagen import File as MediaFile
from mutagen.aac import AAC
from mutagen.aiff import AIFF
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.wave import WAVE

SUPPORTED_EXTENSIONS = frozenset({".mp3", ".wav", ".wave", ".aif", ".aiff", ".flac", ".aac", ".m4a", ".mp4"})
SUPPORTED_FORMATS = ("MP3", "WAV", "AIFF", "FLAC", "AAC", "ALAC")
MAX_INVENTORY_TRACKS = 10_000
MAX_VISITED_ENTRIES = 100_000
MAX_WARNINGS = 100
MAX_METADATA_TEXT = 2_000
MAX_ID3_BYTES = 32 * 1024 * 1024
QUALITY_SUFFIX = re.compile(r"\s*[\[(](HQ|MQ|LQ)[\])]\s*$", re.I)


class InventoryError(ValueError):
    pass


def linked(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def music_root(value: str) -> Path:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise InventoryError("Choose an existing music folder.")
    given = Path(value).expanduser().absolute()
    if not given.is_dir():
        raise InventoryError("Music folder does not exist or is not accessible.")
    if any(linked(part) for part in (given, *given.parents)):
        raise InventoryError("Select the actual music folder rather than a symbolic link or junction.")
    root = given.resolve()
    if root == Path(root.anchor) or root == Path.home().resolve():
        raise InventoryError("Choose a music subfolder rather than a filesystem or home root.")
    if root.name.casefold() == "_organization":
        raise InventoryError("Audit records cannot be selected as the music folder.")
    return root


def safe_path(root: Path, value: str) -> Path:
    """Use native path semantics; POSIX backslashes/colons are ordinary names."""
    if not isinstance(value, str) or not value or "\x00" in value:
        raise InventoryError("Invalid track path.")
    relative = Path(value)
    if relative.is_absolute() or relative.drive or ".." in relative.parts:
        raise InventoryError("A track path must stay inside the selected folder.")
    path = root / relative
    for part in (path, *path.parents):
        if part == root:
            break
        if linked(part):
            raise InventoryError("Symbolic links and junctions are skipped: " + value)
    if not path.resolve().is_relative_to(root):
        raise InventoryError("A track path leaves the selected folder.")
    return path


def regular_file(path: Path) -> os.stat_result:
    info = path.stat(follow_symlinks=False)
    if linked(path) or not stat.S_ISREG(info.st_mode):
        raise InventoryError("Only ordinary audio files can be analyzed: " + path.name)
    # Hard-linked ordinary files are safe to read. No source is ever modified;
    # whole-file hashes detect edits made through any alias.
    return info


def music_source(value: str) -> Path:
    """Validate an explicitly chosen folder or a single ordinary audio file."""
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise InventoryError("Choose an existing music folder or audio file.")
    given = Path(value).expanduser().absolute()
    if given.is_dir():
        return music_root(value)
    if not given.is_file():
        raise InventoryError("Music folder or file does not exist or is not accessible.")
    if any(linked(part) for part in (given, *given.parents)):
        raise InventoryError("Select the actual audio file rather than a symbolic link or junction.")
    if given.suffix.lower() not in SUPPORTED_EXTENSIONS or given.name.startswith("._"):
        raise InventoryError("Choose an MP3, WAV, AIFF, FLAC, AAC or ALAC audio file.")
    if any(part.name.casefold() == "_organization" for part in given.parents):
        raise InventoryError("Audit records cannot be selected as music.")
    regular_file(given)
    # A single file in the home/filesystem root is allowed: its parent is never
    # traversed, and analysis must select exactly this filename.
    return given.resolve()


def _cancelled(cancel) -> None:
    if cancel and cancel():
        raise InterruptedError("Music reading cancelled. Song files were not changed.")


def hash_file(path: Path, cancel=None, progress=None) -> str:
    regular_file(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            _cancelled(cancel)
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
            if progress:
                progress()
    return digest.hexdigest()


def _value(tags, *keys: str) -> str:
    if tags is None:
        return ""
    for key in keys:
        try:
            value = tags.get(key)
        except (KeyError, ValueError, TypeError):
            # Tag containers enforce different key syntaxes. For example a
            # Vorbis comment dictionary rejects MP4's non-ASCII copyright key.
            # An incompatible lookup key is not unreadable audio metadata.
            continue
        if value is None:
            continue
        if hasattr(value, "text"):
            value = value.text
        if isinstance(value, (tuple, list)):
            value = "; ".join(str(part)[:MAX_METADATA_TEXT] for part in value[:20])
        return str(value)[:MAX_METADATA_TEXT].strip()
    return ""


def _positive(value, *, integer=False):
    if isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
        return int(value) if integer else float(value)
    return None


def _oversized_id3(path: Path) -> bool:
    with path.open("rb") as stream:
        header = stream.read(10)
    if header[:3] != b"ID3" or len(header) != 10:
        return False
    size = 0
    for byte in header[6:10]:
        size = (size << 7) | (byte & 127)
    return size > MAX_ID3_BYTES


def inspect_metadata(path: Path) -> dict:
    """Inspect the actual file type. Bad tags never become an audio grade."""
    if _oversized_id3(path):
        raise InventoryError("Metadata exceeds the preview budget; the canonical decoder can still try this file.")
    media = MediaFile(path)
    if media is None and path.suffix.lower() == ".aac":
        media = AAC(path)
    if media is None:
        raise InventoryError("Audio metadata could not be identified; the canonical decoder can still try this file.")
    info = media.info
    tags = media.tags
    result = {
        "artist": _value(tags, "TPE1", "artist", "\xa9ART"),
        "title": _value(tags, "TIT2", "title", "\xa9nam"),
        "genre": _value(tags, "TCON", "genre", "\xa9gen"),
        "sample_rate": _positive(getattr(info, "sample_rate", None), integer=True),
        "channels": _positive(getattr(info, "channels", None), integer=True),
        "duration_seconds": _positive(getattr(info, "length", None)),
        "encoded_bitrate": _positive(getattr(info, "bitrate", None), integer=True),
    }
    lossless = False
    if isinstance(media, MP3):
        layer = getattr(info, "layer", 3)
        result.update(codec="MP3" if layer == 3 else f"MPEG Layer {layer}", container="MPEG audio")
    elif isinstance(media, FLAC):
        result.update(codec="FLAC", container="FLAC")
        lossless = True
    elif isinstance(media, WAVE):
        audio_format = getattr(info, "audio_format", None)
        result.update(codec="PCM" if audio_format == 1 else "PCM float" if audio_format == 3 else "WAV encoding unverified",
                      container="WAV")
        lossless = audio_format in (1, 3)
    elif isinstance(media, AIFF):
        result.update(codec="PCM (AIFF metadata)", container="AIFF")
        # Mutagen reads AIFF-C too. Let the canonical decoder verify its codec;
        # do not claim a PCM bit depth for every compressed AIFF variant.
        with path.open("rb") as stream:
            lossless = stream.read(12)[8:12] == b"AIFF"
    elif isinstance(media, AAC):
        result.update(codec="AAC", container="AAC stream")
    elif isinstance(media, MP4):
        codec = str(getattr(info, "codec", ""))
        description = str(getattr(info, "codec_description", ""))
        if codec == "alac":
            result.update(codec="ALAC", container="MPEG-4")
            lossless = True
        elif codec.startswith("mp4a") and "AAC" in description:
            result.update(codec="AAC", codec_profile=description, container="MPEG-4")
        else:
            result.update(codec=description[:100] or codec[:100] or "Unverified MPEG-4 audio", container="MPEG-4")
    else:
        result.update(codec=type(media).__name__, container="Unverified audio container")
    if lossless:
        bits = _positive(getattr(info, "bits_per_sample", None), integer=True)
        if bits and bits <= 64:
            result["bit_depth"] = bits
    label = _value(tags, "TXXX:Quality", "TXXX:QUALITY", "quality").upper()
    for text in (result["title"], path.stem):
        match = QUALITY_SUFFIX.search(text)
        if match:
            label = match.group(1).upper()
            break
    result["quality"] = label if label in {"HQ", "MQ", "LQ"} else ""
    return {key: value for key, value in result.items() if value is not None}


def scan_library(root: str, progress=None, cancel=None, *,
                 max_tracks=MAX_INVENTORY_TRACKS, max_entries=MAX_VISITED_ENTRIES) -> dict:
    """Inventory native names with bounded traversal and cancellable hashing."""
    source = music_source(root)
    single_file = source.is_file()
    folder = source.parent if single_file else source
    tracks, warnings = [], []
    skipped = {"links": 0, "audit_folders": 0, "sidecars": 0, "unreadable": 0, "non_audio": 0}
    visited = 0
    truncated = False
    last_update = 0.0
    suppressed = 0

    def warn(message):
        nonlocal suppressed
        if len(warnings) < MAX_WARNINGS:
            warnings.append(message)
        else:
            suppressed += 1

    def update(force=False, message=""):
        nonlocal last_update
        now = time.monotonic()
        if progress and (force or now - last_update >= .15):
            last_update = now
            progress({"done": len(tracks), "total": None, "visited": visited,
                      "message": message or f"Found {len(tracks)} audio files; inspected {visited} folder entries"})

    def inaccessible(exc):
        skipped["unreadable"] += 1
        target = Path(exc.filename) if exc.filename else folder
        try:
            relative = target.relative_to(folder).as_posix()
        except ValueError:
            relative = "selected folder"
        warn("A folder could not be read: " + relative + ". Check access permissions.")

    update(True, "Reading the selected audio file" if single_file else "Scanning folders and reading audio metadata")
    entries = ((str(folder), [], [source.name]),) if single_file else os.walk(folder, followlinks=False, onerror=inaccessible)
    for parent, dirs, files in entries:
        _cancelled(cancel)
        directory = Path(parent)
        retained_dirs = []
        for name in sorted(dirs):
            visited += 1
            path = directory / name
            relative = path.relative_to(folder).as_posix()
            if name.casefold() == "_organization":
                skipped["audit_folders"] += 1
                continue
            if linked(path):
                skipped["links"] += 1
                warn("Linked folder skipped: " + relative)
                continue
            retained_dirs.append(name)
        dirs[:] = retained_dirs
        for name in sorted(files):
            _cancelled(cancel)
            visited += 1
            if visited > max_entries:
                truncated = True
                break
            path = directory / name
            relative = path.relative_to(folder).as_posix()
            if name.startswith("._"):
                skipped["sidecars"] += 1
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                skipped["non_audio"] += 1
                continue
            if len(tracks) >= max_tracks:
                truncated = True
                break
            track = {"id": uuid.uuid4().hex, "source_path": relative, "artist": "", "title": path.stem,
                     "quality": "", "enabled": False, "issues": [], "evidence": [], "codec": "Unverified",
                     "container": "Unverified", "size": None}
            try:
                safe_path(folder, relative)
                before = regular_file(path)
                track["size"] = before.st_size
                update(True, f"Reading {relative}")
                try:
                    metadata = inspect_metadata(path)
                    track.update(metadata)
                    track["title"] = metadata.get("title") or path.stem
                except Exception:
                    track["issues"].append("Metadata is unavailable or unsupported. Analysis will try the actual audio; errors receive no grade.")
                digest = hash_file(path, cancel=cancel, progress=update)
                after = regular_file(path)
                if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                    raise InventoryError("File changed while reading; read it again.")
                track.update(enabled=True, original_sha256=digest)
                if track["quality"]:
                    track["evidence"].append("Existing quality label only; not a measured result.")
            except InterruptedError:
                raise
            except (InventoryError, OSError) as exc:
                skipped["links" if linked(path) else "unreadable"] += 1
                track["issues"].append(str(exc))
            tracks.append(track)
            update()
        if truncated or visited > max_entries:
            truncated = True
            break
        update()
    _cancelled(cancel)
    if truncated:
        warn(f"Inventory stopped at the local limit ({max_tracks:,} audio files or {max_entries:,} entries). Choose a smaller folder; this is not a complete library inventory.")
    if skipped["audit_folders"]:
        warn(f"Skipped {skipped['audit_folders']} _Organization audit folders.")
    if skipped["sidecars"]:
        warn(f"Skipped {skipped['sidecars']} AppleDouble metadata sidecars.")
    if suppressed:
        warnings.append(f"{suppressed} additional warnings were omitted; skipped counts remain available.")
    if not tracks:
        warn("No candidate audio files were found. Supported candidates: MP3, WAV, AIFF, FLAC, AAC and ALAC; the actual codec is verified during analysis.")
    update(True, f"Music reading complete: {len(tracks)} audio files")
    return {"root": str(source), "source_kind": "file" if single_file else "folder", "tracks": tracks, "warnings": warnings, "truncated": truncated,
            "visited_entries": visited, "skipped": skipped, "audio_files_modified": False,
            "inventory_limits": {"max_tracks": max_tracks, "max_entries": max_entries}}
