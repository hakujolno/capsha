from __future__ import annotations

from PySide6.QtCore import QLocale


STRINGS: dict[str, dict[str, str]] = {
    "ja": {
        "save": "保存",
        "save_as": "名前を付けて保存",
        "copy": "コピー",
        "to_x": "𝕏へ",
        "select": "選択",
        "text": "テキスト",
        "caption": "番号",
        "rectangle": "四角",
        "arrow": "矢印",
        "mosaic": "モザイク",
        "color": "色",
        "font": "フォント",
        "bold": "太字",
        "italic": "斜体",
        "outline": "輪郭",
        "background": "背景",
        "fill": "塗り",
        "no_fill": "塗りなし",
        "fill_on": "塗りあり",
        "opacity": "透明度",
        "stroke": "線",
        "stroke_width": "線幅",
        "stroke_style": "線種",
        "solid": "実線",
        "dotted": "点線",
        "dashed": "破線",
        "rounded": "角丸",
        "undo": "元に戻す",
        "redo": "やり直す",
        "decrease": "1減らす",
        "increase": "1増やす",
        "main_actions": "主要操作",
        "tool_settings": "ツール設定",
        "delete_selected": "選択注釈を削除",
        "duplicate_selected": "選択注釈を複製",
        "saved": "保存しました",
        "copied": "コピーしました",
        "opened_x": "X投稿画面を開きました",
        "image_copied_paste": "画像はコピー済みです。投稿画面でCtrl+Vしてください。",
        "captured_copied": "撮影画像をクリップボードにコピーしました",
        "tool_tip": "{tool}ツール",
        "undo_tip": "元に戻す  Ctrl+Z",
        "redo_tip": "やり直す  Ctrl+Y",
        "save_tip": "保存  Ctrl+S",
        "save_as_tip": "名前を付けて保存  Ctrl+Shift+S",
        "copy_tip": "編集後画像をコピー  Ctrl+C",
        "x_tip": "X投稿画面を開きます。\n画像は自動でコピーされます。\n投稿欄で Ctrl+V してください。",
        "choose_color": "カラーパレットを開く",
        "add_color": "色を追加",
        "recent_color": "最近の色 {color}",
        "choose_annotation_color": "注釈色を選択",
        "choose_outline_color": "テキスト輪郭色を選択",
        "outline_color": "輪郭色 {color}",
        "stroke_opacity": "線の透明度",
        "fill_opacity": "塗りの透明度",
        "text_background_tip": "文字の後ろに半透明の黒背景を表示",
        "zoom_out": "縮小  Ctrl+マウスホイール",
        "zoom_in": "拡大  Ctrl+マウスホイール",
        "view_settings": "表示設定",
        "actual_size": "100%表示",
        "fit": "フィット表示",
        "grid": "グリッド表示",
        "save_png": "PNGを保存",
        "png_files": "PNG画像 (*.png)",
        "save_failed": "保存できませんでした",
        "check_destination": "保存先を確認してください。",
        "saved_path": "保存しました: {path}",
        "copied_status": "編集後の画像をコピーしました",
        "status_text": "文字  ·  {color}  ·  {font}",
        "status_rectangle": "四角  ·  {color}  ·  {width}px",
        "status_arrow": "矢印  ·  {color}  ·  {width}px",
        "capture_instruction": "ドラッグして範囲を選択   •   Esc で終了",
    },
    "en": {
        "save": "Save",
        "save_as": "Save As",
        "copy": "Copy",
        "to_x": "To 𝕏",
        "select": "Select",
        "text": "Text",
        "caption": "Number",
        "rectangle": "Rectangle",
        "arrow": "Arrow",
        "mosaic": "Mosaic",
        "color": "Color",
        "font": "Font",
        "bold": "Bold",
        "italic": "Italic",
        "outline": "Outline",
        "background": "Background",
        "fill": "Fill",
        "no_fill": "No fill",
        "fill_on": "Fill on",
        "opacity": "Opacity",
        "stroke": "Stroke",
        "stroke_width": "Width",
        "stroke_style": "Style",
        "solid": "Solid",
        "dotted": "Dotted",
        "dashed": "Dashed",
        "rounded": "Rounded",
        "undo": "Undo",
        "redo": "Redo",
        "decrease": "Decrease by 1",
        "increase": "Increase by 1",
        "main_actions": "Main actions",
        "tool_settings": "Tool settings",
        "delete_selected": "Delete selected annotation",
        "duplicate_selected": "Duplicate selected annotation",
        "saved": "Saved",
        "copied": "Copied",
        "opened_x": "Opened X compose",
        "image_copied_paste": "Image copied. Press Ctrl+V in the compose box.",
        "captured_copied": "Captured image copied to the clipboard",
        "tool_tip": "{tool} tool",
        "undo_tip": "Undo  Ctrl+Z",
        "redo_tip": "Redo  Ctrl+Y",
        "save_tip": "Save  Ctrl+S",
        "save_as_tip": "Save As  Ctrl+Shift+S",
        "copy_tip": "Copy edited image  Ctrl+C",
        "x_tip": "Open X compose.\nThe image is copied automatically.\nPress Ctrl+V in the compose box.",
        "choose_color": "Open color picker",
        "add_color": "Add color",
        "recent_color": "Recent color {color}",
        "choose_annotation_color": "Choose annotation color",
        "choose_outline_color": "Choose text outline color",
        "outline_color": "Outline color {color}",
        "stroke_opacity": "Stroke opacity",
        "fill_opacity": "Fill opacity",
        "text_background_tip": "Show a translucent background behind text",
        "zoom_out": "Zoom out  Ctrl+mouse wheel",
        "zoom_in": "Zoom in  Ctrl+mouse wheel",
        "view_settings": "View settings",
        "actual_size": "100%",
        "fit": "Fit to window",
        "grid": "Show grid",
        "save_png": "Save PNG",
        "png_files": "PNG images (*.png)",
        "save_failed": "Could not save",
        "check_destination": "Check the destination and try again.",
        "saved_path": "Saved: {path}",
        "copied_status": "Copied the edited image",
        "status_text": "Text  ·  {color}  ·  {font}",
        "status_rectangle": "Rectangle  ·  {color}  ·  {width}px",
        "status_arrow": "Arrow  ·  {color}  ·  {width}px",
        "capture_instruction": "Drag to select an area   •   Esc to exit",
    },
}


def _detect_language() -> str:
    locale = QLocale.system()
    if any(
        value.lower().replace("_", "-").startswith("ja")
        for value in locale.uiLanguages()
    ):
        return "ja"
    if locale.language() == QLocale.Language.Japanese:
        return "ja"
    return "en"


_language = _detect_language()


def language() -> str:
    return _language


def tr(key: str, **values: object) -> str:
    text = STRINGS[_language].get(key, STRINGS["en"].get(key, key))
    return text.format(**values) if values else text


def set_language_for_testing(value: str) -> None:
    global _language
    _language = value if value in STRINGS else "en"
