"""Render the app's existing SVG mark into a build-only Windows icon.

This intentionally supports only the small SVG vocabulary used by mark.svg.
An unsupported logo edit fails the build instead of silently dropping artwork.
Pillow is a build dependency; the desktop app does not import this module.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw

PROJECT = Path(__file__).resolve().parent.parent
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
PATH_TOKEN = re.compile(r"[MLHVmlhv]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")


def _path_segments(data):
    """Read straight SVG paths, including repeated and relative coordinates."""
    if PATH_TOKEN.sub("", data).strip(" ,\t\r\n"):
        raise ValueError("Icon path uses unsupported SVG commands.")
    tokens = PATH_TOKEN.findall(data)
    paths, points = [], []
    position = (0.0, 0.0)
    command = None
    index = 0
    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
        if command is None:
            raise ValueError("Icon path is missing its first command.")
        count = 2 if command.upper() in {"M", "L"} else 1
        values = tokens[index:index + count]
        if len(values) != count or any(value.isalpha() for value in values):
            raise ValueError("Icon path command is missing coordinates.")
        values = tuple(float(value) for value in values)
        index += count
        relative = command.islower()
        x, y = position
        if command.upper() in {"M", "L"}:
            new_position = (values[0] + (x if relative else 0),
                            values[1] + (y if relative else 0))
        elif command.upper() == "H":
            new_position = (values[0] + (x if relative else 0), y)
        else:
            new_position = (x, values[0] + (y if relative else 0))
        if command.upper() == "M":
            if points:
                paths.append(points)
            points = [new_position]
            command = "l" if relative else "L"
        else:
            if not points:
                raise ValueError("Icon path must begin with a move command.")
            points.append(new_position)
        position = new_position
    if points:
        paths.append(points)
    return paths


def write_icon(source: Path, destination: Path) -> Path:
    source, destination = Path(source), Path(destination)
    root = ET.parse(source).getroot()
    box = tuple(float(value) for value in root.attrib["viewBox"].split())
    if len(box) != 4 or box[0:2] != (0, 0) or box[2] <= 0 or box[2] != box[3]:
        raise ValueError("The icon source must have a square SVG viewBox starting at zero.")
    resolution = 1024
    scale = resolution / box[2]
    image = Image.new("RGBA", (resolution, resolution), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for element in root:
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "rect":
            if set(element.attrib) - {"x", "y", "width", "height", "rx", "fill"}:
                raise ValueError("Icon rectangle uses unsupported SVG attributes.")
            x, y = float(element.get("x", "0")), float(element.get("y", "0"))
            width, height = float(element.attrib["width"]), float(element.attrib["height"])
            radius = float(element.get("rx", "0"))
            draw.rounded_rectangle((x * scale, y * scale, (x + width) * scale,
                                    (y + height) * scale), radius=radius * scale,
                                   fill=element.attrib["fill"])
        elif tag == "path":
            if (set(element.attrib) - {"d", "fill", "stroke", "stroke-width",
                                       "stroke-linecap", "stroke-linejoin"}
                    or element.get("fill") != "none"
                    or element.get("stroke-linecap") != "round"
                    or element.get("stroke-linejoin", "round") != "round"):
                raise ValueError("Icon path uses unsupported SVG styling.")
            width = float(element.attrib["stroke-width"]) * scale
            radius = width / 2
            color = element.attrib["stroke"]
            for points in _path_segments(element.attrib["d"]):
                scaled = [(x * scale, y * scale) for x, y in points]
                if len(scaled) > 1:
                    draw.line(scaled, fill=color, width=round(width), joint="curve")
                for x, y in scaled:
                    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
        else:
            raise ValueError("Icon source uses an unsupported SVG element: " + tag)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="ICO", sizes=[(size, size) for size in ICON_SIZES])
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=PROJECT / "music_library_lab/static/mark.svg")
    parser.add_argument("--output", type=Path, default=PROJECT / ".work/desktop-build/app-icon.ico")
    args = parser.parse_args()
    print(write_icon(args.source, args.output))


if __name__ == "__main__":
    main()
