"""
Composant de glisser-déposer de fichier Excel/CSV avec sélecteur d'onglets.
"""
import os
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QFileDialog, QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from core.file_reader import get_file_sheets

class DropZoneCard(QFrame):
    file_loaded = pyqtSignal(str, str) # file_path, sheet_name

    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.title_text = title
        self.subtitle_text = subtitle
        self.current_file_path = ""
        self.current_sheet = ""

        self.setAcceptDrops(True)
        self.setObjectName("dropZoneCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty("class", "card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # En-tête
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        self.lbl_title = QLabel(self.title_text)
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1e3a8a;")
        header_layout.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel(self.subtitle_text)
        self.lbl_subtitle.setStyleSheet("font-size: 12px; color: #64748b;")
        header_layout.addWidget(self.lbl_subtitle)
        layout.addLayout(header_layout)

        # Zone centrale d'instruction
        self.drop_area = QFrame()
        self.drop_area.setObjectName("dropArea")
        self.drop_area.setStyleSheet("""
            #dropArea {
                border: 2px dashed #cbd5e1;
                border-radius: 12px;
                background-color: #f8fafc;
            }
            #dropArea:hover {
                border-color: #2563eb;
                background-color: #eff6ff;
            }
        """)
        area_layout = QVBoxLayout(self.drop_area)
        area_layout.setContentsMargins(20, 30, 20, 30)
        area_layout.setSpacing(10)
        area_layout.setAlignment(Qt.AlignCenter)

        self.lbl_icon = QLabel("📂")
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet("font-size: 32px; background: transparent;")
        area_layout.addWidget(self.lbl_icon)

        self.lbl_drop_hint = QLabel("Glissez-déposez votre fichier ici<br><span style='color:#94a3b8; font-size:11px;'>ou</span>")
        self.lbl_drop_hint.setAlignment(Qt.AlignCenter)
        self.lbl_drop_hint.setStyleSheet("color: #475569; font-size: 13px; font-weight: 500; background: transparent;")
        area_layout.addWidget(self.lbl_drop_hint)

        self.btn_browse = QPushButton("📁 Parcourir le fichier...")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self.browse_file)
        area_layout.addWidget(self.btn_browse, alignment=Qt.AlignCenter)

        layout.addWidget(self.drop_area, 1)

        # Sélecteur d'onglet si classeur Excel
        self.sheet_widget = QWidget()
        sheet_layout = QHBoxLayout(self.sheet_widget)
        sheet_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_sheet = QLabel("📑 Feuille / Onglet :")
        lbl_sheet.setStyleSheet("font-weight: 600; font-size: 12px; color: #334155;")
        sheet_layout.addWidget(lbl_sheet)

        self.combo_sheet = QComboBox()
        self.combo_sheet.currentIndexChanged.connect(self.on_sheet_changed)
        sheet_layout.addWidget(self.combo_sheet, 1)
        self.sheet_widget.setVisible(False)
        layout.addWidget(self.sheet_widget)

        # Info fichier chargé
        self.lbl_info = QLabel("Aucun fichier sélectionné")
        self.lbl_info.setStyleSheet("font-size: 12px; color: #94a3b8; padding: 4px 0px;")
        layout.addWidget(self.lbl_info)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if os.path.splitext(path)[1].lower() in ('.xlsx', '.xls', '.xlsm', '.csv', '.tsv', '.txt'):
                    event.acceptProposedAction()
                    self.drop_area.setStyleSheet("#dropArea { border: 2px dashed #2563eb; background-color: #dbeafe; border-radius: 12px; }")

    def dragLeaveEvent(self, event):
        self.drop_area.setStyleSheet("""
            #dropArea {
                border: 2px dashed #cbd5e1;
                border-radius: 12px;
                background-color: #f8fafc;
            }
            #dropArea:hover {
                border-color: #2563eb;
                background-color: #eff6ff;
            }
        """)

    def dropEvent(self, event):
        self.drop_area.setStyleSheet("""
            #dropArea {
                border: 2px dashed #cbd5e1;
                border-radius: 12px;
                background-color: #f8fafc;
            }
            #dropArea:hover {
                border-color: #2563eb;
                background-color: #eff6ff;
            }
        """)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.load_file(path)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Sélectionner le fichier pour {self.title_text}",
            "",
            "Tableaux (*.xlsx *.xls *.csv *.tsv);;Tous les fichiers (*.*)"
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path: str):
        if not os.path.exists(file_path):
            return
        self.current_file_path = file_path
        file_name = os.path.basename(file_path)
        
        sheets = get_file_sheets(file_path)
        self.combo_sheet.blockSignals(True)
        self.combo_sheet.clear()
        self.combo_sheet.addItems(sheets)
        self.combo_sheet.blockSignals(False)
        
        self.sheet_widget.setVisible(len(sheets) > 1)
        self.current_sheet = sheets[0] if sheets else ""

        self.lbl_info.setText(f"✓ Chargé : <b>{file_name}</b> ({os.path.getsize(file_path)//1024} Ko)")
        self.lbl_info.setStyleSheet("font-size: 11px; color: #059669;")
        self.file_loaded.emit(self.current_file_path, self.current_sheet)

    def on_sheet_changed(self):
        self.current_sheet = self.combo_sheet.currentText()
        if self.current_file_path:
            self.file_loaded.emit(self.current_file_path, self.current_sheet)
