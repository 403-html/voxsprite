from __future__ import annotations

import sys
from PyQt6.QtWidgets import QApplication

from .error_handler import install_exception_hook
from .i18n import t
from .ui.panel import PanelWindow

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(t("app.name"))
    app.setOrganizationName(t("app.name"))
    install_exception_hook()
    panel = PanelWindow()
    panel.show()
    sys.exit(app.exec())
