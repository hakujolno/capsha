from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "capsha" / "assets" / "logo.svg"
OUTPUT = ROOT / "capsha" / "assets" / "capsha.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def render_png(renderer: QSvgRenderer, size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG", 100):
        raise RuntimeError(f"Failed to render the {size}px icon")
    buffer.close()
    return bytes(data)


def build_icon() -> None:
    renderer = QSvgRenderer(str(SOURCE))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG: {SOURCE}")

    images = [(size, render_png(renderer, size)) for size in SIZES]
    offset = 6 + 16 * len(images)
    entries: list[bytes] = []
    payloads: list[bytes] = []
    for size, payload in images:
        dimension = 0 if size == 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII",
                dimension,
                dimension,
                0,
                0,
                1,
                32,
                len(payload),
                offset,
            )
        )
        payloads.append(payload)
        offset += len(payload)

    OUTPUT.write_bytes(
        struct.pack("<HHH", 0, 1, len(images))
        + b"".join(entries)
        + b"".join(payloads)
    )
    print(f"Created {OUTPUT} ({', '.join(map(str, SIZES))} px)")


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    build_icon()
