from __future__ import annotations

import ctypes
import os
import sys
from typing import TYPE_CHECKING

from ctypes import wintypes

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


SW_HIDE = 0
WDA_EXCLUDEFROMCAPTURE = 0x00000011


def exclude_window_from_capture(widget: QWidget) -> bool:
    """Ask Windows to omit a top-level Capsha window from captures."""
    if sys.platform != "win32":
        return False
    try:
        hwnd = int(widget.winId())
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        function = user32.SetWindowDisplayAffinity
        function.argtypes = (wintypes.HWND, wintypes.DWORD)
        function.restype = wintypes.BOOL
        return bool(function(hwnd, WDA_EXCLUDEFROMCAPTURE))
    except (AttributeError, OSError, ValueError):
        return False


def hide_window(widget: QWidget) -> None:
    """Hide a Qt window and mirror the request to Win32 when available."""
    hwnd = int(widget.winId()) if sys.platform == "win32" else 0
    widget.hide()
    if not hwnd:
        return
    try:
        ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
    except (AttributeError, OSError):
        pass


def hide_process_windows() -> None:
    """Hide any process-owned top-level windows not exposed by Qt."""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM,
        )
        process_id = os.getpid()

        def hide_if_owned(hwnd: int, _lparam: int) -> bool:
            owner_process_id = wintypes.DWORD()
            user32.GetWindowThreadProcessId(
                hwnd,
                ctypes.byref(owner_process_id),
            )
            if owner_process_id.value == process_id:
                user32.ShowWindow(hwnd, SW_HIDE)
            return True

        user32.EnumWindows(callback_type(hide_if_owned), 0)
    except (AttributeError, OSError, ValueError):
        pass


def flush_compositor() -> None:
    """Wait until DWM has processed pending window composition changes."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.dwmapi.DwmFlush()
    except (AttributeError, OSError):
        pass
