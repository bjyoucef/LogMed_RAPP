"""
Point d'entrée principal de l'application LogMed RAPP.
"""
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Support High-DPI displays
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from ui.theme import get_theme_stylesheet
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LogMed RAPP")
    app.setOrganizationName("LogMed")
    app.setStyleSheet(get_theme_stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
