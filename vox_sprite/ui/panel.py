from __future__ import annotations

import copy
import time
import traceback
from pathlib import Path
from typing import Any, Union

from PyQt6.QtCore import QPoint, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QColor, QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QScrollArea,
    QDoubleSpinBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QMainWindow,
)

from .. import config
from ..audio import Mic
from ..dialogs.about import AboutDialog
from ..dialogs.shortcuts import ShortcutsDialog
from ..i18n import (
    DEFAULT_LANG,
    available_languages,
    current_language,
    set_language,
    t,
)
from ..widgets.avatar import AvatarWindow
from ..widgets.level_meter import LevelMeter


class PanelWindow(QMainWindow):
    def __init__(self, values: dict[str, Any] | None = None):
        super().__init__()
        if values is not None:
            self.values = copy.deepcopy(values)
        else:
            self.values = config.load_cfg()
        lang = self.values.get("language") or current_language() or DEFAULT_LANG
        self.values["language"] = set_language(lang)
        self.setWindowTitle(t("panel.title"))
        self._normalize_values()

        self.mic = Mic()
        self.level = 0.0
        self.last_switch = time.time()
        self._mic_error_notified = False

        initial_position = None
        if (
            self.values.get("remember_position")
            and isinstance(self.values.get("avatar_position"), list)
            and len(self.values["avatar_position"]) == 2
        ):
            x_position, y_position = self.values["avatar_position"]
            initial_position = (int(x_position), int(y_position))

        self.avatar = AvatarWindow(
            self.values,
            initial_position=initial_position,
            move_callback=self._on_avatar_moved,
        )
        self._avatar_closed = False

        self._build_ui()
        self._setup_menu()

    def _normalize_values(self):
        frames = self.values.get("idle_frames")
        if not isinstance(frames, list):
            frames = []
        frames = [str(p) for p in frames if p]
        self.values["idle_frames"] = frames
        existing_idle = str(self.values.get("idle_image") or "")
        self.values["idle_image"] = frames[0] if frames else existing_idle
        self.values.setdefault("talk_image", "")
        self.values.setdefault("idle_anim_random", False)
        self.values.setdefault("idle_interval_min", 0.2)
        self.values.setdefault("idle_interval_max", 0.6)
        self.values.setdefault("bg_transparent", False)
        self.values.setdefault("remember_position", False)
        avatar_position = self.values.get("avatar_position")
        if isinstance(avatar_position, list) and len(avatar_position) == 2:
            try:
                x_position = int(avatar_position[0])
                y_position = int(avatar_position[1])
                self.values["avatar_position"] = [x_position, y_position]
            except (TypeError, ValueError):
                self.values["avatar_position"] = []
        else:
            self.values["avatar_position"] = []
        talk_frames = self.values.get("talk_frames")
        if not isinstance(talk_frames, list):
            talk_frames = []
        normalized_talk_frames: list[dict[str, Any]] = []
        for frame in talk_frames:
            if not isinstance(frame, dict):
                continue
            path = str(frame.get("image") or "").strip()
            if not path:
                continue
            try:
                threshold = float(frame.get("threshold", 0.0))
            except (TypeError, ValueError):
                continue
            normalized_talk_frames.append({"image": path, "threshold": max(0.0, threshold)})
        normalized_talk_frames.sort(key=lambda item: item["threshold"])
        self.values["talk_frames"] = normalized_talk_frames
        min_interval = float(self.values["idle_interval_min"])
        max_interval = float(self.values["idle_interval_max"])
        if min_interval <= 0:
            min_interval = 0.1
        if max_interval < min_interval:
            max_interval = min_interval
        self.values["idle_interval_min"] = min_interval
        self.values["idle_interval_max"] = max_interval

    def _idle_paths(self) -> list[str]:
        return [str(p) for p in self.values.get("idle_frames", []) if p]

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        self.setCentralWidget(scroll)

        root = QVBoxLayout(container)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        lang_row = QHBoxLayout()
        self.lang_label = QLabel(t("panel.label.language"), self)
        self.lang_combo = QComboBox(self)
        self._populate_languages()
        self.lang_combo.currentIndexChanged.connect(self._handle_language_change)
        lang_row.addWidget(self.lang_label)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch(1)
        root.addLayout(lang_row)

        audio_group = QGroupBox(t("panel.group.audio"), self)
        audio_layout = QVBoxLayout(audio_group)
        audio_layout.setSpacing(12)

        self.level_meter = LevelMeter(self)
        self.level_meter.set_thresholds(float(self.values["talk_th"]), self._talk_thresholds())
        audio_layout.addWidget(self.level_meter)

        self.talk_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.talk_slider.setRange(1, 500)
        self.talk_slider.valueChanged.connect(self._handle_talk_slider)

        self.talk_spin = QDoubleSpinBox(self)
        self.talk_spin.setDecimals(3)
        self.talk_spin.setRange(0.001, 0.5)
        self.talk_spin.setSingleStep(0.001)
        self.talk_spin.valueChanged.connect(self._handle_talk_spin)

        talk_threshold_row = QHBoxLayout()
        talk_threshold_row.setSpacing(10)
        talk_threshold_row.addWidget(self.talk_slider, 1)
        talk_threshold_row.addWidget(self.talk_spin)
        talk_threshold_wrap = QWidget(self)
        talk_threshold_wrap.setLayout(talk_threshold_row)

        talk_form = QFormLayout()
        talk_form.setContentsMargins(0, 0, 0, 0)
        talk_form.addRow(t("panel.label.talk_threshold"), talk_threshold_wrap)
        audio_layout.addLayout(talk_form)
        self._apply_talk_threshold(float(self.values["talk_th"]))
        root.addWidget(audio_group)

        appearance_group = QGroupBox(t("panel.group.appearance"), self)
        appearance_form = QFormLayout()
        appearance_form.setSpacing(10)

        self.talk_edit = QLineEdit(str(self.values["talk_image"]), self)
        browse_talk = QPushButton(t("panel.button.browse"), self)
        browse_talk.clicked.connect(lambda: self._pick_image("talk"))
        talk_row = QHBoxLayout()
        talk_row.setSpacing(8)
        talk_row.addWidget(self.talk_edit)
        talk_row.addWidget(browse_talk)
        talk_wrap = QWidget(self)
        talk_wrap.setLayout(talk_row)
        appearance_form.addRow(t("panel.label.talking_image"), talk_wrap)

        talk_levels_box = QWidget(self)
        talk_levels_layout = QVBoxLayout(talk_levels_box)
        talk_levels_layout.setContentsMargins(0, 0, 0, 0)
        talk_levels_layout.setSpacing(8)

        self.talk_rows_layout = QVBoxLayout()
        self.talk_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.talk_rows_layout.setSpacing(6)
        talk_levels_layout.addLayout(self.talk_rows_layout)

        talk_add_row = QHBoxLayout()
        talk_add_row.setContentsMargins(0, 0, 0, 0)
        talk_add_row.setSpacing(6)
        self.add_talk_frame_btn = QPushButton(t("panel.button.add_level"), self)
        self.add_talk_frame_btn.clicked.connect(self._add_talk_frame_row)
        talk_add_row.addWidget(self.add_talk_frame_btn, 0, Qt.AlignmentFlag.AlignLeft)
        talk_add_row.addStretch(1)
        talk_levels_layout.addLayout(talk_add_row)
        appearance_form.addRow(t("panel.label.talk_levels"), talk_levels_box)
        self._rebuild_talk_rows()

        self.width_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.width_slider.setRange(64, 1024)
        self.width_slider.setValue(int(self.values["width"]))
        self.width_slider.valueChanged.connect(self._on_width_changed)
        self.width_value = QLabel(f"{self.values['width']} px", self)
        width_row = QHBoxLayout()
        width_row.setSpacing(8)
        width_row.addWidget(self.width_slider, 1)
        width_row.addWidget(self.width_value)
        width_wrap = QWidget(self)
        width_wrap.setLayout(width_row)
        appearance_form.addRow(t("panel.label.width"), width_wrap)

        self.bg_button = QPushButton(str(self.values["bg"]), self)
        self.bg_button.setStyleSheet(f"background:{self.values['bg']};")
        self.bg_button.clicked.connect(self._pick_bg_color)
        self.bg_transparent_cb = QCheckBox(t("panel.checkbox.transparent"), self)
        self.bg_transparent_cb.setChecked(bool(self.values.get("bg_transparent")))
        self.bg_transparent_cb.stateChanged.connect(
            lambda state: self._toggle_bg_transparent(state == Qt.CheckState.Checked.value)
        )
        bg_row = QHBoxLayout()
        bg_row.setSpacing(8)
        bg_row.addWidget(self.bg_button)
        bg_row.addWidget(self.bg_transparent_cb)
        bg_wrap = QWidget(self)
        bg_wrap.setLayout(bg_row)
        appearance_form.addRow(t("panel.label.background"), bg_wrap)

        appearance_group.setLayout(appearance_form)
        root.addWidget(appearance_group)

        idle_group = QGroupBox(t("panel.group.idle"), self)
        idle_layout = QVBoxLayout(idle_group)
        idle_layout.setSpacing(10)

        self.idle_list = QListWidget(self)
        self.idle_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._refresh_idle_frames_list()
        self.idle_list.setMinimumHeight(120)
        idle_layout.addWidget(self.idle_list)

        idle_btn_row = QHBoxLayout()
        idle_btn_row.setSpacing(6)
        add_idle = QPushButton(t("panel.button.add"), self)
        add_idle.clicked.connect(self._add_idle_frames)
        remove_idle = QPushButton(t("panel.button.remove"), self)
        remove_idle.clicked.connect(self._remove_idle_frames)
        up_idle = QPushButton(t("panel.button.up"), self)
        up_idle.clicked.connect(lambda: self._move_idle_frame(-1))
        down_idle = QPushButton(t("panel.button.down"), self)
        down_idle.clicked.connect(lambda: self._move_idle_frame(1))
        clear_idle = QPushButton(t("panel.button.clear"), self)
        clear_idle.clicked.connect(self._clear_idle_frames)
        for btn in (add_idle, remove_idle, up_idle, down_idle, clear_idle):
            idle_btn_row.addWidget(btn)
        idle_layout.addLayout(idle_btn_row)

        idle_opts_row = QHBoxLayout()
        idle_opts_row.setSpacing(8)
        self.idle_random_cb = QCheckBox(t("panel.checkbox.random_order"), self)
        self.idle_random_cb.setChecked(bool(self.values["idle_anim_random"]))
        self.idle_random_cb.stateChanged.connect(lambda state: self._toggle_idle_random(state))
        idle_opts_row.addWidget(self.idle_random_cb)
        idle_opts_row.addStretch(1)

        self.idle_interval_min_spin = QDoubleSpinBox(self)
        self.idle_interval_min_spin.setDecimals(2)
        self.idle_interval_min_spin.setRange(0.05, 10.0)
        self.idle_interval_min_spin.setSingleStep(0.05)
        self.idle_interval_min_spin.setSuffix(" s")
        self.idle_interval_min_spin.setValue(float(self.values["idle_interval_min"]))
        self.idle_interval_min_spin.valueChanged.connect(lambda value: self._on_idle_interval_changed("min", value))

        self.idle_interval_max_spin = QDoubleSpinBox(self)
        self.idle_interval_max_spin.setDecimals(2)
        self.idle_interval_max_spin.setRange(0.05, 10.0)
        self.idle_interval_max_spin.setSingleStep(0.05)
        self.idle_interval_max_spin.setSuffix(" s")
        self.idle_interval_max_spin.setValue(float(self.values["idle_interval_max"]))
        self.idle_interval_max_spin.valueChanged.connect(lambda value: self._on_idle_interval_changed("max", value))

        timing_row = QHBoxLayout()
        timing_row.setSpacing(6)
        timing_row.addWidget(QLabel(t("panel.label.interval")))
        timing_row.addWidget(self.idle_interval_min_spin)
        timing_row.addWidget(QLabel(t("panel.label.interval_to")))
        timing_row.addWidget(self.idle_interval_max_spin)
        timing_row.addStretch(1)
        idle_form = QVBoxLayout()
        idle_form.addLayout(idle_opts_row)
        idle_form.addLayout(timing_row)
        idle_layout.addLayout(idle_form)
        root.addWidget(idle_group)

        window_group = QGroupBox(t("panel.group.window"), self)
        window_layout = QVBoxLayout(window_group)
        window_layout.setSpacing(6)

        self.keep_on_top_cb = QCheckBox(t("panel.checkbox.keep_on_top"), self)
        self.keep_on_top_cb.setChecked(bool(self.values["keep_on_top"]))
        self.keep_on_top_cb.stateChanged.connect(lambda state: self._toggle_keep_on_top(state == Qt.CheckState.Checked.value))

        self.drag_enabled_cb = QCheckBox(t("panel.checkbox.allow_drag"), self)
        self.drag_enabled_cb.setChecked(bool(self.values["drag_enabled"]))
        self.drag_enabled_cb.stateChanged.connect(lambda state: self._toggle_drag(state == Qt.CheckState.Checked.value))

        self.remember_position_cb = QCheckBox(t("panel.checkbox.remember_position"), self)
        self.remember_position_cb.setChecked(bool(self.values.get("remember_position")))
        self.remember_position_cb.stateChanged.connect(
            lambda state: self._toggle_remember_position(state == Qt.CheckState.Checked.value)
        )

        window_layout.addWidget(self.keep_on_top_cb)
        window_layout.addWidget(self.drag_enabled_cb)
        window_layout.addWidget(self.remember_position_cb)
        root.addWidget(window_group)

        self.save_status = QLabel("", self)
        self.save_status.setStyleSheet("color:#2e7d32;font-size:12px;")
        self.save_status.setVisible(False)
        self.save_btn = QPushButton(t("panel.button.save"), self)
        self.save_btn.clicked.connect(self._save_settings)
        save_block = QVBoxLayout()
        save_block.setSpacing(4)
        save_block.addWidget(self.save_status, 0, Qt.AlignmentFlag.AlignRight)
        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_row.addWidget(self.save_btn)
        save_block.addLayout(save_row)
        root.addLayout(save_block)

        self._sync_bg_controls()
        self._sync_talk_markers()

        self.timer = QTimer(self)
        self.timer.setInterval(60)
        self.timer.timeout.connect(self._poll_mic)
        self.timer.start()

        self.resize(520, 680)
        self.show()
        self._sync_idle_anim_options()

    def _setup_menu(self):
        menu_bar = self.menuBar()
        if menu_bar is None:
            return
        help_menu = menu_bar.addMenu(t("menu.help"))
        if help_menu is None:
            return

        about_action = QAction(t("menu.about"), self)
        about_action.setShortcut("F1")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        shortcuts_action = QAction(t("menu.shortcuts"), self)
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        homepage_action = QAction(t("menu.homepage"), self)
        homepage_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/403-html/voxsprite"))
        )
        help_menu.addAction(homepage_action)

        issues_action = QAction(t("menu.issues"), self)
        issues_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/403-html/voxsprite/issues"))
        )
        help_menu.addAction(issues_action)

        open_cfg_action = QAction(t("menu.open_config"), self)
        open_cfg_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path.cwd())))
        )
        help_menu.addAction(open_cfg_action)

        save_action = QAction(t("menu.save"), self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_settings)
        self.addAction(save_action)

        quit_action = QAction(t("menu.quit"), self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)

    def _format_threshold(self, value: Union[float, int, str]) -> str:
        return f"{float(value):.3f}"

    def _pick_image(self, kind: str):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilters([t("file.filter.images"), t("file.filter.all")])
        if file_dialog.exec() != QFileDialog.DialogCode.Accepted:
            return
        path = file_dialog.selectedFiles()[0]
        if kind == "talk":
            self.values["talk_image"] = path
            self.talk_edit.setText(path)
            self._reload_avatar_images()
        else:
            self._set_idle_frames([path])

    def _pick_bg_color(self):
        color = QColorDialog.getColor(QColor(self.values["bg"]), self)
        if not color.isValid():
            return
        css = color.name(QColor.NameFormat.HexRgb)
        self.values["bg"] = css
        self.bg_button.setText(css)
        self.bg_button.setStyleSheet(f"background:{css};")
        self.avatar.set_bg(css)
        self._sync_bg_controls()

    def _toggle_bg_transparent(self, checked: bool):
        self.values["bg_transparent"] = checked
        self._sync_bg_controls()

    def _sync_bg_controls(self):
        transparent = bool(self.values.get("bg_transparent"))
        self.bg_button.setEnabled(not transparent)
        self.avatar.set_transparent_bg(transparent)
        if not transparent:
            self.avatar.set_bg(self.values["bg"])

    def _show_about(self):
        dialog = AboutDialog(
            self,
            homepage_url="https://github.com/403-html/voxsprite",
            issues_url="https://github.com/403-html/voxsprite/issues",
        )
        dialog.exec()

    def _show_shortcuts(self):
        dialog = ShortcutsDialog(self)
        dialog.exec()

    def _reload_avatar_images(self):
        self.avatar.load_images(
            self._idle_paths(),
            self._talk_image_payload(),
            int(self.values["width"]),
        )

    def _refresh_idle_frames_list(self):
        if not hasattr(self, "idle_list"):
            return
        self.idle_list.clear()
        for path in self.values["idle_frames"]:
            self.idle_list.addItem(path)

    def _talk_image_payload(self) -> dict[str, Any]:
        return {
            "default": str(self.values.get("talk_image", "")),
            "frames": list(self.values.get("talk_frames", [])),
        }

    def _talk_thresholds(self) -> list[float]:
        return [
            float(frame.get("threshold", 0.0))
            for frame in self.values.get("talk_frames", [])
            if isinstance(frame, dict)
        ]

    def _sync_talk_markers(self):
        if hasattr(self, "level_meter"):
            self.level_meter.set_thresholds(float(self.values["talk_th"]), self._talk_thresholds())

    def _on_avatar_moved(self, position: QPoint):
        if not bool(self.values.get("remember_position")):
            return
        self.values["avatar_position"] = [int(position.x()), int(position.y())]

    def _populate_languages(self):
        if not hasattr(self, "lang_combo"):
            return
        current = self.values.get("language", DEFAULT_LANG)
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        for code, name in available_languages().items():
            self.lang_combo.addItem(name, code)
        index = self.lang_combo.findData(current)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)
        self.lang_combo.blockSignals(False)

    def _handle_language_change(self):
        code = self.lang_combo.currentData()
        if not code or code == self.values.get("language"):
            return
        self.values["language"] = code
        snapshot = copy.deepcopy(self.values)
        snapshot["language"] = code

        def rebuild():
            self._capture_avatar_position()
            set_language(code)
            saved_geometry = self.geometry()
            self.close()
            app = QApplication.instance()
            new_window = PanelWindow(values=snapshot)
            new_window.setGeometry(saved_geometry)
            new_window.show()
            if app is not None:
                setattr(app, "_vox_panel", new_window)

        QTimer.singleShot(0, rebuild)

    def _rebuild_talk_rows(self):
        if not hasattr(self, "talk_rows_layout"):
            return
        while self.talk_rows_layout.count():
            item = self.talk_rows_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        frames = self._sorted_talk_frames()
        if not frames:
            empty = QLabel(t("panel.message.no_levels"), self)
            empty.setObjectName("talkLevelsEmpty")
            empty.setStyleSheet("color:#888;")
            self.talk_rows_layout.addWidget(empty)
            return
        for idx, frame in enumerate(frames):
            row = QWidget(self)
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)

            path_edit = QLineEdit(str(frame["image"]), row)
            path_edit.setReadOnly(True)
            layout.addWidget(path_edit, 1)

            pick_btn = QPushButton(t("panel.button.browse"), row)
            pick_btn.clicked.connect(lambda _, i=idx: self._pick_talk_row_image(i))
            layout.addWidget(pick_btn)

            spin = QDoubleSpinBox(row)
            spin.setDecimals(3)
            spin.setRange(0.001, 1.0)
            spin.setSingleStep(0.001)
            spin.setValue(float(frame["threshold"]))
            spin.valueChanged.connect(lambda value, i=idx: self._update_talk_row_threshold(i, value))
            layout.addWidget(spin)

            remove_btn = QPushButton(t("panel.button.remove"), row)
            remove_btn.clicked.connect(lambda _, i=idx: self._remove_talk_row(i))
            layout.addWidget(remove_btn)

            self.talk_rows_layout.addWidget(row)

    def _sorted_talk_frames(self) -> list[dict[str, Any]]:
        frames = [
            {"image": str(frame.get("image")), "threshold": float(frame.get("threshold", 0.0))}
            for frame in self.values.get("talk_frames", [])
            if isinstance(frame, dict) and frame.get("image")
        ]
        frames.sort(key=lambda item: item["threshold"])
        self.values["talk_frames"] = frames
        return frames

    def _select_talk_image(self, current: str = "") -> str | None:
        start_dir = str(Path(current).parent) if current else str(Path.cwd())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("file.dialog.talk_frame"),
            start_dir,
            ";;".join([t("file.filter.images"), t("file.filter.all")]),
        )
        if not file_path:
            return None
        return file_path

    def _add_talk_frame_row(self):
        frames = list(self.values.get("talk_frames", []))
        frames.append(
            {
                "image": str(self.values.get("talk_image", "")),
                "threshold": float(self.values.get("talk_th", 0.03)),
            }
        )
        self.values["talk_frames"] = frames
        self._sorted_talk_frames()
        self._rebuild_talk_rows()
        self._reload_avatar_images()
        self._sync_talk_markers()

    def _pick_talk_row_image(self, index: int):
        frames = list(self.values.get("talk_frames", []))
        if not (0 <= index < len(frames)):
            return
        current = frames[index].get("image", "")
        picked = self._select_talk_image(current)
        if not picked:
            return
        frames[index]["image"] = picked
        self.values["talk_frames"] = frames
        self._rebuild_talk_rows()
        self._reload_avatar_images()

    def _update_talk_row_threshold(self, index: int, value: float):
        frames = list(self.values.get("talk_frames", []))
        if not (0 <= index < len(frames)):
            return
        frames[index]["threshold"] = float(value)
        self.values["talk_frames"] = frames
        self._sorted_talk_frames()
        self._rebuild_talk_rows()
        self._reload_avatar_images()
        self._sync_talk_markers()

    def _remove_talk_row(self, index: int):
        frames = list(self.values.get("talk_frames", []))
        if not (0 <= index < len(frames)):
            return
        frames.pop(index)
        self.values["talk_frames"] = frames
        self._rebuild_talk_rows()
        self._reload_avatar_images()
        self._sync_talk_markers()

    def _set_idle_frames(self, frames: list[Any]):
        cleaned = [str(p) for p in frames if p]
        self.values["idle_frames"] = cleaned
        if cleaned:
            self.values["idle_image"] = cleaned[0]
        elif not self.values.get("idle_image"):
            self.values["idle_image"] = ""
        self._refresh_idle_frames_list()
        self._reload_avatar_images()

    def _add_idle_frames(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilters([t("file.filter.images"), t("file.filter.all")])
        if file_dialog.exec() != QFileDialog.DialogCode.Accepted:
            return
        existing = list(self.values["idle_frames"])
        for path in file_dialog.selectedFiles():
            if path not in existing:
                existing.append(path)
        self._set_idle_frames(existing)

    def _remove_idle_frames(self):
        rows = sorted({index.row() for index in self.idle_list.selectedIndexes()}, reverse=True)
        if not rows:
            return
        frames = list(self.values["idle_frames"])
        for row in rows:
            if 0 <= row < len(frames):
                frames.pop(row)
        self._set_idle_frames(frames)

    def _move_idle_frame(self, direction: int):
        if direction == 0 or not self.idle_list.count():
            return
        current = self.idle_list.currentRow()
        if current < 0:
            return
        target = current + direction
        if not (0 <= target < self.idle_list.count()):
            return
        frames = list(self.values["idle_frames"])
        frames[current], frames[target] = frames[target], frames[current]
        self._set_idle_frames(frames)
        self.idle_list.setCurrentRow(target)

    def _clear_idle_frames(self):
        if (
            QMessageBox.question(
                self,
                t("panel.dialog.clear_idle.title"),
                t("panel.dialog.clear_idle.body"),
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.values["idle_image"] = ""
        self._set_idle_frames([])

    def _toggle_idle_random(self, state: int):
        checked = state == int(Qt.CheckState.Checked.value)
        self.values["idle_anim_random"] = checked
        self._sync_idle_anim_options()

    def _on_idle_interval_changed(self, kind: str, value: float):
        min_val = float(self.values["idle_interval_min"])
        max_val = float(self.values["idle_interval_max"])
        if kind == "min":
            min_val = float(value)
            if min_val > max_val:
                max_val = min_val
                self.idle_interval_max_spin.blockSignals(True)
                self.idle_interval_max_spin.setValue(max_val)
                self.idle_interval_max_spin.blockSignals(False)
        else:
            max_val = float(value)
            if max_val < min_val:
                min_val = max_val
                self.idle_interval_min_spin.blockSignals(True)
                self.idle_interval_min_spin.setValue(min_val)
                self.idle_interval_min_spin.blockSignals(False)
        self.values["idle_interval_min"] = min_val
        self.values["idle_interval_max"] = max_val
        self._sync_idle_anim_options()

    def _sync_idle_anim_options(self):
        self.avatar.update_idle_anim_options(
            bool(self.values["idle_anim_random"]),
            float(self.values["idle_interval_min"]),
            float(self.values["idle_interval_max"]),
        )

    def _apply_talk_threshold(self, value: float, *, from_slider: bool = False, from_spin: bool = False):
        clamped = max(0.001, min(0.5, round(float(value), 3)))
        self.values["talk_th"] = clamped
        if not from_slider:
            self.talk_slider.blockSignals(True)
            self.talk_slider.setValue(int(clamped * 1000))
            self.talk_slider.blockSignals(False)
        if not from_spin:
            self.talk_spin.blockSignals(True)
            self.talk_spin.setValue(clamped)
            self.talk_spin.blockSignals(False)
        self._sync_talk_markers()

    def _handle_talk_slider(self, slider_value: int):
        self._apply_talk_threshold(slider_value / 1000.0, from_slider=True)

    def _handle_talk_spin(self, value: float):
        self._apply_talk_threshold(value, from_spin=True)

    def _on_width_changed(self, value: int):
        self.values["width"] = int(value)
        self.width_value.setText(f"{value} px")
        self._reload_avatar_images()

    def _toggle_keep_on_top(self, checked: bool):
        self.values["keep_on_top"] = checked
        self.avatar.keep_on_top = checked
        self.avatar.update_flags()

    def _toggle_drag(self, checked: bool):
        self.values["drag_enabled"] = checked
        self.avatar.drag_enabled = checked

    def _toggle_remember_position(self, checked: bool):
        self.values["remember_position"] = checked
        if checked:
            self._capture_avatar_position()
        else:
            self.values["avatar_position"] = []

    def _capture_avatar_position(self):
        if not self.avatar or not bool(self.values.get("remember_position")):
            return
        self.values["avatar_position"] = [int(self.avatar.x()), int(self.avatar.y())]

    def _save_settings(self):
        self._capture_avatar_position()
        config.save_cfg(self.values)
        self._show_save_status(t("panel.status.saved"))

    def _show_save_status(self, message: str):
        if not hasattr(self, "save_status"):
            return
        self.save_status.setText(message)
        self.save_status.setVisible(True)
        QTimer.singleShot(5000, lambda: self.save_status.setVisible(False))

    def _poll_mic(self):
        try:
            level = self.mic.read()
            self.level = (self.level * 0.7) + (level * 0.3)
            self.level_meter.set_level(self.level)
            self.avatar.set_talk_level(self.level)

            now = time.time()
            talking = self.avatar.is_talking
            talk_th = float(self.values["talk_th"])
            release_th = talk_th * 0.7
            if talking:
                if self.level < release_th and (now - self.last_switch) > 0.05:
                    self.avatar.set_talking(False)
                    self.last_switch = now
            else:
                if self.level > talk_th and (now - self.last_switch) > 0.05:
                    self.avatar.set_talking(True)
                    self.last_switch = now
        except Exception as exception_instance:
            if self.timer.isActive():
                self.timer.stop()
            if not self._mic_error_notified:
                self._mic_error_notified = True
                traceback.print_exc()
                QMessageBox.critical(
                    self,
                    t("panel.error.mic_title"),
                    t("panel.error.mic_body", error=exception_instance),
                )

    def closeEvent(self, event):
        if self.timer.isActive():
            self.timer.stop()
        self.timer.deleteLater()
        if self.mic.stream:
            try:
                self.mic.stream.stop()
                self.mic.stream.close()
            except Exception:
                pass
        self._capture_avatar_position()
        if self.avatar and not self._avatar_closed:
            self.avatar.close()
            self._avatar_closed = True
        super().closeEvent(event)
