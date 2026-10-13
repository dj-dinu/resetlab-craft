"""Generate an obviously labelled local synthetic demo, never private songs."""
from pathlib import Path
from mutagen.id3 import ID3, TIT2, TPE1, TCON, APIC


def create_demo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    # Valid MPEG-1 Layer III zero-side-information frames decode to silence.
    frame = bytes.fromhex("fffb90c0") + bytes(413)
    for index, (artist, title, genre) in enumerate([
        ("Example Artist", "Synthetic Silence (Demo)", "Progressive House"),
        ("Sample Duo", "Another Synthetic Demo (HQ)", "Organic House"),
    ]):
        path = root / f"{index + 1:02d} - {title}.mp3"
        if path.exists():
            continue
        path.write_bytes(frame * 400)
        tags = ID3()
        tags.add(TPE1(encoding=1, text=[artist]))
        tags.add(TIT2(encoding=1, text=[title]))
        tags.add(TCON(encoding=1, text=[genre]))
        tags.save(path, v2_version=3)
    (root / "DEMO.txt").write_text(
        "Generated silent synthetic MP3 frames for testing the application.\n"
        "The existing HQ filename is deliberately untrusted and should be reanalyzed.\n"
        "These are not real songs or examples of high-quality music.\n", encoding="utf-8")
    return root
