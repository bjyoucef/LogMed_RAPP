"""
Point d'entrée principal de l'application LogMed RAPP.
"""
import sys
import os
import ctypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Définition de l'AppUserModelID pour que la barre des tâches Windows affiche l'icône personnalisée
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("logmed.rapp.reconciliation.1.0")
except Exception:
    pass

# Support High-DPI displays
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from ui.theme import get_theme_stylesheet
from ui.main_window import MainWindow
from ui.assets import get_app_icon

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LogMed RAPP")
    app.setOrganizationName("LogMed")
    app.setWindowIcon(get_app_icon())
    app.setStyleSheet(get_theme_stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
