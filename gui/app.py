"""Точка входа GUI RepairExpert AI (PySide6).

Запуск:
    python -m gui.app
    repairexpert-gui   (через entry-point)
"""
from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication, QDialog

from gui.api_client import APIClient
from gui.login_dialog import LoginDialog
from gui.main_window import MainWindow

_API_URL = os.environ.get("REPAIREXPERT_API_URL", "http://127.0.0.1:8077")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("RepairExpert AI")

    client = APIClient(_API_URL)

    login = LoginDialog(client)
    if login.exec() != QDialog.DialogCode.Accepted:
        return 0

    window = MainWindow(client)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
