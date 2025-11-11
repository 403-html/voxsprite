from __future__ import annotations

import platform
from pathlib import Path
from typing import cast

import numpy as np
import sounddevice as sound_device
from PIL import Image
from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QTextBrowser,
    QTextEdit,
    QAbstractButton,
)

from .. import config
from ..i18n import t


class AboutDialog(QDialog):
    def __init__(self, parent, homepage_url: str, issues_url: str):
        super().__init__(parent)
        self.setWindowTitle(t("about.title"))
        self.resize(520, 420)

        about_body = QTextBrowser(self)
        about_body.setOpenExternalLinks(True)
        about_body.setHtml(
            t("about.body_html").format(
                version=config.APP_VERSION,
                homepage=homepage_url,
                issues=issues_url,
            )
        )

        diagnostics_editor = QTextEdit(self)
        diagnostics_editor.setReadOnly(True)
        diagnostics_editor.setMinimumHeight(120)
        diagnostics_editor.setPlainText(self._diagnostics_summary())

        button_box = QDialogButtonBox(self)
        copy_button = cast(
            QAbstractButton,
            button_box.addButton(t("about.button.copy"), QDialogButtonBox.ButtonRole.ActionRole),
        )
        open_config_button = cast(
            QAbstractButton,
            button_box.addButton(t("about.button.config_folder"), QDialogButtonBox.ButtonRole.ActionRole),
        )
        button_box.addButton(QDialogButtonBox.StandardButton.Close)

        copy_button.clicked.connect(
            lambda: (clipboard := QApplication.clipboard())
            and clipboard.setText(diagnostics_editor.toPlainText())
        )
        open_config_button.clicked.connect(self._open_config_folder)
        button_box.rejected.connect(self.reject)

        dialog_layout = QGridLayout(self)
        dialog_layout.addWidget(about_body, 0, 0)
        dialog_layout.addWidget(diagnostics_editor, 1, 0)
        dialog_layout.addWidget(button_box, 2, 0)

    def _diagnostics_summary(self) -> str:
        try:
            portaudio_version_data = getattr(sound_device, "get_portaudio_version", lambda: (None, ""))()
            portaudio_number, portaudio_text = (
                (portaudio_version_data + ("",))[:2] if isinstance(portaudio_version_data, tuple) else (None, "")
            )
        except Exception:
            portaudio_number, portaudio_text = None, ""

        return (
            f"{t('diagnostics.app')}: {config.APP_VERSION}\n"
            f"{t('diagnostics.python')}: {platform.python_version()} ({platform.python_implementation()})\n"
            f"{t('diagnostics.os')}: {platform.system()} {platform.release()} ({platform.version()})\n"
            f"{t('diagnostics.arch')}: {platform.machine()}\n"
            f"{t('diagnostics.numpy')}: {np.__version__}\n"
            f"{t('diagnostics.pillow')}: {Image.__version__}\n"
            f"{t('diagnostics.pyqt')}: {PYQT_VERSION_STR} / Qt {QT_VERSION_STR}\n"
            f"{t('diagnostics.sounddevice')}: {getattr(sound_device, '__version__', 'unknown')}\n"
            f"{t('diagnostics.portaudio')}: {portaudio_number or 'unknown'} {portaudio_text}\n"
            f"{t('diagnostics.config_path')}: {Path.cwd() / config.SETTINGS_FILE}\n"
        )

    def _open_config_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path.cwd())))
