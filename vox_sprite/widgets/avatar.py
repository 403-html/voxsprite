from __future__ import annotations

import random
from typing import Callable, Optional

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QMessageBox, QWidget

from ..i18n import t
from ..image_utils import load_scaled

class AvatarWindow(QWidget):
    def __init__(
        self,
        config_values: dict,
        initial_position: Optional[tuple[int, int]] = None,
        move_callback: Optional[Callable[[QPoint], None]] = None,
    ):
        super().__init__()
        self.setWindowTitle(t("avatar.window.title"))
        self.transparent_bg = bool(config_values.get("bg_transparent", False))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.label = QLabel(self)
        self.bg_color = config_values["bg"]
        self._apply_bg_style()
        self.keep_on_top = config_values["keep_on_top"]
        self.drag_enabled = config_values["drag_enabled"]
        self._press_pos: Optional[QPoint] = None
        self._win_pos: Optional[QPoint] = None
        self._move_callback = move_callback
        self._initial_position = initial_position

        self.idle_pix_list: list[QPixmap] = []
        self.idle_index = 0
        self.talk_pix: Optional[QPixmap] = None
        self.talk_variants: list[tuple[float, QPixmap]] = []
        self.talk_level = 0.0
        self.is_talking = False
        self.idle_random = bool(config_values.get("idle_anim_random", False))
        self.idle_interval_min = float(config_values.get("idle_interval_min", 0.2))
        self.idle_interval_max = float(config_values.get("idle_interval_max", 0.6))
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._advance_idle_frame)

        self.update_flags()
        idle_paths = config_values.get("idle_frames") or [config_values["idle_image"]]
        talk_payload = {"default": config_values["talk_image"], "frames": config_values.get("talk_frames", [])}
        self.load_images(idle_paths, talk_payload, config_values["width"])
        self.show()
        self._apply_initial_position()

    def update_flags(self):
        flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        if self.keep_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def load_images(self, idle_paths: list[str], talk_source, width: int):
        try:
            pix_list: list[QPixmap] = []
            idle_errors: list[str] = []
            for path in (path for path in idle_paths if path):
                try:
                    pix_list.append(load_scaled(path, int(width)))
                except Exception as exception_instance:
                    idle_errors.append(f"{path}: {exception_instance}")
            self.idle_pix_list = pix_list
            self.idle_index = 0

            talk_default_path = ""
            talk_frames_data: list[dict] = []
            if isinstance(talk_source, dict):
                talk_default_path = str(talk_source.get("default", "")).strip()
                talk_frames_data = list(talk_source.get("frames", []))
            else:
                talk_default_path = str(talk_source)

            self.talk_pix = None
            if talk_default_path:
                try:
                    self.talk_pix = load_scaled(talk_default_path, int(width))
                except Exception as exception_instance:
                    idle_errors.append(f"{talk_default_path}: {exception_instance}")

            variants: list[tuple[float, QPixmap]] = []
            variant_errors = []
            for frame in talk_frames_data:
                if not isinstance(frame, dict):
                    continue
                path = str(frame.get("image") or "").strip()
                if not path:
                    continue
                try:
                    threshold = float(frame.get("threshold", 0.0))
                    pixmap = load_scaled(path, int(width))
                    variants.append((threshold, pixmap))
                except Exception as exception_instance:
                    variant_errors.append(f"{path}: {exception_instance}")
            variants.sort(key=lambda item: item[0])
            self.talk_variants = variants
            if idle_errors:
                QMessageBox.warning(
                    self,
                    t("avatar.error.images_title"),
                    t("avatar.error.images_body", details="\n".join(idle_errors)),
                )
            if variant_errors:
                QMessageBox.warning(
                    self,
                    t("avatar.error.talk_frames_title"),
                    t("avatar.error.talk_frames_body", details="\n".join(variant_errors)),
                )
        except Exception as exception_instance:
            QMessageBox.warning(
                self,
                t("avatar.error.images_title"),
                t("avatar.error.images_body", details=str(exception_instance)),
            )
            return
        self.refresh()
        self._update_idle_timer()

    def update_idle_anim_options(self, random_order: bool, interval_min: float, interval_max: float):
        self.idle_random = random_order
        self.idle_interval_min = max(0.05, float(interval_min))
        self.idle_interval_max = max(self.idle_interval_min, float(interval_max))
        self._update_idle_timer()

    def _current_idle_pix(self) -> Optional[QPixmap]:
        if not self.idle_pix_list:
            return None
        return self.idle_pix_list[self.idle_index % len(self.idle_pix_list)]

    def _advance_idle_frame(self):
        if not self.idle_pix_list or self.is_talking:
            self._update_idle_timer()
            return
        if self.idle_random:
            self.idle_index = random.randrange(len(self.idle_pix_list))
        else:
            self.idle_index = (self.idle_index + 1) % len(self.idle_pix_list)
        self.refresh()
        self._update_idle_timer()

    def _update_idle_timer(self):
        if len(self.idle_pix_list) <= 1 or self.is_talking:
            self.idle_timer.stop()
            return
        interval = random.uniform(self.idle_interval_min, self.idle_interval_max)
        self.idle_timer.start(int(interval * 1000))

    def _resolve_talk_variant(self, level: Optional[float] = None) -> tuple[int, Optional[QPixmap]]:
        current_level = self.talk_level if level is None else max(0.0, float(level))
        best_index = -1
        candidate = self.talk_pix
        for variant_index, (threshold, pixmap) in enumerate(self.talk_variants):
            if current_level >= threshold:
                best_index = variant_index
                candidate = pixmap
        return best_index, candidate

    def set_talk_level(self, level: float):
        level = max(0.0, float(level))
        previous_index, _ = self._resolve_talk_variant()
        self.talk_level = level
        new_index, _ = self._resolve_talk_variant()
        if self.is_talking and previous_index != new_index:
            self.refresh()

    def set_talking(self, talking: bool):
        if self.is_talking == talking:
            return
        self.is_talking = talking
        if self.is_talking:
            self._resolve_talk_variant()  # ensure cached
        self.refresh()
        self._update_idle_timer()

    def closeEvent(self, event):
        if self.idle_timer.isActive():
            self.idle_timer.stop()
        super().closeEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._move_callback:
            self._move_callback(self.pos())

    def _apply_initial_position(self):
        if not self._initial_position:
            return
        x_pos, y_pos = self._initial_position
        self.move(int(x_pos), int(y_pos))
        QTimer.singleShot(0, lambda: self.move(int(x_pos), int(y_pos)))

    def set_bg(self, css_color: str):
        self.bg_color = css_color
        if not self.transparent_bg:
            self._apply_bg_style()

    def set_transparent_bg(self, enabled: bool):
        if self.transparent_bg == enabled:
            return
        self.transparent_bg = enabled
        self._apply_bg_style()

    def _apply_bg_style(self):
        if self.transparent_bg:
            self.setStyleSheet("background: transparent;")
            self.label.setStyleSheet("background: transparent;")
        else:
            self.setStyleSheet(f"background:{self.bg_color};")
            self.label.setStyleSheet(f"background:{self.bg_color};")

    def refresh(self):
        if self.is_talking:
            _, pixmap = self._resolve_talk_variant()
        else:
            pixmap = self._current_idle_pix()
        if not pixmap:
            self.label.setText(t("avatar.placeholder.no_images"))
            self.label.adjustSize()
            return
        self.label.setText("")
        self.label.setPixmap(pixmap)
        self.label.resize(pixmap.size())
        self.resize(pixmap.size())

    def mousePressEvent(self, event):
        if not self.drag_enabled:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._win_pos = self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if not self.drag_enabled or self._press_pos is None or self._win_pos is None:
            return
        delta = event.globalPosition().toPoint() - self._press_pos
        self.move(self._win_pos + delta)

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        self._win_pos = None
