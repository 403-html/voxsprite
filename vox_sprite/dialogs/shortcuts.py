from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout

from ..i18n import t


class ShortcutsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(t("shortcuts.title"))
        self.resize(420, 260)

        text = QTextBrowser(self)
        text.setOpenExternalLinks(True)
        text.setHtml(t("shortcuts.body_html"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(text)
        layout.addWidget(buttons)
