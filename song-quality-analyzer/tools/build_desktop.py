"""Build a private desktop alpha from the configured canonical source.

The engine copy is generated, hashed and rebuilt; never edit it independently.
This produces a local test bundle, not permission to publish a release.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
DEPENDENCIES = PROJECT / ".localdeps"
if DEPENDENCIES.is_dir():
    sys.path.insert(0, str(DEPENDENCIES))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scanner", type=Path)
    parser.add_argument("--decoder", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    settings_path = PROJECT / "local_settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.is_file() else {}
    scanner = (args.scanner or Path(settings.get("scanner_path", str(PROJECT / "canonical" / "scan_quality.py")))).resolve()
    decoder = (args.decoder or Path(settings.get("decoder_path", ""))).resolve()
    if not scanner.is_file() or not decoder.is_file():
        raise SystemExit("Provide the canonical --scanner source and a permitted --decoder library.")
    if sys.platform != "win32":
        raise SystemExit("This bundle recipe currently targets Windows; macOS packaging needs its own native recipe and validation.")
    from music_library_lab import __version__, APP_NAME, SUITE_NAME, TOOL_NAME, BUNDLE_NAME
    from tools.build_icon import write_icon

    work = PROJECT / ".work" / "desktop-build"
    icon_source = PROJECT / "music_library_lab" / "static" / "mark.svg"
    icon = write_icon(icon_source, work / "app-icon.ico")
    stage = work / "stage"
    engine_dir, decoder_dir = stage / "canonical", stage / "decoder"
    notices = stage / "third-party-notices"
    for directory in (engine_dir, decoder_dir, notices):
        directory.mkdir(parents=True, exist_ok=True)
    engine_copy = engine_dir / "scan_quality.py"
    shutil.copyfile(scanner, engine_copy)
    if sha256(scanner) != sha256(engine_copy):
        raise SystemExit("The generated engine copy differs from its canonical source.")
    shutil.copyfile(decoder, decoder_dir / "libmpg123-0.dll")
    copying = decoder.parent / "COPYING.txt"
    if copying.is_file():
        shutil.copyfile(copying, notices / "mpg123-COPYING.txt")

    packages = {}
    for name in ("av", "numpy", "mutagen", "pywebview", "pythonnet", "clr_loader", "cffi", "bottle", "proxy_tools", "pyinstaller"):
        try:
            distribution = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            raise SystemExit("Missing desktop/build dependency: " + name)
        packages[name] = distribution.version
        destination = notices / name
        for entry in distribution.files or ():
            path = Path(str(entry))
            if "licenses" in path.parts or path.name.lower().startswith(("license", "copying", "notice")):
                source = Path(distribution.locate_file(entry))
                if source.is_file() and source.suffix.lower() not in {".pyc", ".pyo", ".py"}:
                    destination.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination / source.name)
    (notices / "README.txt").write_text(
        "Local test bundle only. Included license files are preliminary notices, not release qualification.\n"
        "PyAV bundles FFmpeg and additional native libraries. Before redistribution, record each binary's\n"
        "license, exact corresponding source/build recipe and relinking requirements.\n"
        "mpg123: https://www.mpg123.de/ ; PyAV: https://pyav.basswood.io/ ; FFmpeg: https://ffmpeg.org/legal.html\n",
        encoding="utf-8",
    )
    manifest = {"app": APP_NAME, "suite": SUITE_NAME, "tool": TOOL_NAME, "version": __version__, "purpose": "local desktop alpha",
                "public_release_qualified": False, "built_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_license": {"spdx": "GPL-3.0-only", "file": "LICENSE", "sha256": sha256(PROJECT / "LICENSE"),
                                   "scope": "project-owned source; third parties retain their own terms"},
                "engine": {"file": "canonical/scan_quality.py", "sha256": sha256(engine_copy),
                           "maintenance": "generated from canonical source; no independent grading implementation"},
                "decoder": {"file": "decoder/libmpg123-0.dll", "sha256": sha256(decoder)},
                "icon": {"source": "music_library_lab/static/mark.svg", "source_sha256": sha256(icon_source),
                         "sha256": sha256(icon), "embedded_in": BUNDLE_NAME + ".exe"},
                "packages": packages}
    (stage / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    import av
    av_libraries = Path(av.__file__).parent.parent / "av.libs"
    binaries = [(str(path), "av.libs") for path in sorted(av_libraries.glob("*.dll"))]
    binaries.append((str(decoder_dir / "libmpg123-0.dll"), "decoder"))
    datas = [(str(PROJECT / "music_library_lab" / "static"), "music_library_lab/static"),
             (str(PROJECT / "LICENSE"), "."), (str(PROJECT / "docs" / "REUSE_AND_BRANDING.md"), "."),
             (str(engine_copy), "canonical"), (str(stage / "build-manifest.json"), "."),
             (str(notices), "third-party-notices")]
    spec = work / (BUNDLE_NAME + ".spec")
    spec.write_text(
        "from PyInstaller.utils.hooks import collect_submodules, collect_data_files\n"
        f"a = Analysis([{str(PROJECT / 'run_desktop.py')!r}], pathex={[str(PROJECT), str(DEPENDENCIES)]!r},\n"
        f"    binaries={binaries!r}, datas={datas!r} + collect_data_files('webview'),\n"
        "    hiddenimports=collect_submodules('av') + ['wave', 'numpy', 'mutagen', 'webview.platforms.winforms',\n"
        "        'webview.platforms.edgechromium', 'clr_loader', 'pythonnet', 'clr'],\n"
        "    hookspath=[], hooksconfig={}, runtime_hooks=[],\n"
        "    excludes=['tkinter','PyQt5','PyQt6','PySide2','PySide6','matplotlib','pandas','scipy','torch'],\n"
        "    noarchive=False, optimize=1)\n"
        "pyz = PYZ(a.pure)\n"
        f"exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name={BUNDLE_NAME!r},\n"
        f"    debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False, icon={str(icon)!r})\n"
        f"bundle = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name={BUNDLE_NAME!r})\n",
        encoding="utf-8",
    )
    if args.prepare_only:
        print(json.dumps({"prepared": True, "engine_sha256": manifest["engine"]["sha256"], "spec": str(spec)}))
        return
    import PyInstaller.__main__
    PyInstaller.__main__.run([str(spec), "--noconfirm", "--distpath", str(PROJECT / "dist"),
                             "--workpath", str(work / "pyinstaller-work")])
    bundle = PROJECT / "dist" / BUNDLE_NAME
    manifest["bundle_bytes"] = sum(path.stat().st_size for path in bundle.rglob("*") if path.is_file())
    (work / "completed-build.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"built": True, "executable": str(bundle / (BUNDLE_NAME + ".exe")),
                      "bundle_bytes": manifest["bundle_bytes"], "engine_sha256": manifest["engine"]["sha256"]}))


if __name__ == "__main__":
    main()
