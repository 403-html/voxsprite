from __future__ import annotations

import sys
import traceback
from typing import Callable, Optional, Type

from PyQt6.QtWidgets import QApplication, QMessageBox

from .i18n import t


def install_exception_hook() -> None:
    original_hook = sys.excepthook

    def handle_exception(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            original_hook(exc_type, exc_value, exc_traceback)
            return

        diagnostics = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        message_box = QMessageBox()
        message_box.setIcon(QMessageBox.Icon.Critical)
        message_box.setWindowTitle(t("error.unexpected.title"))
        message_box.setText(t("error.unexpected.body"))
        message_box.setDetailedText(diagnostics)
        copy_button = message_box.addButton(t("error.unexpected.copy"), QMessageBox.ButtonRole.ActionRole)
        message_box.addButton(QMessageBox.StandardButton.Close)
        message_box.exec()
        if message_box.clickedButton() == copy_button:
            QApplication.clipboard().setText(diagnostics)

    sys.excepthook = handle_exception
