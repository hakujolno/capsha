from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage, QImageReader


SUPPORTED_IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".gif",
}


def is_supported_image_path(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES


def image_path_from_args(args: list[str]) -> Path | None:
    for value in args:
        path = Path(value)
        if is_supported_image_path(path):
            return path
    return None


def load_image(path: Path) -> QImage | None:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        return None
    image.setDevicePixelRatio(1.0)
    return image
