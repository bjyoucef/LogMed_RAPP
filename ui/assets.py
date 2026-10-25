"""
Gestionnaire des ressources et icônes pour LogMed RAPP.
"""
import sys
import os
from PyQt5.QtGui import QIcon, QPixmap

def get_asset_path(filename: str) -> str:
    """
    Retourne le chemin absolu d'un fichier dans le répertoire assets,
    compatible à la fois en mode développement (source) et en mode packagé (PyInstaller).
    """
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        # Racine du dépôt (parent du dossier ui/)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "assets", filename)

def get_app_icon() -> QIcon:
    """
    Retourne l'icône officielle de l'application LogMed RAPP.
    """
    ico_path = get_asset_path("app_icon.ico")
    if os.path.exists(ico_path):
        return QIcon(ico_path)
    png_path = get_asset_path("app_icon.png")
    if os.path.exists(png_path):
        return QIcon(png_path)
    return QIcon()
