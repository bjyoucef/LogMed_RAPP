"""
Boîte de dialogue moderne permettant à l'utilisateur de choisir précisément
les colonnes des Tableaux A et B à inclure dans les résultats de rapprochement et l'export Excel.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QGroupBox, QFrame,
    QMessageBox
)
from PyQt5.QtCore import Qt
from typing import List, Tuple, Optional
from ui.assets import get_app_icon

class ColumnSelectorDialog(QDialog):
    def __init__(
        self,
        all_cols_a: List[str],
        all_cols_b: List[str],
        selected_cols_a: Optional[List[str]] = None,
        selected_cols_b: Optional[List[str]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Personnaliser les colonnes de résultat")
        self.setWindowIcon(get_app_icon())
        self.resize(720, 540)
        self.setMinimumSize(600, 450)

        self.all_cols_a = list(all_cols_a)
        self.all_cols_b = list(all_cols_b)
        
        # Par défaut, toutes les colonnes si rien n'est spécifié
        self.init_sel_a = set(selected_cols_a if selected_cols_a is not None else self.all_cols_a)
        self.init_sel_b = set(selected_cols_b if selected_cols_b is not None else self.all_cols_b)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # En-tête explicatif
        lbl_title = QLabel("⚙️ Colonnes à inclure dans les résultats et l'export")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #1e3a8a;")
        lbl_sub = QLabel("Cochez les colonnes souhaitées pour chaque tableau. Seules les colonnes cochées apparaîtront dans la grille et le fichier Excel généré.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #64748b;")
        lbl_sub.setWordWrap(True)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # Conteneur des deux panneaux (Tableau A et Tableau B)
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(16)

        # Panneau Tableau A
        panel_a, self.list_a, self.search_a, self.lbl_count_a = self.create_column_panel(
            "📄 Tableau Source A", self.all_cols_a, self.init_sel_a, "#1e3a8a"
        )
        panels_layout.addWidget(panel_a)

        # Panneau Tableau B
        panel_b, self.list_b, self.search_b, self.lbl_count_b = self.create_column_panel(
            "📑 Tableau Source B", self.all_cols_b, self.init_sel_b, "#0284c7"
        )
        panels_layout.addWidget(panel_b)

        layout.addLayout(panels_layout, 1)

        # Barre inférieure
        footer_layout = QHBoxLayout()
        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155;")
        footer_layout.addWidget(self.lbl_total)

        footer_layout.addStretch()

        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(btn_cancel)

        btn_apply = QPushButton("✓ Appliquer la sélection")
        btn_apply.setProperty("class", "btn-primary")
        btn_apply.clicked.connect(self.on_apply)
        footer_layout.addWidget(btn_apply)

        layout.addLayout(footer_layout)

        self.update_counts()

    def create_column_panel(self, title: str, cols: List[str], selected_set: set, accent_color: str):
        box = QGroupBox(title)
        box.setStyleSheet(f"""
            QGroupBox {{
                font-size: 13px;
                font-weight: 700;
                color: {accent_color};
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: #ffffff;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                background-color: #ffffff;
            }}
        """)
        panel_layout = QVBoxLayout(box)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(8)

        # Barre de recherche rapide
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("🔍 Filtrer les colonnes...")
        search_edit.setStyleSheet("padding: 5px 8px; border: 1px solid #e2e8f0; border-radius: 6px;")
        panel_layout.addWidget(search_edit)

        # Liste avec cases à cocher
        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background-color: #f8fafc;
            }
            QListWidget::item {
                padding: 5px 8px;
                border-bottom: 1px solid #f1f5f9;
            }
            QListWidget::item:hover {
                background-color: #e2e8f0;
            }
        """)
        for c in cols:
            item = QListWidgetItem(c)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if c in selected_set else Qt.Unchecked)
            list_widget.addItem(item)
        panel_layout.addWidget(list_widget, 1)

        # Barre de raccourcis : Tout cocher / Décocher
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(6)

        btn_all = QPushButton("☑ Tout cocher")
        btn_all.setStyleSheet("padding: 4px 8px; font-size: 11px;")
        btn_all.clicked.connect(lambda: self.set_all_checked(list_widget, True))
        btn_bar.addWidget(btn_all)

        btn_none = QPushButton("☐ Tout décocher")
        btn_none.setStyleSheet("padding: 4px 8px; font-size: 11px;")
        btn_none.clicked.connect(lambda: self.set_all_checked(list_widget, False))
        btn_bar.addWidget(btn_none)

        btn_bar.addStretch()

        lbl_count = QLabel(f"0 / {len(cols)}")
        lbl_count.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748b;")
        btn_bar.addWidget(lbl_count)

        panel_layout.addLayout(btn_bar)

        # Événements de recherche et changement de case
        search_edit.textChanged.connect(lambda text: self.filter_list(list_widget, text))
        list_widget.itemChanged.connect(lambda _: self.update_counts())

        return box, list_widget, search_edit, lbl_count

    def filter_list(self, list_widget: QListWidget, text: str):
        q = text.strip().lower()
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            item.setHidden(bool(q and q not in item.text().lower()))

    def set_all_checked(self, list_widget: QListWidget, checked: bool):
        target_state = Qt.Checked if checked else Qt.Unchecked
        list_widget.blockSignals(True)
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if not item.isHidden():
                item.setCheckState(target_state)
        list_widget.blockSignals(False)
        self.update_counts()

    def update_counts(self):
        sel_a = len(self.get_checked_items(self.list_a))
        sel_b = len(self.get_checked_items(self.list_b))
        tot_a = self.list_a.count()
        tot_b = self.list_b.count()

        self.lbl_count_a.setText(f"{sel_a} / {tot_a} cochées")
        self.lbl_count_b.setText(f"{sel_b} / {tot_b} cochées")
        self.lbl_total.setText(f"Colonnes retenues : {sel_a} (Tableau A) + {sel_b} (Tableau B) = {sel_a + sel_b} au total")

    def get_checked_items(self, list_widget: QListWidget) -> List[str]:
        result = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.checkState() == Qt.Checked:
                result.append(item.text())
        return result

    def on_apply(self):
        sel_a = self.get_checked_items(self.list_a)
        sel_b = self.get_checked_items(self.list_b)

        if not sel_a and not sel_b:
            QMessageBox.warning(
                self,
                "Aucune colonne sélectionnée",
                "Veuillez sélectionner au moins une colonne dans l'un des tableaux pour afficher les résultats."
            )
            return

        self.accept()

    def get_selected_columns(self) -> Tuple[List[str], List[str]]:
        return self.get_checked_items(self.list_a), self.get_checked_items(self.list_b)
