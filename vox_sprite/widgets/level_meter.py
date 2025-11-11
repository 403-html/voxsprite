from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QRectF, Qt, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ..i18n import t

class LevelMeter(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.level = 0.0
        self.talk_th = 0.03
        self.talk_levels: list[float] = []
        self.setMinimumHeight(42)

    def set_level(self, value: float):
        self.level = max(0.0, float(value))
        self.update()

    def set_threshold(self, talk: float):
        self.set_thresholds(talk, self.talk_levels)

    def set_thresholds(self, talk: float, levels: list[float]):
        self.talk_th = max(0.0, float(talk))
        self.talk_levels = sorted(max(0.0, float(value)) for value in levels)
        self.update()

    def _scale_value(self) -> float:
        return max(0.001, max(self.level, self.talk_th) * 1.5)

    def _value_to_x(self, rect: QRectF, value: float) -> float:
        scale = self._scale_value()
        ratio = max(0.0, min(1.0, float(value) / scale))
        return rect.left() + rect.width() * ratio

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        base_color = self.palette().base()
        painter.fillRect(rect, base_color)
        painter.setPen(self.palette().mid().color())
        painter.drawRoundedRect(rect, 6, 6)

        level_rect = QRectF(rect)
        level_rect.setWidth(self._value_to_x(rect, self.level) - rect.left())
        if level_rect.width() > 0:
            painter.fillRect(level_rect, QColor("#4CAF50"))

        painter.setPen(QPen(QColor("#FFC107"), 2))
        talk_x = self._value_to_x(rect, self.talk_th)
        painter.drawLine(
            QPointF(talk_x, rect.top()),
            QPointF(talk_x, rect.bottom()),
        )

        if self.talk_levels:
            marker_pen = QPen(QColor("#FF5722"), 1, Qt.PenStyle.DashLine)
            painter.setPen(marker_pen)
            for level in self.talk_levels:
                marker_x = self._value_to_x(rect, level)
                painter.drawLine(
                    QPointF(marker_x, rect.top()),
                    QPointF(marker_x, rect.bottom()),
                )

        painter.setPen(self.palette().text().color())
        summary = t("meter.summary", level=self.level, talk=self.talk_th)
        if self.talk_levels:
            summary += t(
                "meter.extra",
                levels=", ".join(f"{lvl:.3f}" for lvl in self.talk_levels),
            )
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, summary)
