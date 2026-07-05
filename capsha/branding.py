from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap


ASSET_DIRECTORY = Path(__file__).resolve().parent / "assets"


def load_brand_logo(size: int) -> QPixmap:
    """Load one replaceable logo asset without background work."""
    for name in ("logo.svg", "logo.png", "logo.ico"):
        path = ASSET_DIRECTORY / name
        if not path.is_file():
            continue
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            return pixmap.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
    return QPixmap()


def load_brand_icon() -> QIcon:
    for name in ("capsha.ico", "logo.svg", "logo.png"):
        path = ASSET_DIRECTORY / name
        if path.is_file():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return QIcon()
