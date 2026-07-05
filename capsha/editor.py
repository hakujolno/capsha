from __future__ import annotations

import webbrowser
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QCloseEvent,
    QFont,
    QImage,
    QIcon,
    QKeyEvent,
    QKeySequence,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QButtonGroup,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFontComboBox,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QToolBar,
    QToolButton,
    QWidget,
)

from capsha.annotations import (
    ArrowAnnotation,
    MosaicAnnotation,
    RectangleAnnotation,
    TextAnnotation,
    Tool,
)
from capsha.branding import load_brand_logo
from capsha.canvas import AnnotationCanvas, DEFAULT_COLOR
from capsha.clipboard import copy_image_to_clipboard
from capsha.icons import make_icon
from capsha.i18n import tr


TOOL_KEYS = {
    Tool.SELECT: "select",
    Tool.TEXT: "text",
    Tool.CAPTION: "caption",
    Tool.RECTANGLE: "rectangle",
    Tool.ARROW: "arrow",
    Tool.MOSAIC: "mosaic",
}


class ReliableSpinBox(QSpinBox):
    def __init__(self) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setKeyboardTracking(True)
        self.setAccelerated(True)
        self.setSingleStep(1)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self.hasFocus():
            self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().wheelEvent(event)


class StepperControl(QWidget):
    valueChanged = Signal(int)

    def __init__(
        self,
        minimum: int,
        maximum: int,
        value: int,
        suffix: str,
    ) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        minus = QPushButton("−")
        minus.setObjectName("stepButton")
        minus.setToolTip(tr("decrease"))
        minus.setFixedSize(32, 34)
        layout.addWidget(minus)

        self.spin = ReliableSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setValue(value)
        self.spin.setSuffix(suffix)
        self.spin.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )
        self.spin.setMinimumWidth(72)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.spin)

        plus = QPushButton("+")
        plus.setObjectName("stepButton")
        plus.setToolTip(tr("increase"))
        plus.setFixedSize(32, 34)
        layout.addWidget(plus)

        minus.clicked.connect(self.spin.stepDown)
        plus.clicked.connect(self.spin.stepUp)
        self.spin.valueChanged.connect(self.valueChanged)

    def value(self) -> int:
        return self.spin.value()

    def setValue(self, value: int) -> None:
        self.spin.setValue(value)


class EditorWindow(QMainWindow):
    def __init__(self, image: QImage) -> None:
        super().__init__()
        self.setWindowTitle("Capsha")
        self.setMinimumSize(1180, 620)
        self.resize(1240, 720)

        self._settings = QSettings("trueWhite", "Capsha")
        self._current_save_path: Path | None = None
        self._image_size_text = f"{image.width()} × {image.height()}"
        self._current_tool = Tool.SELECT
        self._current_color = QColor(DEFAULT_COLOR)
        default_colors = [
            DEFAULT_COLOR,
            "#ffd43b",
            "#2f80ed",
            "#22a06b",
        ]
        stored_colors = self._settings.value("recent_colors", [])
        if isinstance(stored_colors, str):
            stored_colors = [stored_colors]
        valid_colors = (
            [
                str(value)
                for value in stored_colors
                if QColor(str(value)).isValid()
            ]
            if isinstance(stored_colors, list)
            else []
        )
        self._recent_colors = list(
            dict.fromkeys([*valid_colors, *default_colors])
        )[:4]
        self._line_width = 4
        self._font_size = 20
        self._fill_enabled = False
        self._fill_opacity = 30
        self._bold = True
        self._rounded = False
        self._line_opacity = 100
        self._line_style = "solid"
        self._font_family = "Segoe UI Variable"
        self._italic = False
        self._outline_enabled = False
        self._outline_color = QColor("#000000")
        self._background_enabled = False

        self._canvas = AnnotationCanvas(image)
        self._canvas.set_tool(Tool.SELECT)
        self.setCentralWidget(self._canvas)
        self._build_actions()
        self._build_toolbars()
        self._build_zoom_panel()
        self._apply_style()
        QTimer.singleShot(0, self._update_context_visibility)
        QTimer.singleShot(0, self._apply_initial_window_size)

        self._canvas.history_changed.connect(
            self._update_history_actions
        )
        self._canvas.selection_changed.connect(
            self._selection_changed
        )
        self._canvas.tool_change_requested.connect(
            self._select_tool_from_canvas
        )
        self.statusBar().showMessage(
            tr("captured_copied"),
            3500,
        )

    def _build_actions(self) -> None:
        self._save_action = QAction(tr("save"), self)
        self._save_action.setShortcut(QKeySequence.StandardKey.Save)
        self._save_action.triggered.connect(self._save)
        self.addAction(self._save_action)

        self._save_as_action = QAction(tr("save_as"), self)
        self._save_as_action.setShortcut(
            QKeySequence.StandardKey.SaveAs
        )
        self._save_as_action.setToolTip(tr("save_as_tip"))
        self._save_as_action.triggered.connect(self._save_as)
        self.addAction(self._save_as_action)

        self._undo_action = QAction(tr("undo"), self)
        self._undo_action.setShortcut("Ctrl+Z")
        self._undo_action.setEnabled(False)
        self._undo_action.triggered.connect(
            lambda: self._canvas.undo()
        )
        self.addAction(self._undo_action)

        self._redo_action = QAction(tr("redo"), self)
        self._redo_action.setShortcut("Ctrl+Y")
        self._redo_action.setEnabled(False)
        self._redo_action.triggered.connect(
            lambda: self._canvas.redo()
        )
        self.addAction(self._redo_action)

        self._copy_action = QAction(tr("copy"), self)
        self._copy_action.setShortcut("Ctrl+C")
        self._copy_action.triggered.connect(self._copy)
        self.addAction(self._copy_action)

        self._delete_action = QAction(tr("delete_selected"), self)
        self._delete_action.setShortcut("Delete")
        self._delete_action.triggered.connect(
            lambda: self._canvas.delete_selected()
        )
        self.addAction(self._delete_action)

        self._duplicate_action = QAction(
            tr("duplicate_selected"), self
        )
        self._duplicate_action.setShortcut("Ctrl+D")
        self._duplicate_action.triggered.connect(
            lambda: self._canvas.duplicate_selected()
        )
        self.addAction(self._duplicate_action)

    def _build_toolbars(self) -> None:
        commands = QToolBar(tr("main_actions"), self)
        commands.setObjectName("commandBar")
        commands.setMovable(False)
        commands.setFloatable(False)
        commands.setIconSize(QSize(18, 18))
        self.addToolBar(commands)
        self._command_bar = commands

        logo = QLabel()
        logo.setObjectName("brandMark")
        logo.setPixmap(load_brand_logo(22))
        logo.setFixedSize(24, 24)
        logo.setToolTip("Capsha — Capture. Annotate. Share.")
        commands.addWidget(logo)

        brand = QLabel("Capsha")
        brand.setObjectName("brandLabel")
        commands.addWidget(brand)
        commands.addSeparator()

        undo_button = QPushButton(tr("undo"))
        undo_button.setObjectName("quietButton")
        undo_button.setIcon(make_icon("undo"))
        undo_button.setToolTip(tr("undo_tip"))
        undo_button.clicked.connect(self._undo_action.trigger)
        undo_button.setEnabled(False)
        self._undo_action.changed.connect(
            lambda: undo_button.setEnabled(
                self._undo_action.isEnabled()
            )
        )
        commands.addWidget(undo_button)

        redo_button = QPushButton(tr("redo"))
        redo_button.setObjectName("quietButton")
        redo_button.setIcon(make_icon("redo"))
        redo_button.setToolTip(tr("redo_tip"))
        redo_button.clicked.connect(self._redo_action.trigger)
        redo_button.setEnabled(False)
        self._redo_action.changed.connect(
            lambda: redo_button.setEnabled(
                self._redo_action.isEnabled()
            )
        )
        commands.addWidget(redo_button)
        commands.addSeparator()

        tool_items = [
            (tr("select"), Tool.SELECT, "select"),
            (tr("text"), Tool.TEXT, "text"),
            ("①", Tool.CAPTION, "caption"),
            (tr("rectangle"), Tool.RECTANGLE, "rectangle"),
            (tr("arrow"), Tool.ARROW, "arrow"),
            (tr("mosaic"), Tool.MOSAIC, "mosaic"),
        ]
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self._tool_buttons: dict[Tool, QPushButton] = {}
        for text, tool, icon_name in tool_items:
            button = QPushButton(text)
            button.setObjectName("toolButton")
            button.setCheckable(True)
            button.setChecked(tool == Tool.SELECT)
            button.setIcon(make_icon(icon_name))
            button.setToolTip(
                tr("tool_tip", tool=tr(TOOL_KEYS[tool]))
            )
            button.clicked.connect(
                lambda checked=False, selected=tool:
                    self._select_tool(selected)
            )
            self._tool_group.addButton(button)
            self._tool_buttons[tool] = button
            commands.addWidget(button)

        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        commands.addWidget(spacer)

        self._save_button = QPushButton(tr("save"))
        self._save_button.setObjectName("primaryButton")
        self._save_button.setIcon(make_icon("save", "#ffffff"))
        self._save_button.setToolTip(tr("save_tip"))
        self._save_button.setMinimumWidth(84)
        self._save_button.clicked.connect(self._save)
        commands.addWidget(self._save_button)

        self._copy_button = QPushButton(tr("copy"))
        self._copy_button.setObjectName("commandButton")
        self._copy_button.setIcon(make_icon("copy"))
        self._copy_button.setToolTip(tr("copy_tip"))
        self._copy_button.setMinimumWidth(88)
        self._copy_button.clicked.connect(self._copy)
        commands.addWidget(self._copy_button)

        self._x_button = QPushButton(tr("to_x"))
        self._x_button.setObjectName("xButton")
        self._x_button.setIcon(make_icon("x", "#ffffff"))
        self._x_button.setToolTip(tr("x_tip"))
        self._x_button.setMinimumWidth(84)
        self._x_button.clicked.connect(self._open_x)
        commands.addWidget(self._x_button)

        context = QToolBar(tr("tool_settings"), self)
        context.setObjectName("contextBar")
        context.setMovable(False)
        context.setFloatable(False)
        context.setIconSize(QSize(18, 18))
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self.addToolBar(context)
        self._context_bar = context

        context.addWidget(QLabel(tr("color")))
        self._color_button = QPushButton()
        self._color_button.setObjectName("colorButton")
        self._color_button.setMinimumWidth(128)
        self._color_button.setToolTip(tr("choose_color"))
        self._color_button.clicked.connect(self._choose_color)
        context.addWidget(self._color_button)

        self._recent_color_buttons = []
        for color_name in self._recent_colors:
            recent = QToolButton()
            recent.setObjectName("colorChip")
            recent.setFixedSize(30, 30)
            self._recent_color_buttons.append(recent)
            context.addWidget(recent)
        add_color = QToolButton()
        add_color.setObjectName("paletteAddButton")
        add_color.setText("+")
        add_color.setFixedSize(30, 30)
        add_color.setToolTip(tr("add_color"))
        add_color.clicked.connect(self._choose_color)
        context.addWidget(add_color)
        self._update_recent_color_buttons()
        context.addSeparator()

        self._line_widgets: list[QAction] = []
        self._rectangle_widgets: list[QAction] = []
        self._text_widgets: list[QAction] = []

        def add(widget: QWidget, *groups: list[QAction]) -> None:
            action = context.addWidget(widget)
            for group in groups:
                group.append(action)

        line_label = QLabel(tr("stroke_width"))
        self._line_width_combo = QComboBox()
        self._line_width_combo.setEditable(True)
        self._line_width_combo.addItems(
            ["1", "2", "3", "4", "6", "8", "12", "16", "24"]
        )
        self._line_width_combo.setCurrentText(str(self._line_width))
        self._line_width_combo.setFixedWidth(64)
        self._line_width_combo.currentTextChanged.connect(
            self._line_width_text_changed
        )
        add(line_label, self._line_widgets)
        add(self._line_width_combo, self._line_widgets)

        style_label = QLabel(tr("stroke_style"))
        self._line_style_combo = QComboBox()
        self._line_style_combo.addItem(tr("solid"), "solid")
        self._line_style_combo.addItem(tr("dashed"), "dash")
        self._line_style_combo.addItem(tr("dotted"), "dot")
        self._line_style_combo.setFixedWidth(78)
        self._line_style_combo.currentIndexChanged.connect(
            self._line_style_changed
        )
        add(style_label, self._line_widgets)
        add(self._line_style_combo, self._line_widgets)

        line_alpha_label = QLabel(tr("stroke"))
        self._line_opacity_control = QSlider(
            Qt.Orientation.Horizontal
        )
        self._line_opacity_control.setRange(0, 100)
        self._line_opacity_control.setValue(self._line_opacity)
        self._line_opacity_control.setFixedWidth(88)
        self._line_opacity_control.setToolTip(tr("stroke_opacity"))
        self._line_alpha_value = QLabel("100%")
        self._line_opacity_control.valueChanged.connect(
            self._line_opacity_changed
        )
        add(line_alpha_label, self._line_widgets)
        add(self._line_opacity_control, self._line_widgets)
        add(self._line_alpha_value, self._line_widgets)

        self._fill_button = QPushButton(tr("no_fill"))
        self._fill_button.setObjectName("toggleButton")
        self._fill_button.setCheckable(True)
        self._fill_button.toggled.connect(self._fill_changed)
        add(self._fill_button, self._rectangle_widgets)

        fill_alpha_label = QLabel(tr("fill"))
        self._fill_opacity_control = QSlider(
            Qt.Orientation.Horizontal
        )
        self._fill_opacity_control.setRange(0, 100)
        self._fill_opacity_control.setValue(self._fill_opacity)
        self._fill_opacity_control.setFixedWidth(92)
        self._fill_opacity_control.setToolTip(tr("fill_opacity"))
        self._fill_alpha_value = QLabel("30%")
        self._fill_opacity_control.valueChanged.connect(
            self._fill_opacity_changed
        )
        add(fill_alpha_label, self._rectangle_widgets)
        add(self._fill_opacity_control, self._rectangle_widgets)
        add(self._fill_alpha_value, self._rectangle_widgets)

        self._rounded_button = QPushButton(tr("rounded"))
        self._rounded_button.setObjectName("toggleButton")
        self._rounded_button.setCheckable(True)
        self._rounded_button.toggled.connect(self._rounded_changed)
        add(self._rounded_button, self._rectangle_widgets)

        font_label = QLabel(tr("font"))
        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont(self._font_family))
        self._font_combo.setFixedWidth(170)
        self._font_combo.currentFontChanged.connect(
            lambda font: self._font_family_changed(font.family())
        )
        add(font_label, self._text_widgets)
        add(self._font_combo, self._text_widgets)

        self._bold_button = QPushButton("B")
        self._bold_button.setObjectName("formatButton")
        self._bold_button.setCheckable(True)
        self._bold_button.setChecked(self._bold)
        self._bold_button.setToolTip(tr("bold"))
        self._bold_button.toggled.connect(self._bold_changed)
        add(self._bold_button, self._text_widgets)

        self._italic_button = QPushButton("I")
        self._italic_button.setObjectName("formatButton")
        self._italic_button.setCheckable(True)
        self._italic_button.setToolTip(tr("italic"))
        self._italic_button.toggled.connect(self._italic_changed)
        add(self._italic_button, self._text_widgets)

        self._outline_button = QPushButton(tr("outline"))
        self._outline_button.setObjectName("toggleButton")
        self._outline_button.setCheckable(True)
        self._outline_button.setChecked(self._outline_enabled)
        self._outline_button.toggled.connect(self._outline_changed)
        add(self._outline_button, self._text_widgets)

        self._outline_color_button = QToolButton()
        self._outline_color_button.setObjectName("colorChip")
        self._outline_color_button.setFixedSize(30, 30)
        self._outline_color_button.setToolTip(
            tr("choose_outline_color")
        )
        self._outline_color_button.clicked.connect(
            self._choose_outline_color
        )
        add(self._outline_color_button, self._text_widgets)

        self._background_button = QPushButton(tr("background"))
        self._background_button.setObjectName("toggleButton")
        self._background_button.setCheckable(True)
        self._background_button.setChecked(self._background_enabled)
        self._background_button.setToolTip(
            tr("text_background_tip")
        )
        self._background_button.toggled.connect(
            self._background_changed
        )
        add(self._background_button, self._text_widgets)

        context_spacer = QWidget()
        context_spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        context.addWidget(context_spacer)

        self._state_label = QLabel()
        self._state_label.setObjectName("stateLabel")
        self.statusBar().addPermanentWidget(self._state_label)
        self._update_color_button()
        self._update_outline_color_button()
        self._update_state_label()
        self._update_context_visibility()

    def _build_zoom_panel(self) -> None:
        panel = QWidget(self._canvas)
        panel.setObjectName("zoomPanel")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(2)

        zoom_out = QToolButton()
        zoom_out.setObjectName("zoomControl")
        zoom_out.setText("−")
        zoom_out.setFixedSize(30, 30)
        zoom_out.setToolTip(tr("zoom_out"))
        zoom_out.clicked.connect(self._canvas.zoom_out)
        layout.addWidget(zoom_out)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setObjectName("zoomBadge")
        self._zoom_label.setFixedWidth(52)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._zoom_label)

        zoom_in = QToolButton()
        zoom_in.setObjectName("zoomControl")
        zoom_in.setText("+")
        zoom_in.setFixedSize(30, 30)
        zoom_in.setToolTip(tr("zoom_in"))
        zoom_in.clicked.connect(self._canvas.zoom_in)
        layout.addWidget(zoom_in)

        view = QToolButton()
        view.setObjectName("zoomControl")
        view.setText("⋯")
        view.setFixedSize(30, 30)
        view.setToolTip(tr("view_settings"))
        view.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(view)
        menu.addAction(tr("actual_size"), self._canvas.show_100_percent)
        menu.addAction(tr("fit"), self._canvas.fit_image)
        menu.addSeparator()
        self._grid_action = menu.addAction(tr("grid"))
        self._grid_action.setCheckable(True)
        self._grid_action.toggled.connect(self._grid_changed)
        view.setMenu(menu)
        layout.addWidget(view)

        panel.setFixedSize(174, 42)
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 80))
        panel.setGraphicsEffect(shadow)
        panel.show()
        panel.raise_()
        self._zoom_panel = panel
        self._canvas.zoom_changed.connect(
            lambda percent: self._zoom_label.setText(f"{percent}%")
        )
        self._canvas.installEventFilter(self)
        QTimer.singleShot(0, self._position_zoom_panel)

    def _position_zoom_panel(self) -> None:
        if not hasattr(self, "_zoom_panel"):
            return
        self._zoom_panel.move(
            max(12, self._canvas.width() - self._zoom_panel.width() - 16),
            max(12, self._canvas.height() - self._zoom_panel.height() - 16),
        )
        self._zoom_panel.raise_()

    def _apply_initial_window_size(self) -> None:
        command_width = self._command_bar.sizeHint().width() + 24
        minimum_width = max(1180, command_width)
        self.setMinimumSize(minimum_width, 620)
        if self.width() < minimum_width or self.height() < 720:
            self.resize(max(self.width(), minimum_width), 720)
        self._canvas.fit_image()
        self._position_zoom_panel()

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self._canvas and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._position_zoom_panel)
        return super().eventFilter(watched, event)

    def _build_legacy_toolbars(self) -> None:
        tools = QToolBar("注釈ツール", self)
        tools.setMovable(False)
        tools.setFloatable(False)
        self.addToolBar(tools)

        undo_button = QPushButton("↶  元に戻す")
        undo_button.setToolTip("元に戻す (Ctrl+Z)")
        undo_button.setMinimumSize(112, 36)
        undo_button.clicked.connect(
            lambda: self._undo_action.trigger()
        )
        self._undo_action.changed.connect(
            lambda: undo_button.setEnabled(
                self._undo_action.isEnabled()
            )
        )
        undo_button.setEnabled(False)
        tools.addWidget(undo_button)

        redo_button = QPushButton("↷  やり直す")
        redo_button.setToolTip("やり直す (Ctrl+Y)")
        redo_button.setMinimumSize(112, 36)
        redo_button.clicked.connect(
            lambda: self._redo_action.trigger()
        )
        self._redo_action.changed.connect(
            lambda: redo_button.setEnabled(
                self._redo_action.isEnabled()
            )
        )
        redo_button.setEnabled(False)
        tools.addWidget(redo_button)
        tools.addSeparator()

        tools.addWidget(QLabel("ツール"))
        tool_buttons = [
            ("選択", Tool.SELECT),
            ("テキスト", Tool.TEXT),
            ("四角", Tool.RECTANGLE),
            ("矢印", Tool.ARROW),
            ("モザイク", Tool.MOSAIC),
        ]
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        for index, (text, tool) in enumerate(tool_buttons):
            button = QPushButton(text)
            button.setCheckable(True)
            button.setChecked(index == 0)
            self._tool_group.addButton(button)
            button.clicked.connect(
                lambda checked=False, selected=tool:
                    self._select_tool(selected)
            )
            tools.addWidget(button)

        tools.addSeparator()
        self._color_button = QPushButton("色")
        self._color_button.setToolTip(
            "次に追加する注釈の色を選択"
        )
        self._color_button.clicked.connect(self._choose_color)
        self._color_button.setMinimumSize(144, 38)
        tools.addWidget(self._color_button)

        self._recent_color_buttons: list[QToolButton] = []
        for color_name in self._recent_colors:
            recent = QToolButton()
            recent.setFixedSize(34, 34)
            recent.setToolTip(f"最近の色 {color_name}")
            recent.clicked.connect(
                lambda checked=False, name=color_name:
                    self._use_color(QColor(name))
            )
            self._recent_color_buttons.append(recent)
            tools.addWidget(recent)
        self._update_recent_color_buttons()

        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        styles = QToolBar("スタイル", self)
        styles.setMovable(False)
        styles.setFloatable(False)
        self.addToolBar(styles)
        tools = styles

        tools.addWidget(QLabel("線幅"))
        self._line_control = StepperControl(
            1, 24, self._line_width, " px"
        )
        self._line_spin = self._line_control.spin
        self._line_spin.setToolTip(
            "次に追加する四角・矢印の線幅"
        )
        self._line_control.valueChanged.connect(
            self._line_width_changed
        )
        tools.addWidget(self._line_control)

        self._fill_button = QPushButton("塗り: なし")
        self._fill_button.setCheckable(True)
        self._fill_button.setToolTip(
            "四角の内側を現在の色で30%塗りつぶす"
        )
        self._fill_button.toggled.connect(
            self._fill_changed
        )
        tools.addWidget(self._fill_button)

        tools.addWidget(QLabel("塗り透明度"))
        self._fill_opacity_control = StepperControl(
            0, 100, self._fill_opacity, "%"
        )
        self._fill_opacity_control.setToolTip(
            "四角の塗りつぶし透明度 (0〜100%)"
        )
        self._fill_opacity_control.valueChanged.connect(
            self._fill_opacity_changed
        )
        tools.addWidget(self._fill_opacity_control)

        tools.addWidget(QLabel("文字"))
        self._font_control = StepperControl(
            10, 144, self._font_size, " px"
        )
        self._font_spin = self._font_control.spin
        self._font_spin.setToolTip(
            "次に追加するテキストのサイズ"
        )
        self._font_control.valueChanged.connect(
            self._font_size_changed
        )
        tools.addWidget(self._font_control)

        self._bold_button = QPushButton("太字: ON")
        self._bold_button.setCheckable(True)
        self._bold_button.setChecked(True)
        self._bold_button.setToolTip(
            "次に追加するテキストを太字にする"
        )
        self._bold_button.toggled.connect(
            self._bold_changed
        )
        tools.addWidget(self._bold_button)

        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        advanced = QToolBar("詳細設定", self)
        advanced.setMovable(False)
        advanced.setFloatable(False)
        self.addToolBar(advanced)
        tools = advanced

        self._rounded_button = QPushButton("角丸: OFF")
        self._rounded_button.setCheckable(True)
        self._rounded_button.toggled.connect(
            self._rounded_changed
        )
        tools.addWidget(self._rounded_button)

        tools.addWidget(QLabel("線透明度"))
        self._line_opacity_control = StepperControl(
            0, 100, self._line_opacity, "%"
        )
        self._line_opacity_control.valueChanged.connect(
            self._line_opacity_changed
        )
        tools.addWidget(self._line_opacity_control)

        tools.addWidget(QLabel("線種"))
        self._line_style_combo = QComboBox()
        self._line_style_combo.addItem("実線", "solid")
        self._line_style_combo.addItem("破線", "dash")
        self._line_style_combo.addItem("点線", "dot")
        self._line_style_combo.currentIndexChanged.connect(
            self._line_style_changed
        )
        tools.addWidget(self._line_style_combo)

        tools.addSeparator()
        tools.addWidget(QLabel("フォント"))
        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont(self._font_family))
        self._font_combo.setMinimumWidth(180)
        self._font_combo.currentFontChanged.connect(
            lambda font: self._font_family_changed(
                font.family()
            )
        )
        tools.addWidget(self._font_combo)

        self._italic_button = QPushButton("斜体: OFF")
        self._italic_button.setCheckable(True)
        self._italic_button.toggled.connect(
            self._italic_changed
        )
        tools.addWidget(self._italic_button)

        self._outline_button = QPushButton("輪郭: ON")
        self._outline_button.setCheckable(True)
        self._outline_button.setChecked(True)
        self._outline_button.toggled.connect(
            self._outline_changed
        )
        tools.addWidget(self._outline_button)

        self._grid_button = QPushButton("グリッド: OFF")
        self._grid_button.setCheckable(True)
        self._grid_button.toggled.connect(self._grid_changed)
        tools.addWidget(self._grid_button)

        zoom_out = QPushButton("−")
        zoom_out.setToolTip("縮小 (Ctrl+マウスホイール)")
        zoom_out.clicked.connect(self._canvas.zoom_out)
        tools.addWidget(zoom_out)
        self._zoom_label = QLabel("100%")
        self._zoom_label.setMinimumWidth(48)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tools.addWidget(self._zoom_label)
        zoom_in = QPushButton("+")
        zoom_in.setToolTip("拡大 (Ctrl+マウスホイール)")
        zoom_in.clicked.connect(self._canvas.zoom_in)
        tools.addWidget(zoom_in)
        fit = QPushButton("中央にフィット")
        fit.clicked.connect(self._canvas.fit_image)
        tools.addWidget(fit)
        self._canvas.zoom_changed.connect(
            lambda percent: self._zoom_label.setText(
                f"{percent}%"
            )
        )

        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        actions = QToolBar("ファイル操作", self)
        actions.setMovable(False)
        actions.setFloatable(False)
        self.addToolBar(actions)

        self._state_label = QLabel()
        self._state_label.setObjectName("stateLabel")
        actions.addWidget(self._state_label)

        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        actions.addWidget(spacer)

        callbacks: list[tuple[str, Callable[[], object]]] = [
            ("保存", self._save),
            ("コピー  Ctrl+C", self._copy),
            ("Xで投稿", self._open_x),
            ("閉じる", self.close),
        ]
        for text, callback in callbacks:
            button = QPushButton(text)
            button.clicked.connect(callback)
            actions.addWidget(button)

        self._update_color_button()
        self._update_state_label()

    def _apply_style(self) -> None:
        down_arrow = (
            Path(__file__).resolve().parent
            / "assets"
            / "chevron-down.svg"
        ).as_posix()
        self.setStyleSheet(
            "QMainWindow { background: #0f141c; color: #e7eaf0; }"
            "QToolBar { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 #1a212c, stop:1 #161d27); border: 0;"
            " border-bottom: 1px solid #293342; spacing: 7px;"
            " padding: 8px 12px; }"
            "QToolBar#contextBar { background: #141a23; padding: 7px 12px; }"
            "QToolBar::separator { background: #303a48; width: 1px;"
            " margin: 6px 7px; }"
            "QLabel { color: #d7dce4; background: transparent; }"
            "QLabel#brandLabel { color: #f1f3f7; font-size: 15px;"
            " font-weight: 600; padding: 0 11px 0 4px; }"
            "QPushButton { color: #e7eaf0; background: #202936;"
            " border: 1px solid #303b4b; border-radius: 9px;"
            " padding: 7px 12px; min-height: 22px; }"
            "QPushButton:hover { background: #283342;"
            " border-color: #46556a; }"
            "QPushButton:pressed { background: #1a222e;"
            " border-color: #3b4758; }"
            "QPushButton:disabled { color: #667080;"
            " background: #171e28; border-color: #252e3b; }"
            "QPushButton#quietButton, QPushButton#toolButton {"
            " background: transparent; border-color: transparent; }"
            "QPushButton#quietButton:hover, QPushButton#toolButton:hover {"
            " background: #232d3a; border-color: #303b4b; }"
            "QPushButton#toolButton:checked { color: #ffffff;"
            " background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 #377cf0, stop:1 #2866d6); border-color: #4b88ef; }"
            "QPushButton#primaryButton { color: #ffffff;"
            " background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 #3b82f6, stop:1 #2563d8); border-color: #4b8af0;"
            " font-weight: 600; padding: 7px 17px; }"
            "QPushButton#primaryButton:hover {"
            " background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 #4a8df7, stop:1 #2f6ee0); border-color: #6ba0f3; }"
            "QPushButton#xButton { color: #f4f5f7; background: #10141a;"
            " border-color: #343d49; font-weight: 600; padding: 7px 16px; }"
            "QPushButton#xButton:hover { background: #181e27;"
            " border-color: #596575; }"
            "QPushButton#toggleButton:checked,"
            " QPushButton#formatButton:checked { color: #ffffff;"
            " background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 #377cf0, stop:1 #2866d6); border-color: #4b88ef; }"
            "QPushButton#formatButton { min-width: 28px; max-width: 28px;"
            " padding: 6px 3px; font-weight: 700; }"
            "QPushButton#colorButton { text-align: left;"
            " background: #1b2430; padding: 5px 10px; }"
            "QToolButton { color: #dce1e8; background: transparent;"
            " border: 1px solid transparent; border-radius: 9px;"
            " padding: 6px; min-width: 22px; min-height: 22px; }"
            "QToolButton:hover { background: #26313f;"
            " border-color: #3a4758; }"
            "QToolButton#colorChip { background: #1b2430;"
            " border: 1px solid #3a4656; padding: 2px; }"
            "QToolButton#colorChip:hover { border: 2px solid #5792ef; }"
            "QToolButton#paletteAddButton { color: #aeb8c5;"
            " background: #1b2430; border: 1px dashed #46556a;"
            " font-size: 18px; font-weight: 500; padding: 0; }"
            "QToolButton#paletteAddButton:hover { color: #ffffff;"
            " background: #26313f; border: 1px solid #5792ef; }"
            "QToolButton#closeButton:hover { background: #c42b1c; }"
            "QComboBox, QFontComboBox, QSpinBox { color: #edf0f4;"
            " background: #111720; border: 1px solid #354153;"
            " border-radius: 8px; padding: 6px 9px; min-height: 22px; }"
            "QComboBox:hover, QFontComboBox:hover { border-color: #58708e; }"
            "QComboBox::drop-down, QFontComboBox::drop-down {"
            " border: 0; width: 28px; }"
            f"QComboBox::down-arrow, QFontComboBox::down-arrow {{"
            f" image: url({down_arrow}); width: 12px; height: 8px; }}"
            "QComboBox QAbstractItemView,"
            " QFontComboBox QAbstractItemView { color: #edf0f4;"
            " background: #19212c; border: 1px solid #3a4656;"
            " selection-color: #ffffff; selection-background-color: #2d6edb;"
            " outline: 0; padding: 6px; }"
            "QComboBox QLineEdit { color: #edf0f4; background: #111720;"
            " border: 0; selection-color: #ffffff;"
            " selection-background-color: #2d6edb; }"
            "QSlider::groove:horizontal { height: 4px;"
            " background: #354050; border-radius: 2px; }"
            "QSlider::sub-page:horizontal { background: #4b86e8;"
            " border-radius: 2px; }"
            "QSlider::handle:horizontal { background: #f3f5f8;"
            " border: 2px solid #4b86e8; width: 14px; height: 14px;"
            " margin: -6px 0; border-radius: 8px; }"
            "QWidget#zoomPanel { background: rgba(24, 32, 43, 242);"
            " border: 1px solid #3a4656; border-radius: 10px; }"
            "QToolButton#zoomControl { color: #e7eaf0;"
            " background: transparent; font-size: 15px; }"
            "QToolButton#zoomControl:hover { background: #283342; }"
            "QLabel#zoomBadge { color: #edf0f4; font-weight: 600; }"
            "QLabel#stateLabel { color: #8f9aaa; padding: 2px 7px; }"
            "QLabel#toast { color: #ffffff; background: rgba(24, 32, 43, 247);"
            " border: 1px solid #4b86e8; border-radius: 9px;"
            " padding: 10px 18px; font-weight: 600; }"
            "QMenu { color: #edf0f4; background: #19212c;"
            " border: 1px solid #3a4656; border-radius: 9px; padding: 6px; }"
            "QMenu::item { color: #edf0f4; background: transparent;"
            " border-radius: 7px; padding: 8px 26px 8px 12px; }"
            "QMenu::item:selected { color: #ffffff; background: #2d6edb; }"
            "QStatusBar { color: #8f9aaa; background: #0f141c;"
            " border-top: 1px solid #242d39; }"
            "QToolTip { color: #edf0f4; background: #202936;"
            " border: 1px solid #46556a; border-radius: 6px; padding: 7px; }"
        )

    def _apply_light_style(self) -> None:
        self.setStyleSheet(
            "QMainWindow { background: #f3f3f3; color: #1f1f1f; }"
            "QToolBar { background: #f7f7f7; border: 0;"
            " border-bottom: 1px solid #e1e1e1; spacing: 4px;"
            " padding: 5px 8px; }"
            "QToolBar::separator { background: #dddddd; width: 1px;"
            " margin: 5px 5px; }"
            "QLabel { color: #252525; background: transparent; }"
            "QLabel#brandLabel { font-size: 15px; font-weight: 600;"
            " padding: 0 8px 0 3px; }"
            "QPushButton { color: #242424; background: #fbfbfb;"
            " border: 1px solid #d5d5d5; border-radius: 5px;"
            " padding: 5px 10px; min-height: 22px; }"
            "QPushButton:hover { background: #f0f0f0;"
            " border-color: #c4c4c4; }"
            "QPushButton:pressed { background: #e7e7e7; }"
            "QPushButton:disabled { color: #9a9a9a;"
            " background: #f4f4f4; border-color: #e5e5e5; }"
            "QPushButton#quietButton { background: transparent;"
            " border-color: transparent; padding: 5px 8px; }"
            "QPushButton#quietButton:hover { background: #eaeaea; }"
            "QPushButton#toolButton { background: transparent;"
            " border-color: transparent; padding: 5px 9px; }"
            "QPushButton#toolButton:hover { background: #eaeaea; }"
            "QPushButton#toolButton:checked { color: #ffffff;"
            " background: #0f6cbd; border-color: #0f6cbd; }"
            "QPushButton#primaryButton { color: #ffffff;"
            " background: #0f6cbd; border-color: #0b5a9e;"
            " font-weight: 600; padding: 5px 15px; }"
            "QPushButton#primaryButton:hover { background: #115ea3; }"
            "QPushButton#xButton { color: #ffffff; background: #202020;"
            " border-color: #202020; font-weight: 600; padding: 5px 14px; }"
            "QPushButton#xButton:hover { background: #383838; }"
            "QPushButton#toggleButton:checked,"
            " QPushButton#formatButton:checked { color: #ffffff;"
            " background: #0f6cbd; border-color: #0f6cbd; }"
            "QPushButton#formatButton { min-width: 28px; max-width: 28px;"
            " padding: 5px 2px; font-weight: 700; }"
            "QPushButton#colorButton { text-align: left; padding: 3px 9px;"
            " background: #ffffff; }"
            "QToolButton { color: #242424; background: transparent;"
            " border: 1px solid transparent; border-radius: 5px;"
            " padding: 5px; min-width: 22px; min-height: 22px; }"
            "QToolButton:hover { background: #eaeaea; border-color: #d5d5d5; }"
            "QToolButton#colorChip { background: #ffffff;"
            " border: 1px solid #cccccc; padding: 2px; }"
            "QToolButton#colorChip:hover { border: 2px solid #0f6cbd; }"
            "QToolButton#closeButton:hover { background: #c42b1c; }"
            "QComboBox, QFontComboBox, QSpinBox { color: #202020;"
            " background: #ffffff; border: 1px solid #d0d0d0;"
            " border-radius: 5px; padding: 4px 7px; min-height: 22px; }"
            "QComboBox:hover, QFontComboBox:hover { border-color: #9d9d9d; }"
            "QComboBox::drop-down, QFontComboBox::drop-down {"
            " border: 0; width: 22px; }"
            "QComboBox QAbstractItemView,"
            " QFontComboBox QAbstractItemView { color: #202020;"
            " background: #ffffff; border: 1px solid #c8c8c8;"
            " selection-color: #ffffff; selection-background-color: #0f6cbd;"
            " outline: 0; padding: 3px; }"
            "QComboBox QLineEdit { color: #202020; background: #ffffff;"
            " border: 0; selection-color: #ffffff;"
            " selection-background-color: #0f6cbd; }"
            "QSlider::groove:horizontal { height: 4px;"
            " background: #c8c8c8; border-radius: 2px; }"
            "QSlider::sub-page:horizontal { background: #0f6cbd;"
            " border-radius: 2px; }"
            "QSlider::handle:horizontal { background: #ffffff;"
            " border: 2px solid #0f6cbd; width: 14px; height: 14px;"
            " margin: -6px 0; border-radius: 8px; }"
            "QSlider::handle:horizontal:hover { background: #e5f3ff; }"
            "QLabel#stateLabel { color: #5a5a5a; padding: 1px 5px; }"
            "QLabel#zoomBadge { color: #333333; background: #ededed;"
            " border-radius: 10px; padding: 3px 7px; }"
            "QLabel#toast { color: #ffffff; background: rgba(32, 32, 32, 230);"
            " border: 1px solid #4a4a4a; border-radius: 7px;"
            " padding: 9px 16px; font-weight: 600; }"
            "QMenu { color: #202020; background: #ffffff;"
            " border: 1px solid #c8c8c8; padding: 5px; }"
            "QMenu::item { color: #202020; background: transparent;"
            " border-radius: 4px; padding: 6px 24px 6px 10px; }"
            "QMenu::item:selected { color: #ffffff; background: #0f6cbd; }"
            "QStatusBar { color: #555555; background: #f7f7f7;"
            " border-top: 1px solid #e1e1e1; }"
            "QToolTip { color: #202020; background: #ffffff;"
            " border: 1px solid #bdbdbd; padding: 5px; }"
        )

    def _apply_legacy_style(self) -> None:
        self.setStyleSheet(
            "QMainWindow { background: #202124; }"
            "QToolBar {"
            " background: #f5f5f5;"
            " border: 0;"
            " border-bottom: 1px solid #d1d1d1;"
            " spacing: 6px;"
            " padding: 6px;"
            "}"
            "QToolBar QLabel {"
            " color: #252525;"
            " background: transparent;"
            " padding: 0 3px;"
            "}"
            "QPushButton {"
            " color: #202020;"
            " background: #ffffff;"
            " padding: 7px 12px;"
            " border: 1px solid #bdbdbd;"
            " border-radius: 4px;"
            "}"
            "QPushButton:hover {"
            " color: #111111;"
            " background: #eaf2fc;"
            " border-color: #7b9fc9;"
            "}"
            "QPushButton:pressed { background: #dce9f8; }"
            "QPushButton:checked {"
            " color: #ffffff;"
            " background: #2563a9;"
            " border-color: #1f568f;"
            "}"
            "QPushButton:disabled {"
            " color: #7a7a7a;"
            " background: #ededed;"
            " border-color: #d3d3d3;"
            "}"
            "QSpinBox {"
            " color: #202020;"
            " background: #ffffff;"
            " border: 1px solid #bdbdbd;"
            " border-radius: 4px;"
            " padding: 5px;"
            " min-width: 72px;"
            "}"
            "QSpinBox::up-button, QSpinBox::down-button {"
            " width: 22px; background: #eeeeee;"
            " border-left: 1px solid #bdbdbd;"
            "}"
            "QSpinBox::up-button:hover,"
            " QSpinBox::down-button:hover { background: #dce9f8; }"
            "QPushButton#stepButton {"
            " font-size: 20px; font-weight: 600; padding: 0;"
            " min-width: 32px; min-height: 32px;"
            "}"
            "QComboBox, QFontComboBox {"
            " color: #202020; background: #ffffff;"
            " border: 1px solid #bdbdbd; border-radius: 4px;"
            " padding: 6px 8px; min-height: 20px;"
            "}"
            "QToolButton {"
            " background: #ffffff; border: 1px solid #a8a8a8;"
            " border-radius: 4px; padding: 2px;"
            "}"
            "QToolButton:hover { border: 2px solid #2563a9; }"
            "QLabel#stateLabel {"
            " color: #202020;"
            " background: #ffffff;"
            " border: 1px solid #d0d0d0;"
            " border-radius: 4px;"
            " padding: 6px 10px;"
            "}"
            "QStatusBar {"
            " color: #333333;"
            " background: #f5f5f5;"
            "}"
        )

    def _select_tool(self, tool: Tool) -> None:
        self._current_tool = tool
        self._canvas.set_tool(tool)
        self._update_context_visibility()
        self._update_state_label()

    def _select_tool_from_canvas(self, tool: object) -> None:
        if not isinstance(tool, Tool):
            return
        button = self._tool_buttons.get(tool)
        if button is not None:
            button.setChecked(True)
        self._select_tool(tool)

    def _selection_changed(self, selected: bool) -> None:
        self._update_context_visibility()
        self._update_state_label()

    def _update_context_visibility(self) -> None:
        if not hasattr(self, "_line_widgets"):
            return
        tool = self._current_tool
        selected = self._canvas.selected_annotation()
        show_line = tool in {Tool.RECTANGLE, Tool.ARROW}
        show_rectangle = tool == Tool.RECTANGLE
        show_text = tool in {Tool.TEXT, Tool.CAPTION}
        if tool == Tool.SELECT:
            show_line = isinstance(
                selected, (RectangleAnnotation, ArrowAnnotation)
            )
            show_rectangle = isinstance(
                selected, RectangleAnnotation
            )
            show_text = isinstance(selected, TextAnnotation)
        for action in self._line_widgets:
            action.setVisible(show_line)
        for action in self._rectangle_widgets:
            action.setVisible(show_rectangle)
        for action in self._text_widgets:
            action.setVisible(show_text)

    def _line_width_text_changed(self, text: str) -> None:
        try:
            width = int(text)
        except ValueError:
            return
        if 1 <= width <= 24:
            self._line_width_changed(width)

    def _font_size_text_changed(self, text: str) -> None:
        try:
            size = int(text)
        except ValueError:
            return
        if 8 <= size <= 240:
            self._font_size_changed(size)

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(
            self._current_color,
            self,
            tr("choose_annotation_color"),
        )
        if not color.isValid():
            return
        self._use_color(color)

    def _use_color(self, color: QColor) -> None:
        if not color.isValid():
            return
        self._current_color = color
        self._recent_colors = [
            color.name(),
            *[
                item
                for item in self._recent_colors
                if item != color.name()
            ],
        ][:4]
        self._settings.setValue(
            "recent_colors", self._recent_colors
        )
        self._update_recent_color_buttons()
        self._canvas.set_color(color)
        self._update_color_button()
        self._update_state_label()

    def _update_color_button(self) -> None:
        color = self._current_color.name()
        chip = QPixmap(40, 26)
        chip.fill(self._current_color)
        self._color_button.setIcon(QIcon(chip))
        self._color_button.setIconSize(QSize(40, 26))
        self._color_button.setText(f"{tr('color')}  {color}")

    def _update_recent_color_buttons(self) -> None:
        if not hasattr(self, "_recent_color_buttons"):
            return
        for button, color_name in zip(
            self._recent_color_buttons, self._recent_colors
        ):
            chip = QPixmap(26, 26)
            chip.fill(QColor(color_name))
            button.setIcon(QIcon(chip))
            button.setIconSize(QSize(26, 26))
            button.setToolTip(
                tr("recent_color", color=color_name)
            )
            button.setProperty("colorName", color_name)
            if not button.property("colorHandlerConnected"):
                button.clicked.connect(
                    lambda checked=False, source=button:
                        self._use_color(
                            QColor(str(source.property("colorName")))
                        )
                )
                button.setProperty("colorHandlerConnected", True)

    def _choose_outline_color(self) -> None:
        color = QColorDialog.getColor(
            self._outline_color,
            self,
            tr("choose_outline_color"),
        )
        if not color.isValid():
            return
        self._outline_color = color
        self._canvas.set_outline_color(color)
        self._update_outline_color_button()

    def _update_outline_color_button(self) -> None:
        chip = QPixmap(24, 24)
        chip.fill(self._outline_color)
        self._outline_color_button.setIcon(QIcon(chip))
        self._outline_color_button.setIconSize(QSize(24, 24))
        self._outline_color_button.setToolTip(
            tr("outline_color", color=self._outline_color.name())
        )

    def _line_width_changed(self, width: int) -> None:
        self._line_width = width
        self._canvas.set_line_width(width)
        self._update_state_label()

    def _font_size_changed(self, size: int) -> None:
        self._font_size = size
        self._canvas.set_font_size(size)
        self._update_state_label()

    def _fill_changed(self, enabled: bool) -> None:
        self._fill_enabled = enabled
        self._canvas.set_fill_enabled(enabled)
        self._fill_button.setText(
            tr("fill_on") if enabled else tr("no_fill")
        )
        self._update_state_label()

    def _fill_opacity_changed(self, percent: int) -> None:
        self._fill_opacity = percent
        self._canvas.set_fill_opacity(percent)
        if hasattr(self, "_fill_alpha_value"):
            self._fill_alpha_value.setText(f"{percent}%")
        self._update_state_label()

    def _bold_changed(self, enabled: bool) -> None:
        self._bold = enabled
        self._canvas.set_bold(enabled)
        self._bold_button.setText("B")
        self._update_state_label()

    def _rounded_changed(self, enabled: bool) -> None:
        self._rounded = enabled
        self._canvas.set_rounded(enabled)
        self._rounded_button.setText(tr("rounded"))
        self._update_state_label()

    def _line_opacity_changed(self, percent: int) -> None:
        self._line_opacity = percent
        self._canvas.set_line_opacity(percent)
        if hasattr(self, "_line_alpha_value"):
            self._line_alpha_value.setText(f"{percent}%")
        self._update_state_label()

    def _line_style_changed(self, index: int) -> None:
        style = self._line_style_combo.itemData(index)
        if not isinstance(style, str):
            return
        self._line_style = style
        self._canvas.set_line_style(style)
        self._update_state_label()

    def _font_family_changed(self, family: str) -> None:
        self._font_family = family
        self._canvas.set_font_family(family)
        self._update_state_label()

    def _italic_changed(self, enabled: bool) -> None:
        self._italic = enabled
        self._canvas.set_italic(enabled)
        self._italic_button.setText("I")
        self._update_state_label()

    def _outline_changed(self, enabled: bool) -> None:
        self._outline_enabled = enabled
        self._canvas.set_outline_enabled(enabled)
        self._outline_button.setText(tr("outline"))
        self._update_state_label()

    def _background_changed(self, enabled: bool) -> None:
        self._background_enabled = enabled
        self._canvas.set_background_enabled(enabled)
        self._background_button.setText(tr("background"))
        self._update_state_label()

    def _grid_changed(self, enabled: bool) -> None:
        self._canvas.set_grid_enabled(enabled)

    def _update_state_label(self) -> None:
        selected = self._canvas.selected_annotation()
        if selected is None:
            self._state_label.setText(self._image_size_text)
        elif isinstance(selected, TextAnnotation):
            self._state_label.setText(
                tr(
                    "status_text",
                    color=selected.color,
                    font=selected.font_family,
                )
            )
        elif isinstance(selected, RectangleAnnotation):
            self._state_label.setText(
                tr(
                    "status_rectangle",
                    color=selected.color,
                    width=selected.line_width,
                )
            )
        elif isinstance(selected, ArrowAnnotation):
            self._state_label.setText(
                tr(
                    "status_arrow",
                    color=selected.color,
                    width=selected.line_width,
                )
            )
        elif isinstance(selected, MosaicAnnotation):
            self._state_label.setText(tr("mosaic"))

    def _update_history_actions(
        self,
        can_undo: bool,
        can_redo: bool,
    ) -> None:
        self._undo_action.setEnabled(can_undo)
        self._redo_action.setEnabled(can_redo)

    def _show_toast(self, message: str) -> None:
        if not hasattr(self, "_toast"):
            self._toast = QLabel(self._canvas)
            self._toast.setObjectName("toast")
            self._toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._toast.setText(message)
        self._toast.adjustSize()
        x = max(16, (self._canvas.width() - self._toast.width()) // 2)
        y = max(16, self._canvas.height() - self._toast.height() - 28)
        self._toast.move(x, y)
        self._toast.show()
        self._toast.raise_()
        QTimer.singleShot(1600, self._toast.hide)

    def _save(self) -> None:
        if self._current_save_path is None:
            self._save_as()
            return
        self._write_png(self._current_save_path)

    def _save_as(self) -> None:
        default_dir = Path(
            str(
                self._settings.value(
                    "last_save_dir",
                    str(Path.home() / "Pictures"),
                )
            )
        )
        default_name = datetime.now().strftime(
            "capsha_%Y%m%d_%H%M%S.png"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("save_as"),
            str(default_dir / default_name),
            tr("png_files"),
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"

        candidate = Path(path)
        if self._write_png(candidate):
            self._current_save_path = candidate

    def _write_png(self, path: Path) -> bool:
        self._canvas.commit_inline_editing()
        image = self._canvas.render_image()
        image.setDevicePixelRatio(1.0)
        if image.save(str(path), "PNG", 100):
            self._settings.setValue(
                "last_save_dir", str(path.parent)
            )
            self.statusBar().showMessage(
                tr("saved_path", path=str(path)),
                4000,
            )
            self._show_toast(tr("saved"))
            return True
        else:
            QMessageBox.warning(
                self,
                tr("save_failed"),
                tr("check_destination"),
            )
            return False

    def _copy(self) -> None:
        copy_image_to_clipboard(self._canvas.render_image())
        self.statusBar().showMessage(
            tr("copied_status"),
            2500,
        )
        self._show_toast(tr("copied"))

    def _open_x(self) -> None:
        self._canvas.commit_inline_editing()
        copy_image_to_clipboard(self._canvas.render_image())
        webbrowser.open("https://x.com/compose/post")
        self.statusBar().showMessage(tr("opened_x"), 2500)
        self._show_toast(tr("image_copied_paste"))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            QApplication.quit()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
        QApplication.quit()
