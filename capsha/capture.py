from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QWidget

from capsha.i18n import tr


@dataclass(frozen=True)
class ScreenSnapshot:
    geometry: QRect
    image: QImage
    scale_x: float
    scale_y: float


class CaptureOverlay(QWidget):
    captured = Signal(QImage)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._origin: QPoint | None = None
        self._current: QPoint | None = None
        self._virtual_geometry = self._get_virtual_geometry()
        self._screens = self._capture_screens()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setGeometry(self._virtual_geometry)

    @staticmethod
    def _get_virtual_geometry() -> QRect:
        geometry = QRect()
        for screen in QGuiApplication.screens():
            geometry = geometry.united(screen.geometry())
        return geometry

    @staticmethod
    def _capture_screens() -> list[ScreenSnapshot]:
        snapshots: list[ScreenSnapshot] = []
        for screen in QGuiApplication.screens():
            pixmap = screen.grabWindow(0)
            image = pixmap.toImage().convertToFormat(
                QImage.Format.Format_ARGB32_Premultiplied
            )
            image.setDevicePixelRatio(1.0)
            geometry = screen.geometry()
            snapshots.append(
                ScreenSnapshot(
                    QRect(geometry),
                    image,
                    image.width() / max(1, geometry.width()),
                    image.height() / max(1, geometry.height()),
                )
            )
        return snapshots

    def _global_selection(self, selected: QRect) -> QRect:
        return QRect(
            selected.topLeft() + self._virtual_geometry.topLeft(),
            selected.size(),
        )

    @staticmethod
    def _source_rect(
        area: QRect, snapshot: ScreenSnapshot
    ) -> QRect:
        left = round(
            (area.left() - snapshot.geometry.left())
            * snapshot.scale_x
        )
        top = round(
            (area.top() - snapshot.geometry.top())
            * snapshot.scale_y
        )
        right = round(
            (area.left() + area.width() - snapshot.geometry.left())
            * snapshot.scale_x
        )
        bottom = round(
            (area.top() + area.height() - snapshot.geometry.top())
            * snapshot.scale_y
        )
        return QRect(left, top, right - left, bottom - top)

    def _draw_selected_desktop(
        self, painter: QPainter, selected: QRect
    ) -> None:
        global_selection = self._global_selection(selected)
        for snapshot in self._screens:
            area = global_selection.intersected(snapshot.geometry)
            if area.isEmpty():
                continue
            target = QRectF(
                area.x() - self._virtual_geometry.x(),
                area.y() - self._virtual_geometry.y(),
                area.width(),
                area.height(),
            )
            painter.drawImage(
                target,
                snapshot.image,
                QRectF(self._source_rect(area, snapshot)),
            )

    def _capture_selection(self, selected: QRect) -> QImage:
        global_selection = self._global_selection(selected)
        overlaps = [
            (snapshot, global_selection.intersected(snapshot.geometry))
            for snapshot in self._screens
            if global_selection.intersects(snapshot.geometry)
        ]
        if len(overlaps) == 1:
            snapshot, area = overlaps[0]
            result = snapshot.image.copy(
                self._source_rect(area, snapshot)
            )
            result.setDevicePixelRatio(1.0)
            return result

        scale_x = max(
            (snapshot.scale_x for snapshot, _ in overlaps),
            default=1.0,
        )
        scale_y = max(
            (snapshot.scale_y for snapshot, _ in overlaps),
            default=1.0,
        )
        result = QImage(
            max(1, round(selected.width() * scale_x)),
            max(1, round(selected.height() * scale_y)),
            QImage.Format.Format_ARGB32_Premultiplied,
        )
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        for snapshot, area in overlaps:
            target = QRectF(
                (area.x() - global_selection.x()) * scale_x,
                (area.y() - global_selection.y()) * scale_y,
                area.width() * scale_x,
                area.height() * scale_y,
            )
            painter.drawImage(
                target,
                snapshot.image,
                QRectF(self._source_rect(area, snapshot)),
            )
        painter.end()
        result.setDevicePixelRatio(1.0)
        return result

    def selection(self) -> QRect:
        if self._origin is None or self._current is None:
            return QRect()
        return (
            QRect(self._origin, self._current)
            .normalized()
            .intersected(self.rect())
        )

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 105))
        selected = self.selection()
        if not selected.isEmpty():
            self._draw_selected_desktop(painter, selected)
            painter.setPen(QPen(QColor("#2f80ed"), 2))
            painter.drawRect(selected.adjusted(0, 0, -1, -1))

            label = f"{selected.width()} × {selected.height()}"
            label_rect = QRect(
                selected.left(), max(4, selected.top() - 28), 130, 24
            )
            painter.fillRect(label_rect, QColor(25, 25, 25, 220))
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(
                label_rect.adjusted(8, 0, 0, 0),
                Qt.AlignmentFlag.AlignVCenter,
                label,
            )
        elif self._origin is None:
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                tr("capture_instruction"),
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._current = self._origin
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._origin is not None:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() != Qt.MouseButton.LeftButton
            or self._origin is None
        ):
            return
        self._current = event.position().toPoint()
        selected = self.selection()
        if selected.width() < 2 or selected.height() < 2:
            self._origin = None
            self._current = None
            self.update()
            return

        self.hide()
        self.captured.emit(self._capture_selection(selected))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event: object) -> None:
        super().showEvent(event)  # type: ignore[arg-type]
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
