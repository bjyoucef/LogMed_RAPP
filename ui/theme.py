"""
Feuille de style QSS moderne inspirée du design system LogMed.
"""

def get_theme_stylesheet() -> str:
    return """
    /* Global Styles */
    QWidget {
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
        font-size: 13px;
        color: #1e293b;
    }
    
    /* Fenêtre principale & Conteneur */
    QMainWindow, QWidget#centralWidget {
        background-color: #f1f5f9;
    }
    
    QLabel {
        background: transparent;
    }
    
    /* Cartes & Panneaux */
    QFrame[class="card"], QWidget[class="card"], #dropZoneCard {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
    }
    
    QFrame[class="hero-card"], QFrame#heroCard {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e3a8a, stop:1 #0f172a);
        border-radius: 14px;
        border: none;
    }
    
    /* Boutons standards */
    QPushButton {
        background-color: #ffffff;
        color: #1e293b;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: 600;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #f8fafc;
        border-color: #94a3b8;
    }
    QPushButton:pressed {
        background-color: #e2e8f0;
    }
    QPushButton:disabled {
        background-color: #f8fafc;
        color: #94a3b8;
        border-color: #e2e8f0;
    }
    QPushButton:checked {
        background-color: #1e3a8a;
        color: #ffffff;
        border-color: #1e3a8a;
    }
    
    /* Boutons de navigation d'onglets */
    QPushButton[class="nav-tab"] {
        background-color: #ffffff;
        color: #475569;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
    }
    QPushButton[class="nav-tab"]:hover {
        background-color: #f8fafc;
        color: #1e3a8a;
        border-color: #94a3b8;
    }
    QPushButton[class="nav-tab"]:checked {
        background-color: #1e3a8a;
        color: #ffffff;
        border-color: #1e3a8a;
    }

    /* Onglet Atelier Manuel */
    QPushButton[class="nav-tab-manual"] {
        background-color: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 700;
        font-size: 13px;
    }
    QPushButton[class="nav-tab-manual"]:hover {
        background-color: #dbeafe;
        border-color: #93c5fd;
    }
    QPushButton[class="nav-tab-manual"]:checked {
        background-color: #1e40af;
        color: #ffffff;
        border-color: #1e40af;
    }

    /* Boutons de sous-filtres (Pilules) */
    QPushButton[class="filter-pill"] {
        background-color: #f1f5f9;
        color: #475569;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: 500;
    }
    QPushButton[class="filter-pill"]:hover {
        background-color: #e2e8f0;
        color: #1e293b;
    }
    QPushButton[class="filter-pill"]:checked {
        background-color: #1e293b;
        color: #ffffff;
        border-color: #1e293b;
        font-weight: 600;
    }

    /* Bouton Primaire */
    QPushButton[class="btn-primary"] {
        background-color: #1e3a8a;
        color: #ffffff;
        border: 1px solid #1e3a8a;
    }
    QPushButton[class="btn-primary"]:hover {
        background-color: #2563eb;
        border-color: #2563eb;
    }
    QPushButton[class="btn-primary"]:pressed {
        background-color: #1d4ed8;
    }
    QPushButton[class="btn-primary"]:disabled {
        background-color: #e2e8f0;
        color: #94a3b8;
        border-color: #cbd5e1;
    }
    
    /* Bouton Succès / Export */
    QPushButton[class="btn-success"] {
        background-color: #059669;
        color: #ffffff;
        border: 1px solid #059669;
    }
    QPushButton[class="btn-success"]:hover {
        background-color: #047857;
        border-color: #047857;
    }
    QPushButton[class="btn-success"]:pressed {
        background-color: #065f46;
    }
    
    /* Bouton Danger */
    QPushButton[class="btn-danger"] {
        background-color: #ffffff;
        color: #dc2626;
        border: 1px solid #fecaca;
    }
    QPushButton[class="btn-danger"]:hover {
        background-color: #fee2e2;
        border-color: #ef4444;
    }
    QPushButton[class="btn-danger"]:pressed {
        background-color: #fca5a5;
    }
    
    /* Champs de saisie & listes déroulantes */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 5px 8px;
        color: #1e293b;
        selection-background-color: #bfdbfe;
        selection-color: #1e3a8a;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
        border: 2px solid #3b82f6;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid #e2e8f0;
    }
    QComboBox QAbstractItemView {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        selection-background-color: #dbeafe;
        selection-color: #1e3a8a;
        padding: 4px;
    }

    /* Style spécifique pour les widgets intégrés aux cellules de tableau */
    QTableWidget QComboBox {
        margin: 2px 3px;
        padding: 4px 8px;
        min-height: 26px;
    }
    
    QTableWidget QLineEdit {
        margin: 2px 3px;
        padding: 4px 6px;
        min-height: 26px;
    }
    
    /* Tableaux */
    QTableWidget {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        gridline-color: #f1f5f9;
        alternate-background-color: #f8fafc;
        selection-background-color: #dbeafe;
        selection-color: #1e3a8a;
        outline: none;
    }
    QTableWidget::item {
        padding: 5px 8px;
        border-bottom: 1px solid #f1f5f9;
    }
    QTableWidget::item:selected {
        background-color: #dbeafe;
        color: #1e3a8a;
        font-weight: 600;
    }
    QHeaderView::section {
        background-color: #f8fafc;
        color: #334155;
        padding: 8px 10px;
        border: none;
        border-bottom: 2px solid #cbd5e1;
        border-right: 1px solid #f1f5f9;
        font-weight: 600;
        font-size: 12px;
    }
    
    /* Splitter */
    QSplitter::handle:horizontal {
        background-color: #e2e8f0;
        width: 6px;
        margin: 2px 0px;
        border-radius: 3px;
    }
    QSplitter::handle:horizontal:hover {
        background-color: #3b82f6;
    }

    /* Barre de progression */
    QProgressBar {
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        background-color: #f1f5f9;
        text-align: center;
        color: #1e293b;
        font-weight: bold;
    }
    QProgressBar::chunk {
        background-color: #2563eb;
        border-radius: 5px;
    }
    
    /* Scrollbars */
    QScrollBar:vertical {
        background: #f8fafc;
        width: 10px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #cbd5e1;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #94a3b8;
    }
    QScrollBar:horizontal {
        background: #f8fafc;
        height: 10px;
        margin: 0px;
    }
    QScrollBar::handle:horizontal {
        background: #cbd5e1;
        min-width: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #94a3b8;
    }
    """