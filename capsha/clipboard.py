from __future__ import annotations

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QMimeData
from PySide6.QtGui import QGuiApplication, QImage


def copy_image_to_clipboard(image: QImage) -> None:
    image = image.copy()
    image.setDevicePixelRatio(1.0)
    png = QByteArray()
    buffer = QBuffer(png)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG", 100)
    buffer.close()

    mime = QMimeData()
    mime.setImageData(image)
    mime.setData("image/png", png)
    QGuiApplication.clipboard().setMimeData(mime)
