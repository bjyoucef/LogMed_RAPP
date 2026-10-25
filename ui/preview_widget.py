"""
Widget de prévisualisation interactif avec KPIs, filtres dynamiques,
visualisation complète des Suspens et atelier d'ajustement manuel (associer/dissocier).
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QHeaderView, QFrame,
    QStackedWidget, QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Dict, Any, List
from core.matching_engine import parse_amount

class PreviewWidget(QWidget):
    results_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_results: Dict[str, Any] = {
            "matched": [],
            "orphans_a": [],
            "orphans_b": [],
            "kpis": {}
        }
        self.current_view = "matched" # 'matched', 'orphans_a', 'orphans_b', 'manual'
        self.current_sub_filter = "all" # 'all', 'exact', 'fuzzy', 'diff', 'grouped', 'manual'
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Cartes KPIs
        kpi_bar = QHBoxLayout()
        kpi_bar.setSpacing(10)

        self.card_total_a = self.create_kpi_card("LIGNES (A)", "0", "#1e3a8a")
        self.card_total_b = self.create_kpi_card("LIGNES (B)", "0", "#0284c7")
        self.card_matched = self.create_kpi_card("RAPPROCHÉS", "0 (0%)", "#059669")
        self.card_orphans_a = self.create_kpi_card("SUSPENS (A)", "0", "#d97706")
        self.card_orphans_b = self.create_kpi_card("SUSPENS (B)", "0", "#dc2626")

        kpi_bar.addWidget(self.card_total_a)
        kpi_bar.addWidget(self.card_total_b)
        kpi_bar.addWidget(self.card_matched)
        kpi_bar.addWidget(self.card_orphans_a)
        kpi_bar.addWidget(self.card_orphans_b)
        layout.addLayout(kpi_bar)

        # 2. Barre d'onglets de navigation principale
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(8)

        self.btn_view_matched = QPushButton("Dossiers Rapprochés")
        self.btn_view_matched.setCheckable(True)
        self.btn_view_matched.setChecked(True)
        self.btn_view_matched.clicked.connect(lambda: self.switch_view("matched"))
        nav_bar.addWidget(self.btn_view_matched)

        self.btn_view_orphans_a = QPushButton("Suspens Tableau A")
        self.btn_view_orphans_a.setCheckable(True)
        self.btn_view_orphans_a.clicked.connect(lambda: self.switch_view("orphans_a"))
        nav_bar.addWidget(self.btn_view_orphans_a)

        self.btn_view_orphans_b = QPushButton("Suspens Tableau B")
        self.btn_view_orphans_b.setCheckable(True)
        self.btn_view_orphans_b.clicked.connect(lambda: self.switch_view("orphans_b"))
        nav_bar.addWidget(self.btn_view_orphans_b)

        self.btn_view_manual = QPushButton("⚡ Atelier d'Association Manuelle")
        self.btn_view_manual.setCheckable(True)
        self.btn_view_manual.setStyleSheet("font-weight: 700; color: #1e3a8a;")
        self.btn_view_manual.clicked.connect(lambda: self.switch_view("manual"))
        nav_bar.addWidget(self.btn_view_manual)

        nav_bar.addStretch()

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Recherche rapide dans la vue...")
        self.edit_search.setFixedWidth(240)
        self.edit_search.textChanged.connect(self.on_search_changed)
        nav_bar.addWidget(self.edit_search)

        layout.addLayout(nav_bar)

        # 3. Stacked widget contenant les différentes vues
        self.stack = QStackedWidget()

        # --- VUE 1 : Rapprochés ---
        self.view_matched_widget = QWidget()
        matched_layout = QVBoxLayout(self.view_matched_widget)
        matched_layout.setContentsMargins(0, 0, 0, 0)
        matched_layout.setSpacing(8)

        # Barre d'actions & sous-filtres des rapprochés
        sub_tools = QHBoxLayout()
        self.btn_f_all = QPushButton("Tous")
        self.btn_f_all.setCheckable(True)
        self.btn_f_all.setChecked(True)
        self.btn_f_all.clicked.connect(lambda: self.apply_sub_filter("all"))
        sub_tools.addWidget(self.btn_f_all)

        self.btn_f_exact = QPushButton("Exacts")
        self.btn_f_exact.setCheckable(True)
        self.btn_f_exact.clicked.connect(lambda: self.apply_sub_filter("exact"))
        sub_tools.addWidget(self.btn_f_exact)

        self.btn_f_fuzzy = QPushButton("Fuzzy / Variantes")
        self.btn_f_fuzzy.setCheckable(True)
        self.btn_f_fuzzy.clicked.connect(lambda: self.apply_sub_filter("fuzzy"))
        sub_tools.addWidget(self.btn_f_fuzzy)

        self.btn_f_diff = QPushButton("Avec écarts")
        self.btn_f_diff.setCheckable(True)
        self.btn_f_diff.clicked.connect(lambda: self.apply_sub_filter("diff"))
        sub_tools.addWidget(self.btn_f_diff)

        self.btn_f_grouped = QPushButton("Groupés N-à-1")
        self.btn_f_grouped.setCheckable(True)
        self.btn_f_grouped.clicked.connect(lambda: self.apply_sub_filter("grouped"))
        sub_tools.addWidget(self.btn_f_grouped)

        self.btn_f_manual = QPushButton("Manuels")
        self.btn_f_manual.setCheckable(True)
        self.btn_f_manual.clicked.connect(lambda: self.apply_sub_filter("manual"))
        sub_tools.addWidget(self.btn_f_manual)

        sub_tools.addStretch()

        self.btn_dissociate = QPushButton("✕ Dissocier la ligne sélectionnée")
        self.btn_dissociate.setProperty("class", "btn-danger")
        self.btn_dissociate.setCursor(Qt.PointingHandCursor)
        self.btn_dissociate.setToolTip("Dissocie la paire sélectionnée et renvoie les lignes dans les Suspens A et B.")
        self.btn_dissociate.clicked.connect(self.dissociate_selected)
        sub_tools.addWidget(self.btn_dissociate)

        matched_layout.addLayout(sub_tools)

        self.table_matched = QTableWidget()
        self.table_matched.setAlternatingRowColors(True)
        self.table_matched.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_matched.setSelectionMode(QTableWidget.SingleSelection)
        self.table_matched.setSortingEnabled(True)
        matched_layout.addWidget(self.table_matched)
        self.stack.addWidget(self.view_matched_widget)

        # --- VUE 2 : Suspens Tableau A ---
        self.view_orphans_a_widget = QWidget()
        oa_layout = QVBoxLayout(self.view_orphans_a_widget)
        oa_layout.setContentsMargins(0, 0, 0, 0)
        self.table_orphans_a = QTableWidget()
        self.table_orphans_a.setAlternatingRowColors(True)
        self.table_orphans_a.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_orphans_a.setSortingEnabled(True)
        oa_layout.addWidget(self.table_orphans_a)
        self.stack.addWidget(self.view_orphans_a_widget)

        # --- VUE 3 : Suspens Tableau B ---
        self.view_orphans_b_widget = QWidget()
        ob_layout = QVBoxLayout(self.view_orphans_b_widget)
        ob_layout.setContentsMargins(0, 0, 0, 0)
        self.table_orphans_b = QTableWidget()
        self.table_orphans_b.setAlternatingRowColors(True)
        self.table_orphans_b.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_orphans_b.setSortingEnabled(True)
        ob_layout.addWidget(self.table_orphans_b)
        self.stack.addWidget(self.view_orphans_b_widget)

        # --- VUE 4 : Atelier d'Association Manuelle ---
        self.view_manual_widget = QWidget()
        man_layout = QVBoxLayout(self.view_manual_widget)
        man_layout.setContentsMargins(0, 0, 0, 0)
        man_layout.setSpacing(10)

        info_manual = QLabel(
            "💡 <b>Mode Manuel :</b> Sélectionnez une ligne dans les <b>Suspens A</b> (gauche) et une ligne dans les <b>Suspens B</b> (droite), puis cliquez sur Associer."
        )
        info_manual.setStyleSheet("color: #1e3a8a; padding: 6px 10px; background: #e0f2fe; border-radius: 6px;")
        man_layout.addWidget(info_manual)

        splitter = QSplitter(Qt.Horizontal)

        # Panneau Gauche : Suspens A
        panel_a = QWidget()
        pa_layout = QVBoxLayout(panel_a)
        pa_layout.setContentsMargins(0, 0, 0, 0)
        lbl_pa = QLabel("1. Sélectionner une ligne dans Suspens A :")
        lbl_pa.setStyleSheet("font-weight: bold; color: #d97706;")
        pa_layout.addWidget(lbl_pa)
        self.table_man_a = QTableWidget()
        self.table_man_a.setAlternatingRowColors(True)
        self.table_man_a.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_man_a.setSelectionMode(QTableWidget.SingleSelection)
        self.table_man_a.setSortingEnabled(True)
        pa_layout.addWidget(self.table_man_a)
        splitter.addWidget(panel_a)

        # Panneau Central : Bouton Action
        panel_center = QWidget()
        pc_layout = QVBoxLayout(panel_center)
        pc_layout.setContentsMargins(10, 0, 10, 0)
        pc_layout.addStretch()
        self.btn_link_manual = QPushButton("⚡ Associer\nces 2 lignes")
        self.btn_link_manual.setProperty("class", "btn-primary")
        self.btn_link_manual.setCursor(Qt.PointingHandCursor)
        self.btn_link_manual.setFixedHeight(65)
        self.btn_link_manual.clicked.connect(self.associate_manual_selected)
        pc_layout.addWidget(self.btn_link_manual)
        pc_layout.addStretch()
        splitter.addWidget(panel_center)

        # Panneau Droit : Suspens B
        panel_b = QWidget()
        pb_layout = QVBoxLayout(panel_b)
        pb_layout.setContentsMargins(0, 0, 0, 0)
        lbl_pb = QLabel("2. Sélectionner une ligne dans Suspens B :")
        lbl_pb.setStyleSheet("font-weight: bold; color: #dc2626;")
        pb_layout.addWidget(lbl_pb)
        self.table_man_b = QTableWidget()
        self.table_man_b.setAlternatingRowColors(True)
        self.table_man_b.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_man_b.setSelectionMode(QTableWidget.SingleSelection)
        self.table_man_b.setSortingEnabled(True)
        pb_layout.addWidget(self.table_man_b)
        splitter.addWidget(panel_b)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 4)
        man_layout.addWidget(splitter)

        self.stack.addWidget(self.view_manual_widget)
        layout.addWidget(self.stack, 1)

    def create_kpi_card(self, title: str, val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setObjectName("kpiCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"""
            #kpiCard {{
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-top: 4px solid {color_hex};
                border-radius: 10px;
            }}
        """)
        l = QVBoxLayout(card)
        l.setContentsMargins(14, 12, 14, 12)
        l.setSpacing(4)
        
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; background: transparent;")
        l.addWidget(lbl_t)

        lbl_v = QLabel(val)
        lbl_v.setObjectName("val")
        lbl_v.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {color_hex}; background: transparent;")
        l.addWidget(lbl_v)
        return card

    def display_results(self, results: Dict[str, Any]):
        self.current_results = results
        self.refresh_kpi_display()
        self.switch_view(self.current_view)

    def get_results(self) -> Dict[str, Any]:
        """Retourne les résultats à jour pour l'export Excel."""
        return self.current_results

    def refresh_kpi_display(self):
        kpis = self.current_results.get("kpis", {})
        total_a = kpis.get("total_a", 0)
        total_b = kpis.get("total_b", 0)
        matched_count = len(self.current_results.get("matched", []))
        orphans_a_count = len(self.current_results.get("orphans_a", []))
        orphans_b_count = len(self.current_results.get("orphans_b", []))

        pct = round((matched_count / total_a * 100) if total_a > 0 else 0.0, 1)

        self.card_total_a.findChild(QLabel, "val").setText(str(total_a))
        self.card_total_b.findChild(QLabel, "val").setText(str(total_b))
        self.card_matched.findChild(QLabel, "val").setText(f"{matched_count} ({pct}%)")
        self.card_orphans_a.findChild(QLabel, "val").setText(str(orphans_a_count))
        self.card_orphans_b.findChild(QLabel, "val").setText(str(orphans_b_count))

        # Mettre à jour les labels d'onglets avec les totaux
        self.btn_view_matched.setText(f"Dossiers Rapprochés ({matched_count})")
        self.btn_view_orphans_a.setText(f"Suspens Tableau A ({orphans_a_count})")
        self.btn_view_orphans_b.setText(f"Suspens Tableau B ({orphans_b_count})")

        # Synchroniser dans les KPIs stockés
        kpis["matched_count"] = matched_count
        kpis["matched_pct"] = pct
        kpis["orphans_a_count"] = orphans_a_count
        kpis["orphans_b_count"] = orphans_b_count

    def switch_view(self, view_id: str):
        self.current_view = view_id
        self.btn_view_matched.setChecked(view_id == "matched")
        self.btn_view_orphans_a.setChecked(view_id == "orphans_a")
        self.btn_view_orphans_b.setChecked(view_id == "orphans_b")
        self.btn_view_manual.setChecked(view_id == "manual")

        if view_id == "matched":
            self.stack.setCurrentIndex(0)
            self.apply_sub_filter(self.current_sub_filter)
        elif view_id == "orphans_a":
            self.stack.setCurrentIndex(1)
            self.render_single_table(self.table_orphans_a, self.current_results.get("orphans_a", []), "A")
        elif view_id == "orphans_b":
            self.stack.setCurrentIndex(2)
            self.render_single_table(self.table_orphans_b, self.current_results.get("orphans_b", []), "B")
        elif view_id == "manual":
            self.stack.setCurrentIndex(3)
            self.render_single_table(self.table_man_a, self.current_results.get("orphans_a", []), "A")
            self.render_single_table(self.table_man_b, self.current_results.get("orphans_b", []), "B")

    def apply_sub_filter(self, filter_type: str):
        self.current_sub_filter = filter_type
        self.btn_f_all.setChecked(filter_type == "all")
        self.btn_f_exact.setChecked(filter_type == "exact")
        self.btn_f_fuzzy.setChecked(filter_type == "fuzzy")
        self.btn_f_diff.setChecked(filter_type == "diff")
        self.btn_f_grouped.setChecked(filter_type == "grouped")
        self.btn_f_manual.setChecked(filter_type == "manual")

        matched = self.current_results.get("matched", [])
        if filter_type == "exact":
            rows = [m for m in matched if m.get("badge_type") == "exact"]
        elif filter_type == "fuzzy":
            rows = [m for m in matched if m.get("badge_type") == "fuzzy"]
        elif filter_type == "diff":
            rows = [m for m in matched if m.get("badge_type") == "warning"]
        elif filter_type == "grouped":
            rows = [m for m in matched if m.get("badge_type") == "grouped"]
        elif filter_type == "manual":
            rows = [m for m in matched if m.get("badge_type") == "manual"]
        else:
            rows = matched

        self.render_matched_table(rows)

    def on_search_changed(self, text: str):
        # Rafraîchir la vue active avec le filtre de recherche
        if self.current_view == "matched":
            self.apply_sub_filter(self.current_sub_filter)
        elif self.current_view == "orphans_a":
            self.render_single_table(self.table_orphans_a, self.current_results.get("orphans_a", []), "A")
        elif self.current_view == "orphans_b":
            self.render_single_table(self.table_orphans_b, self.current_results.get("orphans_b", []), "B")
        elif self.current_view == "manual":
            self.render_single_table(self.table_man_a, self.current_results.get("orphans_a", []), "A")
            self.render_single_table(self.table_man_b, self.current_results.get("orphans_b", []), "B")

    def render_matched_table(self, items: List[Dict[str, Any]]):
        q = self.edit_search.text().strip().lower()
        if q:
            filtered = []
            for r in items:
                text_all = " ".join([str(v) for v in r["row_a"].values()] + [str(v) for v in r["row_b"].values()] + [r.get("statut", "")]).lower()
                if q in text_all:
                    filtered.append(r)
            items = filtered

        self.table_matched.setRowCount(0)
        if not items:
            self.table_matched.setColumnCount(1)
            self.table_matched.setHorizontalHeaderLabels(["Résultat"])
            self.table_matched.insertRow(0)
            self.table_matched.setItem(0, 0, QTableWidgetItem("Aucun dossier correspondant."))
            return

        cols_a = list(items[0]["row_a"].keys())[:4]
        cols_b = list(items[0]["row_b"].keys())[:4]

        headers = ["Statut Rapprochement", "Score", "Écart Montant"] + [f"[A] {c}" for c in cols_a] + [f"[B] {c}" for c in cols_b]
        self.table_matched.setColumnCount(len(headers))
        self.table_matched.setHorizontalHeaderLabels(headers)

        display_limit = min(len(items), 300)
        self.table_matched.setRowCount(display_limit)
        for r_idx, it in enumerate(items[:display_limit]):
            item_statut = QTableWidgetItem(it.get("statut", ""))
            # Stocker la référence à l'objet dans le premier item
            item_statut.setData(Qt.UserRole, it)
            self.table_matched.setItem(r_idx, 0, item_statut)

            self.table_matched.setItem(r_idx, 1, QTableWidgetItem(f"{it.get('score_pct', 0)}%"))
            self.table_matched.setItem(r_idx, 2, QTableWidgetItem(f"{it.get('delta_amount', 0.0):+.2f}"))

            curr_c = 3
            for ca in cols_a:
                self.table_matched.setItem(r_idx, curr_c, QTableWidgetItem(str(it["row_a"].get(ca, ""))))
                curr_c += 1
            for cb in cols_b:
                self.table_matched.setItem(r_idx, curr_c, QTableWidgetItem(str(it["row_b"].get(cb, ""))))
                curr_c += 1

        self.table_matched.resizeColumnsToContents()

    def render_single_table(self, table: QTableWidget, rows: List[Dict[str, Any]], prefix: str):
        q = self.edit_search.text().strip().lower()
        if q:
            rows = [r for r in rows if q in " ".join(str(v) for v in r.values()).lower()]

        table.setRowCount(0)
        if not rows:
            table.setColumnCount(1)
            table.setHorizontalHeaderLabels(["Information"])
            table.insertRow(0)
            table.setItem(0, 0, QTableWidgetItem(f"Aucun suspens dans le Tableau {prefix}."))
            return

        cols = list(rows[0].keys())
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels([f"[{prefix}] {c}" for c in cols])

        display_limit = min(len(rows), 300)
        table.setRowCount(display_limit)
        for r_idx, r_data in enumerate(rows[:display_limit]):
            for c_idx, col_name in enumerate(cols):
                it = QTableWidgetItem(str(r_data.get(col_name, "")))
                if c_idx == 0:
                    it.setData(Qt.UserRole, r_data)
                table.setItem(r_idx, c_idx, it)

        table.resizeColumnsToContents()

    def dissociate_selected(self):
        """Dissocie la paire sélectionnée dans les rapprochés et la renvoie dans les suspens."""
        selected_rows = self.table_matched.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Sélection requise", "Veuillez sélectionner une ligne rapprochée à dissocier.")
            return

        row_idx = selected_rows[0].row()
        item = self.table_matched.item(row_idx, 0)
        if not item:
            return
        matched_obj = item.data(Qt.UserRole)
        if not matched_obj:
            return

        confirm = QMessageBox.question(
            self,
            "Confirmer la dissociation",
            "Voulez-vous vraiment séparer cette paire ?\nLes deux lignes redeviendront des Suspens dans leurs tableaux respectifs.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        # Retirer de matched
        matched_list = self.current_results.get("matched", [])
        if matched_obj in matched_list:
            matched_list.remove(matched_obj)

        # Ajouter aux orphelins
        self.current_results.setdefault("orphans_a", []).append(matched_obj["row_a"])
        self.current_results.setdefault("orphans_b", []).append(matched_obj["row_b"])

        self.refresh_kpi_display()
        self.apply_sub_filter(self.current_sub_filter)
        self.results_updated.emit(self.current_results)
        QMessageBox.information(self, "Dissocié", "La ligne a été dissociée et replacée dans les Suspens A et B.")

    def associate_manual_selected(self):
        """Associe manuellement une ligne de Suspens A et une de Suspens B."""
        sel_a = self.table_man_a.selectionModel().selectedRows()
        sel_b = self.table_man_b.selectionModel().selectedRows()

        if not sel_a or not sel_b:
            QMessageBox.warning(
                self, "Sélection incomplète",
                "Veuillez sélectionner exactement 1 ligne dans Suspens A (gauche) ET 1 ligne dans Suspens B (droite)."
            )
            return

        item_a = self.table_man_a.item(sel_a[0].row(), 0)
        item_b = self.table_man_b.item(sel_b[0].row(), 0)
        if not item_a or not item_b:
            return

        row_a = item_a.data(Qt.UserRole)
        row_b = item_b.data(Qt.UserRole)
        if not row_a or not row_b:
            return

        # Calcul de l'écart montant si possible
        kpis = self.current_results.get("kpis", {})
        col_amt_a = kpis.get("amount_col_a")
        col_amt_b = kpis.get("amount_col_b")
        delta = 0.0
        if col_amt_a and col_amt_b:
            delta = parse_amount(row_a.get(col_amt_a)) - parse_amount(row_b.get(col_amt_b))

        new_match = {
            "statut": "Rapproché Manuellement",
            "badge_type": "manual",
            "score_pct": 100,
            "delta_amount": round(delta, 2),
            "row_a": row_a,
            "row_b": row_b,
        }

        # Ajouter aux rapprochés
        self.current_results.setdefault("matched", []).insert(0, new_match)

        # Retirer des suspens
        orphans_a = self.current_results.get("orphans_a", [])
        orphans_b = self.current_results.get("orphans_b", [])
        if row_a in orphans_a:
            orphans_a.remove(row_a)
        if row_b in orphans_b:
            orphans_b.remove(row_b)

        self.refresh_kpi_display()
        self.render_single_table(self.table_man_a, orphans_a, "A")
        self.render_single_table(self.table_man_b, orphans_b, "B")
        self.results_updated.emit(self.current_results)

        QMessageBox.information(
            self, "Succès",
            "Les deux lignes ont été associées manuellement avec succès !"
        )
