# Capsha

<p align="center">
  <img src="capsha/assets/logo.svg" width="120" alt="Capsha Logo">
</p>

<h1 align="center">Capsha</h1>

<p align="center">
<b>Capture. Annotate. Share.</b>
</p>

<p align="center">
Clipboard-first screenshot annotation for Windows.
</p>

<p align="center">

![Platform](https://img.shields.io/badge/Platform-Windows-0078D4)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB)
![License](https://img.shields.io/github/license/hakujolno/capsha)
![Release](https://img.shields.io/github/v/release/hakujolno/capsha)

</p>

---

## Overview

Capsha is a lightweight screenshot annotation tool built for people who share screenshots every day.

Instead of focusing on editing, Capsha focuses on **speed**.

From capture to clipboard, annotation, saving, and sharing, every interaction is designed to minimize clicks.

---

## Features

- ⚡ Instant region capture
- ✏️ Text annotations
- ▭ Rectangle annotations
- ➜ Arrow annotations
- 🟪 Mosaic / Blur
- 📋 Automatic clipboard copy
- 💾 PNG export
- 𝕏 Open X compose page
- 🌐 Japanese / English UI
- 🖥 Multi-monitor support
- 🎨 Modern Windows UI

---

## Philosophy

Most screenshot tools are built to edit images.

Capsha is built to **share them.**

Every feature exists for one reason:

> **Reduce the time between capturing a screenshot and sharing it.**

---

## Screenshots

*(Coming soon)*

---

## Installation

Download the latest release from GitHub Releases.

```
Capsha.exe
```

No installation required.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Esc | Exit |
| Ctrl + Z | Undo |
| Ctrl + Y | Redo |
| Ctrl + C | Copy |
| Ctrl + S | Save |
| Ctrl + Shift + S | Save As |

---

## Building

```bash
git clone https://github.com/hakujolno/capsha.git
cd capsha

python -m venv .venv
pip install -r requirements.txt

python main.py
```

---

## Build Executable

```powershell
scripts/build_release.ps1
```

or

```bash
pyinstaller capsha.spec
```

---

## Roadmap

- [x] Clipboard-first workflow
- [x] Fast annotation
- [x] Multi-language support
- [ ] Automatic updates
- [ ] macOS support
- [ ] OCR
- [ ] AI-assisted captions
- [ ] Plugin-based sharing

---

## Contributing

Issues, Pull Requests, feature requests, and feedback are always welcome.

---

## Support

If Capsha saves you time, consider supporting its development.

☕ Ko-fi *(Coming soon)*

---

## License

MIT License

---

<p align="center">

Made with ❤️ by **trueWhite**

</p>
