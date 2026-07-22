from pathlib import Path


project_root = Path(SPECPATH)
assets = project_root / "capsha" / "assets"

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(assets), "capsha/assets")],
    hiddenimports=["PySide6.QtSvg"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "PySide6.QtMultimedia",
        "PySide6.QtNetwork",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
    ],
    noarchive=False,
    optimize=1,
)

unused_files = {
    "PySide6/Qt6Network.dll",
    "PySide6/Qt6OpenGL.dll",
    "PySide6/Qt6Pdf.dll",
    "PySide6/Qt6Qml.dll",
    "PySide6/Qt6QmlMeta.dll",
    "PySide6/Qt6QmlModels.dll",
    "PySide6/Qt6QmlWorkerScript.dll",
    "PySide6/Qt6Quick.dll",
    "PySide6/Qt6VirtualKeyboard.dll",
    "PySide6/QtNetwork.pyd",
    "PySide6/opengl32sw.dll",
    "libcrypto-1_1.dll",
}
unused_prefixes = (
    "PySide6/plugins/generic/",
    "PySide6/plugins/networkinformation/",
    "PySide6/plugins/platforminputcontexts/",
    "PySide6/plugins/tls/",
)
allowed_image_plugins = {
    "qgif.dll",
    "qico.dll",
    "qjpeg.dll",
    "qsvg.dll",
    "qwebp.dll",
}
allowed_platform_plugins = {"qoffscreen.dll", "qwindows.dll"}
allowed_translations = {
    "qt_en.qm",
    "qt_ja.qm",
    "qtbase_en.qm",
    "qtbase_ja.qm",
}


def keep_qt_file(entry):
    destination = entry[0].replace("\\", "/")
    if destination in unused_files:
        return False
    if destination.startswith(unused_prefixes):
        return False
    if destination.startswith("PySide6/plugins/imageformats/"):
        return Path(destination).name in allowed_image_plugins
    if destination.startswith("PySide6/plugins/platforms/"):
        return Path(destination).name in allowed_platform_plugins
    if destination.startswith("PySide6/translations/"):
        return Path(destination).name in allowed_translations
    return True


a.binaries = [entry for entry in a.binaries if keep_qt_file(entry)]
a.datas = [entry for entry in a.datas if keep_qt_file(entry)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Capsha",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(assets / "capsha.ico"),
    version=str(project_root / "packaging" / "windows_version_info.txt"),
)
