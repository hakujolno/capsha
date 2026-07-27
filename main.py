if __name__ == "__main__":
    from capsha.dpi import enable_per_monitor_dpi_awareness

    enable_per_monitor_dpi_awareness()

    from capsha.app import run

    raise SystemExit(run())
