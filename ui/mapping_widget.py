"""
Widget interactif de configuration des critères de rapprochement.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QHeaderView, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt
from typing import List, Dict, Any
import difflib
from core.profile_manager import list_profiles, save_profile, load_profile

RULE_TYPES = {
    "text_exact": "Texte Exact",
    "text_fuzzy": "Texte Tolérant / Orthographe",
    "amount": "Montant Numérique",
    "date": "Date",
}

class MappingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cols_a: List[str] = []
        self.cols_b: List[str] = []
        self.criteria: List[Dict[str, Any]] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Barre supérieure : Titre et Modèles
        top_bar = QHBoxLayout()
        lbl_section = QLabel("Critères & Règles d'Appariement :")
        lbl_section.setStyleSheet("font-weight: bold; font-size: 14px; color: #1e3a8a;")
        top_bar.addWidget(lbl_section)

        top_bar.addStretch()

        self.combo_profiles = QComboBox()
        self.refresh_profiles_list()
        top_bar.addWidget(QLabel("Modèle sauvegardé :"))
        top_bar.addWidget(self.combo_profiles)

        btn_load_profile = QPushButton("Charger")
        btn_load_profile.clicked.connect(self.on_load_profile_clicked)
        top_bar.addWidget(btn_load_profile)

        btn_save_profile = QPushButton("Enregistrer ce modèle...")
        btn_save_profile.clicked.connect(self.on_save_profile_clicked)
        top_bar.addWidget(btn_save_profile)

        layout.addLayout(top_bar)

        # Tableau des critères
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Colonne Tableau A", "Colonne Tableau B", "Type de Règle", 
            "Tolérance", "Poids", "Action"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # Barre inférieure : Ajouter / Réinitialiser
        bottom_bar = QHBoxLayout()
        btn_add = QPushButton("+ Ajouter un critère")
        btn_add.setProperty("class", "btn-primary")
        btn_add.clicked.connect(lambda: self.add_criteria_row())
        bottom_bar.addWidget(btn_add)

        bottom_bar.addStretch()

        layout.addLayout(bottom_bar)

    def set_columns(self, cols_a: List[str], cols_b: List[str]):
        self.cols_a = cols_a
        self.cols_b = cols_b

    def set_criteria(self, criteria_list: List[Dict[str, Any]]):
        self.table.setRowCount(0)
        for crit in criteria_list:
            self.add_criteria_row(crit)

    def add_criteria_row(self, crit: Dict[str, Any] = None):
        crit = crit or {}
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 0. Combo Col A
        combo_a = QComboBox()
        combo_a.addItems(self.cols_a)
        target_a = crit.get("col_a", "")
        if target_a in self.cols_a:
            combo_a.setCurrentText(target_a)
        elif self.cols_a and target_a:
            matches_a = difflib.get_close_matches(str(target_a), self.cols_a, n=1, cutoff=0.35)
            if matches_a:
                combo_a.setCurrentText(matches_a[0])
        self.table.setCellWidget(row, 0, combo_a)

        # 1. Combo Col B
        combo_b = QComboBox()
        combo_b.addItems(self.cols_b)
        target_b = crit.get("col_b", "")
        if target_b in self.cols_b:
            combo_b.setCurrentText(target_b)
        elif self.cols_b and target_b:
            matches_b = difflib.get_close_matches(str(target_b), self.cols_b, n=1, cutoff=0.35)
            if matches_b:
                combo_b.setCurrentText(matches_b[0])
        self.table.setCellWidget(row, 1, combo_b)

        # 2. Combo Rule Type
        combo_rule = QComboBox()
        for k, v in RULE_TYPES.items():
            combo_rule.addItem(v, k)
        rule_key = crit.get("rule_type", "text_fuzzy")
        idx = combo_rule.findData(rule_key)
        if idx >= 0:
            combo_rule.setCurrentIndex(idx)
        self.table.setCellWidget(row, 2, combo_rule)

        # 3. Tolérance
        edit_tol = QLineEdit(str(crit.get("tolerance", "85")))
        edit_tol.setFixedWidth(70)
        self.table.setCellWidget(row, 3, edit_tol)

        # 4. Poids
        edit_weight = QLineEdit(str(crit.get("weight", "1.0")))
        edit_weight.setFixedWidth(50)
        self.table.setCellWidget(row, 4, edit_weight)

        # 5. Bouton Supprimer
        btn_del = QPushButton("✕")
        btn_del.setProperty("class", "btn-danger")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setFixedWidth(32)
        btn_del.clicked.connect(lambda _, b=btn_del: self.remove_criteria_row(b))
        self.table.setCellWidget(row, 5, btn_del)

    def remove_criteria_row(self, button: QPushButton):
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, 5) is button:
                self.table.removeRow(r)
                break

    def get_configured_criteria(self) -> List[Dict[str, Any]]:
        criteria = []
        for row in range(self.table.rowCount()):
            combo_a = self.table.cellWidget(row, 0)
            combo_b = self.table.cellWidget(row, 1)
            combo_rule = self.table.cellWidget(row, 2)
            edit_tol = self.table.cellWidget(row, 3)
            edit_weight = self.table.cellWidget(row, 4)

            if combo_a and combo_b and combo_rule:
                col_a = combo_a.currentText()
                col_b = combo_b.currentText()
                rule_type = combo_rule.currentData()
                try:
                    tol = float(edit_tol.text().replace(",", "."))
                except Exception:
                    tol = 85.0
                try:
                    weight = float(edit_weight.text().replace(",", "."))
                except Exception:
                    weight = 1.0

                criteria.append({
                    "col_a": col_a,
                    "col_b": col_b,
                    "rule_type": rule_type,
                    "tolerance": tol,
                    "weight": weight
                })
        return criteria

    def refresh_profiles_list(self):
        self.combo_profiles.clear()
        profs = list_profiles()
        self.combo_profiles.addItems(profs if profs else ["Aucun modèle"])

    def on_save_profile_clicked(self):
        criteria = self.get_configured_criteria()
        if not criteria:
            QMessageBox.warning(self, "Attention", "Veuillez configurer au moins un critère avant d'enregistrer.")
            return
        name, ok = QInputDialog.getText(self, "Enregistrer le modèle", "Nom du modèle de rapprochement :")
        if ok and name.strip():
            save_profile(name.strip(), criteria)
            self.refresh_profiles_list()
            QMessageBox.information(self, "Succès", f"Modèle '{name}' enregistré avec succès !")

    def on_load_profile_clicked(self):
        name = self.combo_profiles.currentText()
        if not name or name == "Aucun modèle":
            return
        data = load_profile(name)
        if data and "criteria" in data:
            self.set_criteria(data["criteria"])
            QMessageBox.information(self, "Succès", f"Modèle '{name}' appliqué !")
