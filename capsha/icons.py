from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)


def make_icon(name: str, color: str = "#e5e7eb", size: int = 20) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), max(1.5, size / 12))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    s = float(size)

    if name in {"undo", "redo"}:
        path = QPainterPath()
        if name == "undo":
            path.moveTo(s * .78, s * .72)
            path.cubicTo(s * .82, s * .30, s * .35, s * .25, s * .22, s * .52)
            arrow = QPolygonF([
                QPointF(s * .18, s * .52), QPointF(s * .39, s * .39),
                QPointF(s * .36, s * .64),
            ])
        else:
            path.moveTo(s * .22, s * .72)
            path.cubicTo(s * .18, s * .30, s * .65, s * .25, s * .78, s * .52)
            arrow = QPolygonF([
                QPointF(s * .82, s * .52), QPointF(s * .61, s * .39),
                QPointF(s * .64, s * .64),
            ])
        painter.drawPath(path)
        painter.setBrush(QColor(color))
        painter.drawPolygon(arrow)
    elif name == "select":
        painter.drawPolygon(QPolygonF([
            QPointF(s * .23, s * .14), QPointF(s * .72, s * .60),
            QPointF(s * .49, s * .62), QPointF(s * .61, s * .86),
            QPointF(s * .48, s * .92), QPointF(s * .37, s * .67),
            QPointF(s * .20, s * .83),
        ]))
    elif name == "text":
        painter.drawLine(QPointF(s * .22, s * .22), QPointF(s * .78, s * .22))
        painter.drawLine(QPointF(s * .50, s * .22), QPointF(s * .50, s * .82))
    elif name == "caption":
        painter.drawEllipse(QRectF(s * .14, s * .14, s * .72, s * .72))
        font = QFont("Segoe UI Variable")
        font.setPixelSize(round(s * .50))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(
            QRectF(0, 0, s, s),
            Qt.AlignmentFlag.AlignCenter,
            "1",
        )
    elif name == "rectangle":
        painter.drawRoundedRect(QRectF(s * .15, s * .22, s * .70, s * .56), 2, 2)
    elif name == "arrow":
        painter.drawLine(QPointF(s * .16, s * .76), QPointF(s * .78, s * .23))
        painter.drawLine(QPointF(s * .50, s * .25), QPointF(s * .80, s * .21))
        painter.drawLine(QPointF(s * .78, s * .23), QPointF(s * .75, s * .52))
    elif name == "mosaic":
        for row in range(3):
            for col in range(3):
                painter.drawRect(QRectF(s * (.16 + col * .25), s * (.16 + row * .25), s * .14, s * .14))
    elif name == "save":
        painter.drawRoundedRect(QRectF(s * .18, s * .12, s * .64, s * .76), 2, 2)
        painter.drawRect(QRectF(s * .31, s * .12, s * .37, s * .25))
        painter.drawRoundedRect(QRectF(s * .31, s * .58, s * .38, s * .30), 2, 2)
    elif name == "copy":
        painter.drawRoundedRect(QRectF(s * .28, s * .25, s * .55, s * .59), 2, 2)
        painter.drawRoundedRect(QRectF(s * .15, s * .12, s * .55, s * .59), 2, 2)
    elif name == "close":
        painter.drawLine(QPointF(s * .25, s * .25), QPointF(s * .75, s * .75))
        painter.drawLine(QPointF(s * .75, s * .25), QPointF(s * .25, s * .75))
    elif name == "x":
        painter.drawLine(QPointF(s * .24, s * .18), QPointF(s * .76, s * .82))
        painter.drawLine(QPointF(s * .72, s * .18), QPointF(s * .28, s * .82))
    elif name == "palette":
        painter.setBrush(QColor(color))
        painter.drawEllipse(QRectF(s * .12, s * .16, s * .76, s * .68))
        painter.setBrush(Qt.GlobalColor.transparent)
        painter.drawEllipse(QRectF(s * .58, s * .58, s * .25, s * .25))

    painter.end()
    return QIcon(pixmap)
