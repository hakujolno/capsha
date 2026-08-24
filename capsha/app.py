from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication, QImage
from PySide6.QtWidgets import QApplication, QToolTip, QWidget

from capsha.capture import CaptureOverlay, capture_desktop
from capsha.branding import load_brand_icon
from capsha.clipboard import copy_image_to_clipboard
from capsha.editor import EditorWindow
from capsha.image_io import image_path_from_args, load_image
from capsha.window_sync import (
    exclude_window_from_capture,
    flush_compositor,
    hide_process_windows,
    hide_window,
)


RETAKE_SETTLE_DELAY_MS = 70


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
        self._retake_pending = False

    def start_capture(self) -> None:
        self._retake_pending = False
        if self._overlay is not None:
            self._overlay.close()
            self._overlay.deleteLater()
            self._overlay = None
        desktop = capture_desktop()
        self._overlay = CaptureOverlay(desktop)
        self._overlay.captured.connect(self._open_editor)
        self._overlay.cancelled.connect(self.quit)
        self._overlay.show()
        self._overlay.activateWindow()

    def _open_editor(self, image: QImage) -> None:
        self.setQuitOnLastWindowClosed(True)
        copy_image_to_clipboard(image)
        if self._editor is not None:
            self._editor.hide()
            self._editor.deleteLater()
            self._editor = None
        self._editor = EditorWindow(image)
        self._editor.retake_requested.connect(self._retake)
        self._editor.show()
        exclude_window_from_capture(self._editor)
        self._editor.raise_()
        self._editor.activateWindow()
        if self._overlay is not None:
            self._overlay.close()
            self._overlay.deleteLater()
            self._overlay = None

    def open_image_file(self, path: Path) -> bool:
        image = load_image(path)
        if image is None:
            return False
        if self._editor is not None:
            self._editor.hide()
            self._editor.deleteLater()
        self._editor = EditorWindow(image, source_path=path)
        self._editor.retake_requested.connect(self._retake)
        self._editor.show()
        exclude_window_from_capture(self._editor)
        self._editor.raise_()
        self._editor.activateWindow()
        return True

    def _retake(self) -> None:
        if self._retake_pending:
            return
        self._retake_pending = True
        self.setQuitOnLastWindowClosed(False)

        editor = self._editor
        self._hide_capsha_windows(editor)
        self.processEvents()
        flush_compositor()

        if editor is not None:
            editor.deleteLater()
        self._editor = None
        QTimer.singleShot(
            RETAKE_SETTLE_DELAY_MS,
            self._start_retake_capture,
        )

    def _hide_capsha_windows(self, editor: QWidget | None) -> None:
        QToolTip.hideText()
        windows = [
            window
            for window in self.topLevelWidgets()
            if window is not editor
        ]
        if editor is not None:
            windows.append(editor)
        for window in windows:
            exclude_window_from_capture(window)
            hide_window(window)
        hide_process_windows()

    def _start_retake_capture(self) -> None:
        if not self._retake_pending:
            return
        self._hide_capsha_windows(None)
        self.processEvents()
        flush_compositor()
        self.start_capture()


def run() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = CapshaApplication(sys.argv)
    image_path = image_path_from_args(sys.argv[1:])
    if image_path is not None and app.open_image_file(image_path):
        return app.exec()
    app.start_capture()
    return app.exec()
