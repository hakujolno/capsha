from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QImage
from PySide6.QtWidgets import QApplication

from capsha.capture import CaptureOverlay
from capsha.branding import load_brand_icon
from capsha.clipboard import copy_image_to_clipboard
from capsha.editor import EditorWindow
from capsha.image_io import image_path_from_args, load_image


class CapshaApplication(QApplication):
    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.setApplicationName("Capsha")
        self.setOrganizationName("trueWhite")
        self.setFont(QFont("Segoe UI Variable", 9))
        self.setWindowIcon(load_brand_icon())
        self.setQuitOnLastWindowClosed(True)
        self._overlay: CaptureOverlay | None = None
        self._editor: EditorWindow | None = None

    def start_capture(self) -> None:
        self._overlay = CaptureOverlay()
        self._overlay.captured.connect(self._open_editor)
        self._overlay.cancelled.connect(self.quit)
        self._overlay.show()
        self._overlay.activateWindow()

    def _open_editor(self, image: QImage) -> None:
        copy_image_to_clipboard(image)
        self._editor = EditorWindow(image)
        self._editor.show()
        self._editor.raise_()
        self._editor.activateWindow()
        if self._overlay is not None:
            self._overlay.close()
            self._overlay = None

    def open_image_file(self, path: Path) -> bool:
        image = load_image(path)
        if image is None:
            return False
        self._editor = EditorWindow(image, source_path=path)
        self._editor.show()
        self._editor.raise_()
        self._editor.activateWindow()
        return True


def run() -> int:
    app = CapshaApplication(sys.argv)
    image_path = image_path_from_args(sys.argv[1:])
    if image_path is not None and app.open_image_file(image_path):
        return app.exec()
    app.start_capture()
    return app.exec()
