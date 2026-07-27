from __future__ import annotations

import ctypes
import sys


def enable_per_monitor_dpi_awareness() -> None:
    if sys.platform != "win32":
        return

    try:
        awareness_context_per_monitor_v2 = ctypes.c_void_p(-4)
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(
            awareness_context_per_monitor_v2
        ):
            return
    except Exception:
        pass

    try:
        process_per_monitor_dpi_aware = 2
        ctypes.windll.shcore.SetProcessDpiAwareness(
            process_per_monitor_dpi_aware
        )
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
