from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from PySide6.QtCore import QPointF, QRectF


class Tool(Enum):
    SELECT = auto()
    TEXT = auto()
    CAPTION = auto()
    RECTANGLE = auto()
    ARROW = auto()
    MOSAIC = auto()


@dataclass
class TextAnnotation:
    text: str
    position: QPointF
    color: str = "#ef3f4f"
    font_size: int = 20
    bold: bool = True
    font_family: str = "Segoe UI Variable"
    italic: bool = False
    outline_enabled: bool = False
    outline_color: str = "#000000"
    background_enabled: bool = False
    background_color: str = "#000000"
    background_opacity: int = 115


@dataclass
class CaptionAnnotation(TextAnnotation):
    number: int = 1


@dataclass
class RectangleAnnotation:
    rect: QRectF
    color: str = "#ef3f4f"
    line_width: int = 4
    fill_enabled: bool = False
    fill_opacity: int = 77
    rounded: bool = False
    line_opacity: int = 255
    line_style: str = "solid"


@dataclass
class ArrowAnnotation:
    start: QPointF
    end: QPointF
    color: str = "#ef3f4f"
    line_width: int = 4
    line_opacity: int = 255
    line_style: str = "solid"


@dataclass
class MosaicAnnotation:
    rect: QRectF


Annotation = (
    TextAnnotation
    | CaptionAnnotation
    | RectangleAnnotation
    | ArrowAnnotation
    | MosaicAnnotation
)
