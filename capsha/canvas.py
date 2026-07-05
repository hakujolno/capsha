from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFocusEvent,
    QFont,
    QFontMetricsF,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QTextEdit,
    QWidget,
)

from capsha.annotations import (
    Annotation,
    ArrowAnnotation,
    CaptionAnnotation,
    MosaicAnnotation,
    RectangleAnnotation,
    TextAnnotation,
    Tool,
)

DEFAULT_COLOR = "#ef3f4f"
CIRCLED_NUMBERS = [
    "①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
    "⑪", "⑫", "⑬", "⑭", "⑮", "⑯", "⑰", "⑱", "⑲", "⑳",
]


class InlineTextEditor(QTextEdit):
    committed = Signal()
    canceled = Signal()
    focus_committed = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._finishing = False
        self._ever_focused = False

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if (
            event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}
            and not bool(
                event.modifiers()
                & Qt.KeyboardModifier.ShiftModifier
            )
        ):
            self._finishing = True
            self.committed.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self._finishing = True
            self.canceled.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        self._ever_focused = True
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        if (
            self._ever_focused
            and not self._finishing
            and not self.toPlainText().strip()
        ):
            QTimer.singleShot(0, self._commit_if_still_unfocused)

    def _commit_if_still_unfocused(self) -> None:
        if not self._finishing and not self.hasFocus():
            self._finishing = True
            self.focus_committed.emit()


class AnnotationCanvas(QWidget):
    changed = Signal()
    history_changed = Signal(bool, bool)
    selection_changed = Signal(bool)
    zoom_changed = Signal(int)
    tool_change_requested = Signal(object)

    def __init__(self, image: QImage) -> None:
        super().__init__()
        source = image.copy()
        source.setDevicePixelRatio(1.0)
        self._base = source.convertToFormat(
            QImage.Format.Format_ARGB32_Premultiplied
        )
        self._base.setDevicePixelRatio(1.0)
        self._mosaic_preview = self._base
        self._annotations: list[Annotation] = []
        self._history: list[list[Annotation]] = [[]]
        self._history_index = 0

        self._tool = Tool.TEXT
        self._color = DEFAULT_COLOR
        self._line_width = 4
        self._font_size = 20
        self._bold = True
        self._fill_enabled = False
        self._fill_opacity = 30
        self._rounded = False
        self._line_opacity = 100
        self._line_style = "solid"
        self._font_family = "Segoe UI Variable"
        self._italic = False
        self._outline_enabled = False
        self._outline_color = "#000000"
        self._background_enabled = False
        self._caption_number = 1

        self._start: QPointF | None = None
        self._current: QPointF | None = None
        self._selected_index: int | None = None
        self._dragged_index: int | None = None
        self._drag_offset = QPointF()
        self._drag_origin: QPointF | None = None
        self._drag_original: Annotation | None = None
        self._resize_handle: str | None = None
        self._zoom = 1.0
        self._pan = QPointF()
        self._space_pressed = False
        self._panning = False
        self._pan_mouse_start = QPointF()
        self._pan_start = QPointF()
        self._grid_enabled = False
        self._inline_editor: InlineTextEditor | None = None
        self._editing_index: int | None = None
        self._editing_position: QPointF | None = None
        self._editing_original_text = ""
        self._inline_finishing = False
        self._inline_focus_pending = False

        self.setMinimumSize(560, 360)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet("background: #111827;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if (
            self._inline_editor is not None
            and not self._inline_focus_pending
            and event.type() == QEvent.Type.MouseButtonPress
        ):
            editor = self._inline_editor
            clicked_inside = (
                watched is editor
                or (
                    isinstance(watched, QWidget)
                    and editor.isAncestorOf(watched)
                )
            )
            if not clicked_inside:
                self._commit_inline_editor()
        elif (
            self._inline_editor is not None
            and self._inline_focus_pending
            and event.type() == QEvent.Type.MouseButtonRelease
        ):
            self._activate_inline_editor()
        return super().eventFilter(watched, event)

    def set_tool(self, tool: Tool) -> None:
        self._tool = tool
        cursor = Qt.CursorShape.ArrowCursor
        if tool == Tool.TEXT:
            cursor = Qt.CursorShape.PointingHandCursor
        elif tool != Tool.SELECT:
            cursor = Qt.CursorShape.CrossCursor
        self.setCursor(cursor)

    def set_color(self, color: QColor) -> None:
        self._color = color.name()
        annotation = self.selected_annotation()
        if isinstance(
            annotation,
            (TextAnnotation, RectangleAnnotation, ArrowAnnotation),
        ):
            annotation.color = self._color
            self._commit_history()
            self.update()

    def set_line_width(self, width: int) -> None:
        self._line_width = width
        annotation = self.selected_annotation()
        if isinstance(
            annotation, (RectangleAnnotation, ArrowAnnotation)
        ):
            annotation.line_width = width
            self._commit_history()
            self.update()

    def set_font_size(self, size: int) -> None:
        size = max(8, min(size, 240))
        self._font_size = size
        annotation = self.selected_annotation()
        if isinstance(annotation, TextAnnotation):
            annotation.font_size = size
            self._commit_history()
            self.update()

    def set_bold(self, enabled: bool) -> None:
        self._bold = enabled
        annotation = self.selected_annotation()
        if isinstance(annotation, TextAnnotation):
            annotation.bold = enabled
            self._commit_history()
            self.update()

    def set_fill_enabled(self, enabled: bool) -> None:
        self._fill_enabled = enabled
        annotation = self.selected_annotation()
        if isinstance(annotation, RectangleAnnotation):
            annotation.fill_enabled = enabled
            self._commit_history()
            self.update()

    def set_fill_opacity(self, percent: int) -> None:
        self._fill_opacity = percent
        annotation = self.selected_annotation()
        if isinstance(annotation, RectangleAnnotation):
            annotation.fill_opacity = round(percent * 255 / 100)
            self._commit_history()
            self.update()

    def set_rounded(self, enabled: bool) -> None:
        self._rounded = enabled
        annotation = self.selected_annotation()
        if isinstance(annotation, RectangleAnnotation):
            annotation.rounded = enabled
            self._commit_history()
            self.update()

    def set_line_opacity(self, percent: int) -> None:
        self._line_opacity = percent
        annotation = self.selected_annotation()
        if isinstance(
            annotation, (RectangleAnnotation, ArrowAnnotation)
        ):
            annotation.line_opacity = round(percent * 255 / 100)
            self._commit_history()
            self.update()

    def set_line_style(self, style: str) -> None:
        self._line_style = style
        annotation = self.selected_annotation()
        if isinstance(
            annotation, (RectangleAnnotation, ArrowAnnotation)
        ):
            annotation.line_style = style
            self._commit_history()
            self.update()

    def set_font_family(self, family: str) -> None:
        self._font_family = family
        annotation = self.selected_annotation()
        if isinstance(annotation, TextAnnotation):
            annotation.font_family = family
            self._commit_history()
            self.update()

    def set_italic(self, enabled: bool) -> None:
        self._italic = enabled
        annotation = self.selected_annotation()
        if isinstance(annotation, TextAnnotation):
            annotation.italic = enabled
            self._commit_history()
            self.update()

    def set_outline_enabled(self, enabled: bool) -> None:
        self._outline_enabled = enabled
        annotation = self.selected_annotation()
        if isinstance(annotation, TextAnnotation):
            annotation.outline_enabled = enabled
            self._commit_history()
            self.update()

    def set_outline_color(self, color: QColor) -> None:
        self._outline_color = color.name()
        annotation = self.selected_annotation()
        if isinstance(annotation, TextAnnotation):
            annotation.outline_color = self._outline_color
            self._commit_history()
            self.update()

    def set_background_enabled(self, enabled: bool) -> None:
        self._background_enabled = enabled
        annotation = self.selected_annotation()
        if isinstance(annotation, TextAnnotation):
            annotation.background_enabled = enabled
            self._commit_history()
            self.update()

    def selected_annotation(self) -> Annotation | None:
        if (
            self._selected_index is None
            or self._selected_index >= len(self._annotations)
        ):
            return None
        return self._annotations[self._selected_index]

    def delete_selected(self) -> None:
        if self._inline_editor is not None:
            return
        selected = self.selected_annotation()
        if selected is None:
            return
        rebuild_mosaic = isinstance(selected, MosaicAnnotation)
        del self._annotations[self._selected_index]  # type: ignore[index]
        self._selected_index = None
        self.selection_changed.emit(False)
        self._commit_history()
        if rebuild_mosaic:
            self._rebuild_mosaic_preview()
        self._sync_caption_number()
        self.update()

    def duplicate_selected(self) -> None:
        annotation = self.selected_annotation()
        if annotation is None:
            return
        clone = self._clone_annotations([annotation])[0]
        self._translate_annotation(clone, QPointF(12, 12))
        self._annotations.append(clone)
        self._selected_index = len(self._annotations) - 1
        self.selection_changed.emit(True)
        self._commit_history()
        if isinstance(clone, MosaicAnnotation):
            self._rebuild_mosaic_preview()
        self.update()

    def _rebuild_mosaic_preview(self) -> None:
        mosaics = [
            annotation
            for annotation in self._annotations
            if isinstance(annotation, MosaicAnnotation)
        ]
        if not mosaics:
            self._mosaic_preview = self._base
            return
        preview = self._base.copy()
        for annotation in mosaics:
            self._apply_mosaic(preview, annotation.rect)
        self._mosaic_preview = preview

    def _sync_caption_number(self) -> None:
        numbers = [
            annotation.number
            for annotation in self._annotations
            if isinstance(annotation, CaptionAnnotation)
        ]
        self._caption_number = max(numbers, default=0) + 1

    @staticmethod
    def _caption_text(number: int) -> str:
        if 1 <= number <= len(CIRCLED_NUMBERS):
            return CIRCLED_NUMBERS[number - 1]
        return str(number)

    def set_grid_enabled(self, enabled: bool) -> None:
        self._grid_enabled = enabled
        self.update()

    def zoom_in(self) -> None:
        self._set_zoom(self._zoom * 1.2)

    def zoom_out(self) -> None:
        self._set_zoom(self._zoom / 1.2)

    def fit_image(self) -> None:
        self._zoom = 1.0
        self._pan = QPointF()
        self.zoom_changed.emit(self.current_zoom_percent())
        self._position_inline_editor()
        self.update()

    def show_100_percent(self) -> None:
        self._zoom = 1.0 / max(self._fit_scale(), 0.01)
        self._pan = QPointF()
        self.zoom_changed.emit(100)
        self._position_inline_editor()
        self.update()

    def current_zoom_percent(self) -> int:
        return round(self._fit_scale() * self._zoom * 100)

    def _set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.25, min(zoom, 6.0))
        self.zoom_changed.emit(self.current_zoom_percent())
        self._position_inline_editor()
        self.update()

    @staticmethod
    def _clone_annotations(
        annotations: list[Annotation],
    ) -> list[Annotation]:
        cloned: list[Annotation] = []
        for annotation in annotations:
            if isinstance(annotation, CaptionAnnotation):
                cloned.append(
                    CaptionAnnotation(
                        annotation.text,
                        QPointF(annotation.position),
                        annotation.color,
                        annotation.font_size,
                        annotation.bold,
                        annotation.font_family,
                        annotation.italic,
                        annotation.outline_enabled,
                        annotation.outline_color,
                        annotation.background_enabled,
                        annotation.background_color,
                        annotation.background_opacity,
                        annotation.number,
                    )
                )
            elif isinstance(annotation, TextAnnotation):
                cloned.append(
                    TextAnnotation(
                        annotation.text,
                        QPointF(annotation.position),
                        annotation.color,
                        annotation.font_size,
                        annotation.bold,
                        annotation.font_family,
                        annotation.italic,
                        annotation.outline_enabled,
                        annotation.outline_color,
                        annotation.background_enabled,
                        annotation.background_color,
                        annotation.background_opacity,
                    )
                )
            elif isinstance(annotation, RectangleAnnotation):
                cloned.append(
                    RectangleAnnotation(
                        QRectF(annotation.rect),
                        annotation.color,
                        annotation.line_width,
                        annotation.fill_enabled,
                        annotation.fill_opacity,
                        annotation.rounded,
                        annotation.line_opacity,
                        annotation.line_style,
                    )
                )
            elif isinstance(annotation, ArrowAnnotation):
                cloned.append(
                    ArrowAnnotation(
                        QPointF(annotation.start),
                        QPointF(annotation.end),
                        annotation.color,
                        annotation.line_width,
                        annotation.line_opacity,
                        annotation.line_style,
                    )
                )
            elif isinstance(annotation, MosaicAnnotation):
                cloned.append(
                    MosaicAnnotation(QRectF(annotation.rect))
                )
        return cloned

    def can_undo(self) -> bool:
        return self._history_index > 0

    def can_redo(self) -> bool:
        return self._history_index + 1 < len(self._history)

    def _commit_history(self) -> None:
        del self._history[self._history_index + 1 :]
        self._history.append(self._clone_annotations(self._annotations))
        self._history_index += 1
        self.history_changed.emit(self.can_undo(), self.can_redo())
        self.changed.emit()

    def undo(self) -> None:
        if not self.can_undo():
            return
        self._history_index -= 1
        self._annotations = self._clone_annotations(
            self._history[self._history_index]
        )
        self._rebuild_mosaic_preview()
        self._sync_caption_number()
        self._normalize_selection()
        self.history_changed.emit(self.can_undo(), self.can_redo())
        self.changed.emit()
        self.update()

    def redo(self) -> None:
        if not self.can_redo():
            return
        self._history_index += 1
        self._annotations = self._clone_annotations(
            self._history[self._history_index]
        )
        self._rebuild_mosaic_preview()
        self._sync_caption_number()
        self._normalize_selection()
        self.history_changed.emit(self.can_undo(), self.can_redo())
        self.changed.emit()
        self.update()

    def _normalize_selection(self) -> None:
        if (
            self._selected_index is not None
            and self._selected_index >= len(self._annotations)
        ):
            self._selected_index = None
        self.selection_changed.emit(
            self._selected_index is not None
        )

    def _display_rect(self) -> QRectF:
        margin = 24.0
        available = QRectF(self.rect()).adjusted(
            margin, margin, -margin, -margin
        )
        size = self._base.size()
        scale = self._fit_scale()
        width = size.width() * scale * self._zoom
        height = size.height() * scale * self._zoom
        return QRectF(
            available.center().x() - width / 2 + self._pan.x(),
            available.center().y() - height / 2 + self._pan.y(),
            width,
            height,
        )

    def _fit_scale(self) -> float:
        margin = 24.0
        available = QRectF(self.rect()).adjusted(
            margin, margin, -margin, -margin
        )
        if self._base.width() <= 0 or self._base.height() <= 0:
            return 1.0
        return max(
            0.01,
            min(
                available.width() / self._base.width(),
                available.height() / self._base.height(),
                1.0,
            ),
        )

    def _to_image(self, point: QPointF) -> QPointF | None:
        shown = self._display_rect()
        if not shown.contains(point):
            return None
        return QPointF(
            (point.x() - shown.left())
            * self._base.width()
            / shown.width(),
            (point.y() - shown.top())
            * self._base.height()
            / shown.height(),
        )

    def _to_widget(self, point: QPointF) -> QPointF:
        shown = self._display_rect()
        return QPointF(
            shown.left()
            + point.x() * shown.width() / self._base.width(),
            shown.top()
            + point.y() * shown.height() / self._base.height(),
        )

    def _start_inline_editor(
        self,
        position: QPointF,
        index: int | None = None,
        initial_text: str = "",
    ) -> None:
        if self._inline_editor is not None:
            self._commit_inline_editor()
        self._editing_index = index
        self._editing_position = QPointF(position)
        self._editing_original_text = initial_text
        self._inline_finishing = False
        self._inline_focus_pending = True
        self._dragged_index = None
        self._drag_origin = None
        self._drag_original = None

        editor = InlineTextEditor(self)
        editor.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        editor.setPlainText(initial_text)
        editor.setPlaceholderText("")
        editor.setAcceptRichText(False)
        editor.setFrameShape(QFrame.Shape.NoFrame)
        editor.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        editor.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        editor.setCursorWidth(2)
        editor.document().setDocumentMargin(0)
        editor.setContentsMargins(0, 0, 0, 0)
        editor.viewport().setAutoFillBackground(False)
        style = self._editing_style()
        preview_color = QColor(style.color)
        if preview_color.lightness() < 95:
            background = "rgba(255, 255, 255, 135)"
            border = "rgba(96, 165, 250, 150)"
        else:
            background = "rgba(17, 24, 39, 100)"
            border = "rgba(96, 165, 250, 145)"
        editor.setStyleSheet(
            f"QTextEdit {{ color: {preview_color.name()};"
            f" background: {background};"
            f" border: 1px solid {border}; border-radius: 6px;"
            " padding: 3px 5px;"
            " selection-color: #ffffff;"
            " selection-background-color: #2563eb; }"
            "QScrollBar { width: 0px; height: 0px; }"
        )
        editor.committed.connect(self._commit_inline_editor)
        editor.canceled.connect(self._cancel_inline_editor)
        editor.focus_committed.connect(self._commit_inline_editor)
        editor.textChanged.connect(self._position_inline_editor)
        self._inline_editor = editor
        self._position_inline_editor()
        editor.show()
        editor.raise_()
        if initial_text:
            editor.selectAll()
        self.update()

    def _activate_inline_editor(self) -> None:
        if self._inline_editor is None:
            return
        self._inline_editor.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus
        )
        self._inline_editor.raise_()
        self._inline_editor.setFocus(
            Qt.FocusReason.MouseFocusReason
        )
        self._inline_focus_pending = False

    def _editing_style(self) -> TextAnnotation:
        if self._editing_index is not None:
            annotation = self._annotations[self._editing_index]
            if isinstance(annotation, TextAnnotation):
                return annotation
        return TextAnnotation(
            "",
            self._editing_position or QPointF(),
            self._color,
            self._font_size,
            self._bold,
            self._font_family,
            self._italic,
            self._outline_enabled,
            self._outline_color,
            self._background_enabled,
        )

    def _position_inline_editor(self) -> None:
        if (
            self._inline_editor is None
            or self._editing_position is None
        ):
            return
        shown = self._display_rect()
        scale = shown.width() / max(1, self._base.width())
        annotation = self._editing_style()
        font = QFont(annotation.font_family)
        font.setPixelSize(
            max(12, round(annotation.font_size * scale))
        )
        font.setBold(annotation.bold)
        font.setItalic(annotation.italic)
        self._inline_editor.setFont(font)
        metrics = QFontMetricsF(font)
        lines = (
            self._inline_editor.toPlainText() or " "
        ).split("\n")
        text_width = max(
            metrics.horizontalAdvance(line or " ")
            for line in lines
        )
        widget_point = self._to_widget(self._editing_position)
        available_width = max(80, self.width() - round(widget_point.x()) - 12)
        width = max(80, min(round(text_width + 20), available_width))
        height = max(
            28,
            round(metrics.height() * min(len(lines), 8) + 8),
        )
        self._inline_editor.setGeometry(
            round(widget_point.x()),
            round(widget_point.y()),
            width,
            height,
        )

    def _commit_inline_editor(self) -> None:
        if self._inline_editor is None:
            return
        if self._inline_finishing:
            return
        self._inline_finishing = True
        text = self._inline_editor.toPlainText().strip()
        index = self._editing_index
        position = QPointF(self._editing_position or QPointF())
        changed = False
        if text:
            if index is None:
                annotation = self._editing_style()
                annotation.text = text
                annotation.position = position
                self._annotations.append(annotation)
                index = len(self._annotations) - 1
                changed = True
            else:
                annotation = self._annotations[index]
                if (
                    isinstance(annotation, TextAnnotation)
                    and annotation.text != text
                ):
                    annotation.text = text
                    changed = True
        self._close_inline_editor()
        if index is not None:
            self._selected_index = index
            self.selection_changed.emit(True)
        if changed:
            self._commit_history()
        self.set_tool(Tool.SELECT)
        self.tool_change_requested.emit(Tool.SELECT)
        self.update()

    def commit_inline_editing(self) -> None:
        if self._inline_editor is not None:
            self._commit_inline_editor()

    def _cancel_inline_editor(self) -> None:
        if self._inline_editor is None:
            return
        if self._inline_finishing:
            return
        self._inline_finishing = True
        self._close_inline_editor()
        self.update()

    def _close_inline_editor(self) -> None:
        editor = self._inline_editor
        self._inline_editor = None
        self._editing_index = None
        self._editing_position = None
        self._editing_original_text = ""
        self._inline_focus_pending = False
        if editor is not None:
            editor.hide()
            editor.deleteLater()

    @staticmethod
    def _text_font(annotation: TextAnnotation) -> QFont:
        font = QFont(annotation.font_family)
        font.setPixelSize(annotation.font_size)
        font.setBold(annotation.bold)
        font.setItalic(annotation.italic)
        return font

    @classmethod
    def _text_rect(cls, annotation: TextAnnotation) -> QRectF:
        metrics = QFontMetricsF(cls._text_font(annotation))
        lines = annotation.text.split("\n") or [""]
        width = max(
            metrics.horizontalAdvance(line or " ")
            for line in lines
        )
        return QRectF(
            annotation.position.x(),
            annotation.position.y(),
            width,
            metrics.height() * len(lines),
        )

    @classmethod
    def _text_path(cls, annotation: TextAnnotation) -> QPainterPath:
        font = cls._text_font(annotation)
        metrics = QFontMetricsF(font)
        path = QPainterPath()
        for line_number, line in enumerate(annotation.text.split("\n")):
            if not line:
                continue
            baseline = annotation.position + QPointF(
                0,
                metrics.ascent() + line_number * metrics.height(),
            )
            path.addText(baseline, font, line)
        return path

    def _text_at(self, point: QPointF) -> TextAnnotation | None:
        for annotation in reversed(self._annotations):
            if (
                isinstance(annotation, TextAnnotation)
                and self._text_rect(annotation)
                .adjusted(-8, -8, 8, 8)
                .contains(point)
            ):
                return annotation
        return None

    def _annotation_bounds(self, annotation: Annotation) -> QRectF:
        if isinstance(annotation, TextAnnotation):
            return self._text_rect(annotation)
        if isinstance(annotation, RectangleAnnotation):
            return QRectF(annotation.rect)
        if isinstance(annotation, ArrowAnnotation):
            return QRectF(
                annotation.start, annotation.end
            ).normalized()
        return QRectF(annotation.rect)

    @staticmethod
    def _distance_to_segment(
        point: QPointF, start: QPointF, end: QPointF
    ) -> float:
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length_squared = dx * dx + dy * dy
        if length_squared == 0:
            return math.hypot(
                point.x() - start.x(), point.y() - start.y()
            )
        t = max(
            0.0,
            min(
                1.0,
                (
                    (point.x() - start.x()) * dx
                    + (point.y() - start.y()) * dy
                )
                / length_squared,
            ),
        )
        nearest = QPointF(start.x() + t * dx, start.y() + t * dy)
        return math.hypot(
            point.x() - nearest.x(), point.y() - nearest.y()
        )

    def _annotation_at(self, point: QPointF) -> int | None:
        for index in range(len(self._annotations) - 1, -1, -1):
            annotation = self._annotations[index]
            if isinstance(annotation, TextAnnotation):
                hit = self._text_rect(annotation).adjusted(
                    -8, -8, 8, 8
                ).contains(point)
            elif isinstance(annotation, ArrowAnnotation):
                hit = self._distance_to_segment(
                    point, annotation.start, annotation.end
                ) <= max(8, annotation.line_width + 4)
            else:
                hit = self._annotation_bounds(annotation).adjusted(
                    -8, -8, 8, 8
                ).contains(point)
            if hit:
                return index
        return None

    @staticmethod
    def _translate_annotation(
        annotation: Annotation, delta: QPointF
    ) -> None:
        if isinstance(annotation, TextAnnotation):
            annotation.position += delta
        elif isinstance(annotation, RectangleAnnotation):
            annotation.rect.translate(delta)
        elif isinstance(annotation, ArrowAnnotation):
            annotation.start += delta
            annotation.end += delta
        elif isinstance(annotation, MosaicAnnotation):
            annotation.rect.translate(delta)

    @staticmethod
    def _square_point(start: QPointF, point: QPointF) -> QPointF:
        dx = point.x() - start.x()
        dy = point.y() - start.y()
        side = max(abs(dx), abs(dy))
        return QPointF(
            start.x() + (side if dx >= 0 else -side),
            start.y() + (side if dy >= 0 else -side),
        )

    def _select_and_begin_drag(
        self, index: int, point: QPointF
    ) -> None:
        self._selected_index = index
        self.selection_changed.emit(True)
        self._dragged_index = index
        self._drag_origin = QPointF(point)
        self._drag_original = self._clone_annotations(
            [self._annotations[index]]
        )[0]
        self.update()

    def _handle_points(
        self, annotation: Annotation
    ) -> dict[str, QPointF]:
        if isinstance(annotation, ArrowAnnotation):
            return {
                "start": QPointF(annotation.start),
                "end": QPointF(annotation.end),
            }
        bounds = self._annotation_bounds(annotation)
        return {
            "tl": bounds.topLeft(),
            "tr": bounds.topRight(),
            "bl": bounds.bottomLeft(),
            "br": bounds.bottomRight(),
        }

    def _handle_radius(self) -> float:
        shown = self._display_rect()
        scale = shown.width() / max(1, self._base.width())
        return max(3.0, 6.0 / max(scale, 0.01))

    def _handle_at(self, point: QPointF) -> str | None:
        annotation = self.selected_annotation()
        if annotation is None:
            return None
        radius = self._handle_radius() * 1.5
        for name, handle_point in self._handle_points(
            annotation
        ).items():
            if math.hypot(
                point.x() - handle_point.x(),
                point.y() - handle_point.y(),
            ) <= radius:
                return name
        return None

    def _begin_resize(self, handle: str, point: QPointF) -> None:
        if self._selected_index is None:
            return
        self._resize_handle = handle
        self._drag_origin = QPointF(point)
        self._drag_original = self._clone_annotations(
            [self._annotations[self._selected_index]]
        )[0]

    def _resized_annotation(
        self,
        original: Annotation,
        handle: str,
        point: QPointF,
    ) -> Annotation:
        clone = self._clone_annotations([original])[0]
        if isinstance(clone, ArrowAnnotation):
            if handle == "start":
                clone.start = QPointF(point)
            elif handle == "end":
                clone.end = QPointF(point)
        elif isinstance(clone, (RectangleAnnotation, MosaicAnnotation)):
            rect = QRectF(clone.rect)
            if "l" in handle:
                rect.setLeft(point.x())
            if "r" in handle:
                rect.setRight(point.x())
            if "t" in handle:
                rect.setTop(point.y())
            if "b" in handle:
                rect.setBottom(point.y())
            clone.rect = rect.normalized()
        elif isinstance(clone, TextAnnotation):
            bounds = self._text_rect(original)
            anchors = {
                "tl": bounds.bottomRight(),
                "tr": bounds.bottomLeft(),
                "bl": bounds.topRight(),
                "br": bounds.topLeft(),
            }
            anchor = anchors.get(handle, bounds.topLeft())
            original_handle = self._handle_points(original).get(
                handle, bounds.bottomRight()
            )
            original_distance = max(
                1.0,
                math.hypot(
                    original_handle.x() - anchor.x(),
                    original_handle.y() - anchor.y(),
                ),
            )
            new_distance = max(
                1.0,
                math.hypot(
                    point.x() - anchor.x(),
                    point.y() - anchor.y(),
                ),
            )
            clone.font_size = max(
                8,
                min(
                    240,
                    round(
                        original.font_size
                        * new_distance
                        / original_distance
                    ),
                ),
            )
            new_size = self._text_rect(clone).size()
            if handle == "tl":
                clone.position = anchor - QPointF(
                    new_size.width(), new_size.height()
                )
            elif handle == "tr":
                clone.position = QPointF(
                    anchor.x(), anchor.y() - new_size.height()
                )
            elif handle == "bl":
                clone.position = QPointF(
                    anchor.x() - new_size.width(), anchor.y()
                )
            else:
                clone.position = QPointF(anchor)
        return clone

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._inline_editor is not None:
            if self._inline_editor.geometry().contains(
                event.position().toPoint()
            ):
                return
            self._commit_inline_editor()
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        if self._space_pressed:
            self._panning = True
            self._pan_mouse_start = event.position()
            self._pan_start = QPointF(self._pan)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        point = self._to_image(event.position())
        if point is None:
            return

        if self._tool == Tool.SELECT:
            handle = self._handle_at(point)
            if handle is not None:
                self._begin_resize(handle, point)
                return
            index = self._annotation_at(point)
            self._selected_index = index
            self.selection_changed.emit(index is not None)
            if index is not None:
                self._select_and_begin_drag(index, point)
            else:
                self.update()
            return

        if self._tool == Tool.TEXT:
            index = self._annotation_at(point)
            if (
                index is not None
                and isinstance(
                    self._annotations[index], TextAnnotation
                )
            ):
                self._select_and_begin_drag(index, point)
                return

            self._start_inline_editor(point)
            return

        if self._tool == Tool.CAPTION:
            number = self._caption_number
            self._annotations.append(
                CaptionAnnotation(
                    self._caption_text(number),
                    point,
                    self._color,
                    max(28, self._font_size),
                    True,
                    self._font_family,
                    self._italic,
                    self._outline_enabled,
                    self._outline_color,
                    self._background_enabled,
                    "#000000",
                    150,
                    number,
                )
            )
            self._caption_number += 1
            self._selected_index = len(self._annotations) - 1
            self.selection_changed.emit(True)
            self._commit_history()
            self.update()
            return

        self._start = point
        self._current = point

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            self._pan = self._pan_start + (
                event.position() - self._pan_mouse_start
            )
            self._position_inline_editor()
            self.update()
            return

        point = self._to_image(event.position())
        if point is None:
            return
        if (
            self._resize_handle is not None
            and self._selected_index is not None
            and self._drag_original is not None
        ):
            self._annotations[self._selected_index] = (
                self._resized_annotation(
                    self._drag_original,
                    self._resize_handle,
                    point,
                )
            )
            self.update()
        elif (
            self._dragged_index is not None
            and self._drag_origin is not None
            and self._drag_original is not None
        ):
            clone = self._clone_annotations(
                [self._drag_original]
            )[0]
            self._translate_annotation(
                clone, point - self._drag_origin
            )
            self._annotations[self._dragged_index] = clone
            self.update()
        elif self._start is not None:
            self._current = (
                self._square_point(self._start, point)
                if self._tool == Tool.RECTANGLE
                and bool(
                    event.modifiers()
                    & Qt.KeyboardModifier.ShiftModifier
                )
                else point
            )
            self.update()
        elif self._tool == Tool.SELECT:
            handle = self._handle_at(point)
            if handle in {"tl", "br"}:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handle in {"tr", "bl"}:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif handle in {"start", "end"}:
                self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if (
            self._inline_editor is not None
            and self._inline_focus_pending
        ):
            self._activate_inline_editor()
            return

        if self._panning:
            self._panning = False
            self.set_tool(self._tool)
            return

        if self._resize_handle is not None:
            resized_mosaic = isinstance(
                self._drag_original, MosaicAnnotation
            )
            changed = (
                self._selected_index is not None
                and self._drag_original is not None
                and self._annotations[self._selected_index]
                != self._drag_original
            )
            self._resize_handle = None
            self._drag_origin = None
            self._drag_original = None
            if changed:
                self._commit_history()
                if resized_mosaic:
                    self._rebuild_mosaic_preview()
            return

        if self._dragged_index is not None:
            moved_mosaic = isinstance(
                self._drag_original, MosaicAnnotation
            )
            moved = (
                self._drag_original is not None
                and self._annotations[self._dragged_index]
                != self._drag_original
            )
            self._dragged_index = None
            self._drag_origin = None
            self._drag_original = None
            if moved:
                self._commit_history()
                if moved_mosaic:
                    self._rebuild_mosaic_preview()
            return

        point = self._to_image(event.position())
        if self._start is None or point is None:
            self._start = None
            self._current = None
            self.update()
            return

        start = self._start
        self._current = (
            self._square_point(self._start, point)
            if self._tool == Tool.RECTANGLE
            and bool(
                event.modifiers()
                & Qt.KeyboardModifier.ShiftModifier
            )
            else point
        )
        point = self._current
        rect = QRectF(start, point).normalized()
        created = False

        if (
            self._tool == Tool.RECTANGLE
            and rect.width() >= 3
            and rect.height() >= 3
        ):
            self._annotations.append(
                RectangleAnnotation(
                    rect,
                    self._color,
                    self._line_width,
                    self._fill_enabled,
                    round(self._fill_opacity * 255 / 100),
                    self._rounded,
                    round(self._line_opacity * 255 / 100),
                    self._line_style,
                )
            )
            created = True
        elif (
            self._tool == Tool.ARROW
            and (point - start).manhattanLength() >= 3
        ):
            self._annotations.append(
                ArrowAnnotation(
                    start,
                    point,
                    self._color,
                    self._line_width,
                    round(self._line_opacity * 255 / 100),
                    self._line_style,
                )
            )
            created = True
        elif (
            self._tool == Tool.MOSAIC
            and rect.width() >= 3
            and rect.height() >= 3
        ):
            self._annotations.append(MosaicAnnotation(rect))
            created = True

        self._start = None
        self._current = None
        if created:
            self._selected_index = len(self._annotations) - 1
            self.selection_changed.emit(True)
            self._commit_history()
            if self._tool == Tool.MOSAIC:
                self._rebuild_mosaic_preview()
        self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = self._to_image(event.position())
        if point is None:
            return
        index = self._annotation_at(point)
        if index is None:
            return
        annotation = self._annotations[index]
        if not isinstance(annotation, TextAnnotation):
            return
        self._selected_index = index
        self.selection_changed.emit(True)
        self._start_inline_editor(
            annotation.position,
            index,
            annotation.text,
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if (
            event.key() == Qt.Key.Key_Escape
            and self._tool == Tool.CAPTION
        ):
            self.set_tool(Tool.SELECT)
            self.tool_change_requested.emit(Tool.SELECT)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
            return
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = False
            if not self._panning:
                self.set_tool(self._tool)
            return
        super().keyReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if bool(
            event.modifiers()
            & Qt.KeyboardModifier.ControlModifier
        ):
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self._set_zoom(self._zoom * factor)
            event.accept()
            return
        super().wheelEvent(event)

    def render_image(
        self,
        include_preview: bool = False,
        include_selection: bool = False,
    ) -> QImage:
        result = self._base.copy()
        annotations = list(self._annotations)

        if (
            include_preview
            and self._start is not None
            and self._current is not None
        ):
            rect = QRectF(
                self._start, self._current
            ).normalized()
            if self._tool == Tool.RECTANGLE:
                annotations.append(
                    RectangleAnnotation(
                        rect,
                        self._color,
                        self._line_width,
                        self._fill_enabled,
                        round(self._fill_opacity * 255 / 100),
                        self._rounded,
                        round(self._line_opacity * 255 / 100),
                        self._line_style,
                    )
                )
            elif self._tool == Tool.ARROW:
                annotations.append(
                    ArrowAnnotation(
                        self._start,
                        self._current,
                        self._color,
                        self._line_width,
                        round(self._line_opacity * 255 / 100),
                        self._line_style,
                    )
                )
            elif self._tool == Tool.MOSAIC:
                annotations.append(MosaicAnnotation(rect))

        for annotation in annotations:
            if isinstance(annotation, MosaicAnnotation):
                self._apply_mosaic(result, annotation.rect)

        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for annotation in annotations:
            if isinstance(annotation, RectangleAnnotation):
                if annotation.fill_enabled:
                    fill = QColor(annotation.color)
                    fill.setAlpha(annotation.fill_opacity)
                    painter.setBrush(fill)
                else:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                line = QColor(annotation.color)
                line.setAlpha(annotation.line_opacity)
                painter.setPen(
                    QPen(
                        line,
                        annotation.line_width,
                        self._pen_style(annotation.line_style),
                        Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin,
                    )
                )
                if annotation.rounded:
                    painter.drawRoundedRect(annotation.rect, 12, 12)
                else:
                    painter.drawRect(annotation.rect)
            elif isinstance(annotation, ArrowAnnotation):
                self._paint_arrow(painter, annotation)
            elif isinstance(annotation, TextAnnotation):
                if annotation.background_enabled:
                    background = QColor(annotation.background_color)
                    background.setAlpha(annotation.background_opacity)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(background)
                    painter.drawRoundedRect(
                        self._text_rect(annotation).adjusted(
                            -8, -5, 8, 5
                        ),
                        5,
                        5,
                    )
                path = self._text_path(annotation)
                if annotation.outline_enabled:
                    painter.setPen(
                        QPen(
                            QColor(annotation.outline_color),
                            5,
                            Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin,
                        )
                    )
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(annotation.color))
                painter.drawPath(path)

        if include_selection:
            selected = self.selected_annotation()
            if selected is not None:
                bounds = self._annotation_bounds(selected).adjusted(
                    -5, -5, 5, 5
                )
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(
                    QPen(
                        QColor("#2f80ed"),
                        2,
                        Qt.PenStyle.DashLine,
                    )
                )
                painter.drawRect(bounds)
                radius = self._handle_radius()
                painter.setPen(QPen(QColor("#2f80ed"), 2))
                painter.setBrush(Qt.GlobalColor.white)
                for point in self._handle_points(selected).values():
                    painter.drawRect(
                        QRectF(
                            point.x() - radius,
                            point.y() - radius,
                            radius * 2,
                            radius * 2,
                        )
                    )

        painter.end()
        return result

    @staticmethod
    def _pen_style(style: str) -> Qt.PenStyle:
        return {
            "dash": Qt.PenStyle.DashLine,
            "dot": Qt.PenStyle.DotLine,
        }.get(style, Qt.PenStyle.SolidLine)

    @staticmethod
    def _apply_mosaic(image: QImage, rect: QRectF) -> None:
        bounded = rect.toAlignedRect().intersected(
            image.rect()
        )
        if bounded.isEmpty():
            return

        source = image.copy(bounded)
        block = 12
        tiny = source.scaled(
            max(1, source.width() // block),
            max(1, source.height() // block),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        pixelated = tiny.scaled(
            source.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        painter = QPainter(image)
        painter.drawImage(bounded, pixelated)
        painter.end()

    @staticmethod
    def _paint_arrow(
        painter: QPainter,
        annotation: ArrowAnnotation,
    ) -> None:
        color = QColor(annotation.color)
        color.setAlpha(annotation.line_opacity)
        painter.setPen(
            QPen(
                color,
                annotation.line_width,
                AnnotationCanvas._pen_style(annotation.line_style),
                Qt.PenCapStyle.RoundCap,
            )
        )
        painter.setBrush(color)
        painter.drawLine(annotation.start, annotation.end)

        angle = math.atan2(
            annotation.end.y() - annotation.start.y(),
            annotation.end.x() - annotation.start.x(),
        )
        size = max(14.0, annotation.line_width * 4.0)
        left = annotation.end - QPointF(
            math.cos(angle - 0.55) * size,
            math.sin(angle - 0.55) * size,
        )
        right = annotation.end - QPointF(
            math.cos(angle + 0.55) * size,
            math.sin(angle + 0.55) * size,
        )
        painter.drawPolygon(
            QPolygonF([annotation.end, left, right])
        )

    def _preview_annotations(self) -> list[Annotation]:
        annotations = [
            annotation
            for index, annotation in enumerate(self._annotations)
            if index != self._editing_index
        ]
        if self._start is None or self._current is None:
            return annotations
        rect = QRectF(self._start, self._current).normalized()
        if self._tool == Tool.RECTANGLE:
            annotations.append(
                RectangleAnnotation(
                    rect,
                    self._color,
                    self._line_width,
                    self._fill_enabled,
                    round(self._fill_opacity * 255 / 100),
                    self._rounded,
                    round(self._line_opacity * 255 / 100),
                    self._line_style,
                )
            )
        elif self._tool == Tool.ARROW:
            annotations.append(
                ArrowAnnotation(
                    self._start,
                    self._current,
                    self._color,
                    self._line_width,
                    round(self._line_opacity * 255 / 100),
                    self._line_style,
                )
            )
        return annotations

    def _paint_preview_annotations(
        self, painter: QPainter
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for annotation in self._preview_annotations():
            if isinstance(annotation, RectangleAnnotation):
                if annotation.fill_enabled:
                    fill = QColor(annotation.color)
                    fill.setAlpha(annotation.fill_opacity)
                    painter.setBrush(fill)
                else:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                line = QColor(annotation.color)
                line.setAlpha(annotation.line_opacity)
                painter.setPen(
                    QPen(
                        line,
                        annotation.line_width,
                        self._pen_style(annotation.line_style),
                        Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin,
                    )
                )
                if annotation.rounded:
                    painter.drawRoundedRect(annotation.rect, 12, 12)
                else:
                    painter.drawRect(annotation.rect)
            elif isinstance(annotation, ArrowAnnotation):
                self._paint_arrow(painter, annotation)
            elif isinstance(annotation, TextAnnotation):
                if annotation.background_enabled:
                    background = QColor(annotation.background_color)
                    background.setAlpha(annotation.background_opacity)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(background)
                    painter.drawRoundedRect(
                        self._text_rect(annotation).adjusted(
                            -8, -5, 8, 5
                        ),
                        5,
                        5,
                    )
                path = self._text_path(annotation)
                if annotation.outline_enabled:
                    painter.setPen(
                        QPen(
                            QColor(annotation.outline_color),
                            5,
                            Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin,
                        )
                    )
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(annotation.color))
                painter.drawPath(path)

        if self._inline_editor is not None:
            return
        selected = self.selected_annotation()
        if selected is None:
            return
        bounds = self._annotation_bounds(selected).adjusted(
            -5, -5, 5, 5
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(
            QPen(QColor("#2f80ed"), 2, Qt.PenStyle.DashLine)
        )
        painter.drawRect(bounds)
        radius = self._handle_radius()
        painter.setPen(QPen(QColor("#2f80ed"), 2))
        painter.setBrush(Qt.GlobalColor.white)
        for point in self._handle_points(selected).values():
            painter.drawRect(
                QRectF(
                    point.x() - radius,
                    point.y() - radius,
                    radius * 2,
                    radius * 2,
                )
            )

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform, True
        )
        painter.fillRect(self.rect(), QColor("#0f141c"))
        shown = self._display_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 20))
        painter.drawRoundedRect(
            shown.adjusted(-4, -2, 4, 7), 3, 3
        )
        painter.setBrush(QColor(0, 0, 0, 28))
        painter.drawRoundedRect(
            shown.adjusted(-2, 0, 2, 4), 2, 2
        )
        painter.drawImage(shown, self._mosaic_preview)
        painter.save()
        painter.setClipRect(shown)
        painter.translate(shown.left(), shown.top())
        painter.scale(
            shown.width() / self._base.width(),
            shown.height() / self._base.height(),
        )
        self._paint_preview_annotations(painter)
        painter.restore()
        if self._grid_enabled:
            scale = shown.width() / self._base.width()
            step = max(8.0, 50.0 * scale)
            painter.setPen(QPen(QColor(255, 255, 255, 70), 1))
            x = shown.left()
            while x <= shown.right():
                painter.drawLine(
                    QPointF(x, shown.top()),
                    QPointF(x, shown.bottom()),
                )
                x += step
            y = shown.top()
            while y <= shown.bottom():
                painter.drawLine(
                    QPointF(shown.left(), y),
                    QPointF(shown.right(), y),
                )
                y += step

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        self.zoom_changed.emit(self.current_zoom_percent())
        self._position_inline_editor()
