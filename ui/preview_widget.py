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
from PyQt5.QtGui import QColor, QBrush, QFont
from typing import Dict, Any, List, Optional, Tuple
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
        self.current_view = "matched"  # 'matched', 'orphans_a', 'orphans_b', 'manual'
        self.current_sub_filter = "all"  # 'all', 'exact', 'fuzzy', 'diff', 'grouped', 'manual'
        self.all_cols_a: List[str] = []
        self.all_cols_b: List[str] = []
        self.selected_cols_a: List[str] = []
        self.selected_cols_b: List[str] = []
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
        self.btn_view_matched.setProperty("class", "nav-tab")
        self.btn_view_matched.setCheckable(True)
        self.btn_view_matched.setChecked(True)
        self.btn_view_matched.setCursor(Qt.PointingHandCursor)
        self.btn_view_matched.clicked.connect(lambda: self.switch_view("matched"))
        nav_bar.addWidget(self.btn_view_matched)

        self.btn_view_orphans_a = QPushButton("Suspens Tableau A")
        self.btn_view_orphans_a.setProperty("class", "nav-tab")
        self.btn_view_orphans_a.setCheckable(True)
        self.btn_view_orphans_a.setCursor(Qt.PointingHandCursor)
        self.btn_view_orphans_a.clicked.connect(lambda: self.switch_view("orphans_a"))
        nav_bar.addWidget(self.btn_view_orphans_a)

        self.btn_view_orphans_b = QPushButton("Suspens Tableau B")
        self.btn_view_orphans_b.setProperty("class", "nav-tab")
        self.btn_view_orphans_b.setCheckable(True)
        self.btn_view_orphans_b.setCursor(Qt.PointingHandCursor)
        self.btn_view_orphans_b.clicked.connect(lambda: self.switch_view("orphans_b"))
        nav_bar.addWidget(self.btn_view_orphans_b)

        self.btn_view_manual = QPushButton("⚡ Atelier d'Association Manuelle")
        self.btn_view_manual.setProperty("class", "nav-tab-manual")
        self.btn_view_manual.setCheckable(True)
        self.btn_view_manual.setCursor(Qt.PointingHandCursor)
        self.btn_view_manual.clicked.connect(lambda: self.switch_view("manual"))
        nav_bar.addWidget(self.btn_view_manual)

        nav_bar.addStretch()

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("🔍 Recherche rapide dans la vue...")
        self.edit_search.setClearButtonEnabled(True)
        self.edit_search.setFixedWidth(250)
        self.edit_search.textChanged.connect(self.on_search_changed)
        nav_bar.addWidget(self.edit_search)

        self.btn_select_cols = QPushButton("⚙️ Colonnes...")
        self.btn_select_cols.setCursor(Qt.PointingHandCursor)
        self.btn_select_cols.setToolTip("Choisir les colonnes des deux tableaux à afficher et exporter")
        self.btn_select_cols.clicked.connect(self.on_customize_columns_clicked)
        nav_bar.addWidget(self.btn_select_cols)

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
        sub_tools.setSpacing(6)

        self.btn_f_all = QPushButton("Tous")
        self.btn_f_all.setProperty("class", "filter-pill")
        self.btn_f_all.setCheckable(True)
        self.btn_f_all.setChecked(True)
        self.btn_f_all.setCursor(Qt.PointingHandCursor)
        self.btn_f_all.clicked.connect(lambda: self.apply_sub_filter("all"))
        sub_tools.addWidget(self.btn_f_all)

        self.btn_f_exact = QPushButton("Exacts")
        self.btn_f_exact.setProperty("class", "filter-pill")
        self.btn_f_exact.setCheckable(True)
        self.btn_f_exact.setCursor(Qt.PointingHandCursor)
        self.btn_f_exact.clicked.connect(lambda: self.apply_sub_filter("exact"))
        sub_tools.addWidget(self.btn_f_exact)

        self.btn_f_fuzzy = QPushButton("Fuzzy / Variantes")
        self.btn_f_fuzzy.setProperty("class", "filter-pill")
        self.btn_f_fuzzy.setCheckable(True)
        self.btn_f_fuzzy.setCursor(Qt.PointingHandCursor)
        self.btn_f_fuzzy.clicked.connect(lambda: self.apply_sub_filter("fuzzy"))
        sub_tools.addWidget(self.btn_f_fuzzy)

        self.btn_f_diff = QPushButton("Avec écarts")
        self.btn_f_diff.setProperty("class", "filter-pill")
        self.btn_f_diff.setCheckable(True)
        self.btn_f_diff.setCursor(Qt.PointingHandCursor)
        self.btn_f_diff.clicked.connect(lambda: self.apply_sub_filter("diff"))
        sub_tools.addWidget(self.btn_f_diff)

        self.btn_f_grouped = QPushButton("Groupés N-à-1")
        self.btn_f_grouped.setProperty("class", "filter-pill")
        self.btn_f_grouped.setCheckable(True)
        self.btn_f_grouped.setCursor(Qt.PointingHandCursor)
        self.btn_f_grouped.clicked.connect(lambda: self.apply_sub_filter("grouped"))
        sub_tools.addWidget(self.btn_f_grouped)

        self.btn_f_manual = QPushButton("Manuels")
        self.btn_f_manual.setProperty("class", "filter-pill")
        self.btn_f_manual.setCheckable(True)
        self.btn_f_manual.setCursor(Qt.PointingHandCursor)
        self.btn_f_manual.clicked.connect(lambda: self.apply_sub_filter("manual"))
        sub_tools.addWidget(self.btn_f_manual)

        sub_tools.addStretch()

        self.btn_dissociate = QPushButton("✕ Dissocier la sélection")
        self.btn_dissociate.setProperty("class", "btn-danger")
        self.btn_dissociate.setEnabled(False)
        self.btn_dissociate.setCursor(Qt.PointingHandCursor)
        self.btn_dissociate.setToolTip("Dissocie la paire sélectionnée et renvoie les lignes dans les Suspens A et B.")
        self.btn_dissociate.clicked.connect(self.dissociate_selected)
        sub_tools.addWidget(self.btn_dissociate)

        matched_layout.addLayout(sub_tools)

        self.table_matched = QTableWidget()
        self.table_matched.setAlternatingRowColors(True)
        self.table_matched.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_matched.setSelectionMode(QTableWidget.SingleSelection)
        self.table_matched.verticalHeader().setDefaultSectionSize(30)
        self.table_matched.itemSelectionChanged.connect(self.on_matched_selection_changed)
        matched_layout.addWidget(self.table_matched)
        self.stack.addWidget(self.view_matched_widget)

        # --- VUE 2 : Suspens Tableau A ---
        self.view_orphans_a_widget = QWidget()
        oa_layout = QVBoxLayout(self.view_orphans_a_widget)
        oa_layout.setContentsMargins(0, 0, 0, 0)
        self.table_orphans_a = QTableWidget()
        self.table_orphans_a.setAlternatingRowColors(True)
        self.table_orphans_a.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_orphans_a.verticalHeader().setDefaultSectionSize(30)
        oa_layout.addWidget(self.table_orphans_a)
        self.stack.addWidget(self.view_orphans_a_widget)

        # --- VUE 3 : Suspens Tableau B ---
        self.view_orphans_b_widget = QWidget()
        ob_layout = QVBoxLayout(self.view_orphans_b_widget)
        ob_layout.setContentsMargins(0, 0, 0, 0)
        self.table_orphans_b = QTableWidget()
        self.table_orphans_b.setAlternatingRowColors(True)
        self.table_orphans_b.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_orphans_b.verticalHeader().setDefaultSectionSize(30)
        ob_layout.addWidget(self.table_orphans_b)
        self.stack.addWidget(self.view_orphans_b_widget)

        # --- VUE 4 : Atelier d'Association Manuelle ---
        self.view_manual_widget = QWidget()
        man_layout = QVBoxLayout(self.view_manual_widget)
        man_layout.setContentsMargins(0, 0, 0, 0)
        man_layout.setSpacing(6)

        info_manual = QLabel(
            "💡 <b>Mode Manuel :</b> Sélectionnez 1 ligne dans Suspens A (gauche) et 1 dans Suspens B (droite), puis cliquez sur <b>Associer</b>."
        )
        info_manual.setFixedHeight(28)
        info_manual.setStyleSheet("color: #1e40af; font-size: 12px; font-weight: 500; padding: 2px 10px; background: #eff6ff; border: 1px solid #dbeafe; border-radius: 6px;")
        man_layout.addWidget(info_manual, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Panneau Gauche : Suspens A
        panel_a = QWidget()
        pa_layout = QVBoxLayout(panel_a)
        pa_layout.setContentsMargins(0, 0, 0, 0)
        pa_layout.setSpacing(6)

        header_pa = QHBoxLayout()
        self.lbl_pa_title = QLabel("1. Suspens Tableau A")
        self.lbl_pa_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #b45309;")
        header_pa.addWidget(self.lbl_pa_title)
        header_pa.addStretch()
        pa_layout.addLayout(header_pa)

        self.search_man_a = QLineEdit()
        self.search_man_a.setPlaceholderText("🔍 Filtrer Suspens A (nom, montant...)...")
        self.search_man_a.setClearButtonEnabled(True)
        self.search_man_a.textChanged.connect(self.on_search_man_a_changed)
        pa_layout.addWidget(self.search_man_a)

        self.table_man_a = QTableWidget()
        self.table_man_a.setAlternatingRowColors(True)
        self.table_man_a.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_man_a.setSelectionMode(QTableWidget.SingleSelection)
        self.table_man_a.verticalHeader().setDefaultSectionSize(30)
        self.table_man_a.itemSelectionChanged.connect(self.on_manual_selection_changed)
        pa_layout.addWidget(self.table_man_a)
        splitter.addWidget(panel_a)

        # Panneau Central : Contrôle & Liaison
        panel_center = QWidget()
        panel_center.setFixedWidth(175)
        pc_layout = QVBoxLayout(panel_center)
        pc_layout.setContentsMargins(4, 0, 4, 0)
        pc_layout.setSpacing(10)
        pc_layout.addStretch()

        center_card = QFrame()
        center_card.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 8px;")
        cc_layout = QVBoxLayout(center_card)
        cc_layout.setContentsMargins(8, 10, 8, 10)
        cc_layout.setSpacing(8)
        cc_layout.setAlignment(Qt.AlignCenter)

        lbl_icon_center = QLabel("🔗")
        lbl_icon_center.setAlignment(Qt.AlignCenter)
        lbl_icon_center.setStyleSheet("font-size: 24px; background: transparent; border: none;")
        cc_layout.addWidget(lbl_icon_center)

        self.lbl_man_status = QLabel("Sélectionnez 1 ligne dans A et 1 dans B")
        self.lbl_man_status.setWordWrap(True)
        self.lbl_man_status.setAlignment(Qt.AlignCenter)
        self.lbl_man_status.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 600; background: transparent; border: none;")
        cc_layout.addWidget(self.lbl_man_status)

        self.lbl_man_delta = QLabel("")
        self.lbl_man_delta.setAlignment(Qt.AlignCenter)
        self.lbl_man_delta.setStyleSheet("font-size: 11px; background: transparent; border: none;")
        cc_layout.addWidget(self.lbl_man_delta)

        self.btn_link_manual = QPushButton("⚡ Associer\nces 2 lignes")
        self.btn_link_manual.setProperty("class", "btn-primary")
        self.btn_link_manual.setEnabled(False)
        self.btn_link_manual.setCursor(Qt.PointingHandCursor)
        self.btn_link_manual.setFixedHeight(56)
        self.btn_link_manual.clicked.connect(self.associate_manual_selected)
        cc_layout.addWidget(self.btn_link_manual)

        self.btn_clear_man = QPushButton("Annuler sélection")
        self.btn_clear_man.setCursor(Qt.PointingHandCursor)
        self.btn_clear_man.setStyleSheet("font-size: 11px; color: #94a3b8; background: transparent; border: none; padding: 3px;")
        self.btn_clear_man.clicked.connect(self.clear_manual_selection)
        cc_layout.addWidget(self.btn_clear_man)

        pc_layout.addWidget(center_card)
        pc_layout.addStretch()
        splitter.addWidget(panel_center)

        # Panneau Droit : Suspens B
        panel_b = QWidget()
        pb_layout = QVBoxLayout(panel_b)
        pb_layout.setContentsMargins(0, 0, 0, 0)
        pb_layout.setSpacing(6)

        header_pb = QHBoxLayout()
        self.lbl_pb_title = QLabel("2. Suspens Tableau B")
        self.lbl_pb_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #b91c1c;")
        header_pb.addWidget(self.lbl_pb_title)
        header_pb.addStretch()
        pb_layout.addLayout(header_pb)

        self.search_man_b = QLineEdit()
        self.search_man_b.setPlaceholderText("🔍 Filtrer Suspens B (nom, montant...)...")
        self.search_man_b.setClearButtonEnabled(True)
        self.search_man_b.textChanged.connect(self.on_search_man_b_changed)
        pb_layout.addWidget(self.search_man_b)

        self.table_man_b = QTableWidget()
        self.table_man_b.setAlternatingRowColors(True)
        self.table_man_b.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_man_b.setSelectionMode(QTableWidget.SingleSelection)
        self.table_man_b.verticalHeader().setDefaultSectionSize(30)
        self.table_man_b.itemSelectionChanged.connect(self.on_manual_selection_changed)
        pb_layout.addWidget(self.table_man_b)
        splitter.addWidget(panel_b)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 5)
        man_layout.addWidget(splitter, 1)

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

    def display_results(
        self,
        results: Dict[str, Any],
        selected_cols_a: Optional[List[str]] = None,
        selected_cols_b: Optional[List[str]] = None
    ):
        self.current_results = results

        # Extraire toutes les colonnes disponibles
        matched = results.get("matched", [])
        orphans_a = results.get("orphans_a", [])
        orphans_b = results.get("orphans_b", [])

        if not self.all_cols_a:
            if matched:
                self.all_cols_a = list(matched[0]["row_a"].keys())
            elif orphans_a:
                self.all_cols_a = list(orphans_a[0].keys())
        if not self.all_cols_b:
            if matched:
                self.all_cols_b = list(matched[0]["row_b"].keys())
            elif orphans_b:
                self.all_cols_b = list(orphans_b[0].keys())

        if selected_cols_a is not None:
            self.selected_cols_a = [c for c in selected_cols_a if c in self.all_cols_a]
        elif not self.selected_cols_a:
            self.selected_cols_a = list(self.all_cols_a)

        if selected_cols_b is not None:
            self.selected_cols_b = [c for c in selected_cols_b if c in self.all_cols_b]
        elif not self.selected_cols_b:
            self.selected_cols_b = list(self.all_cols_b)

        self.refresh_kpi_display()
        self.switch_view(self.current_view)

    def set_columns_info(
        self,
        all_a: List[str],
        all_b: List[str],
        sel_a: Optional[List[str]] = None,
        sel_b: Optional[List[str]] = None
    ):
        self.all_cols_a = list(all_a)
        self.all_cols_b = list(all_b)
        self.selected_cols_a = list(sel_a) if sel_a is not None else list(all_a)
        self.selected_cols_b = list(sel_b) if sel_b is not None else list(all_b)

    def get_selected_columns(self) -> Tuple[List[str], List[str]]:
        return list(self.selected_cols_a), list(self.selected_cols_b)

    def on_customize_columns_clicked(self):
        from ui.column_selector_dialog import ColumnSelectorDialog
        dlg = ColumnSelectorDialog(
            self.all_cols_a, self.all_cols_b,
            self.selected_cols_a, self.selected_cols_b,
            parent=self
        )
        if dlg.exec_():
            self.selected_cols_a, self.selected_cols_b = dlg.get_selected_columns()
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
        self.lbl_pa_title.setText(f"1. Suspens Tableau A ({orphans_a_count} lignes)")
        self.lbl_pb_title.setText(f"2. Suspens Tableau B ({orphans_b_count} lignes)")

        # Mettre à jour les compteurs des sous-filtres
        self.update_sub_filter_labels()

        # Synchroniser dans les KPIs stockés
        kpis["matched_count"] = matched_count
        kpis["matched_pct"] = pct
        kpis["orphans_a_count"] = orphans_a_count
        kpis["orphans_b_count"] = orphans_b_count

    def update_sub_filter_labels(self):
        matched = self.current_results.get("matched", [])
        c_all = len(matched)
        c_exact = sum(1 for m in matched if m.get("badge_type") == "exact")
        c_fuzzy = sum(1 for m in matched if m.get("badge_type") == "fuzzy")
        c_diff = sum(1 for m in matched if m.get("badge_type") == "warning")
        c_grouped = sum(1 for m in matched if m.get("badge_type") == "grouped")
        c_manual = sum(1 for m in matched if m.get("badge_type") == "manual")

        self.btn_f_all.setText(f"Tous ({c_all})")
        self.btn_f_exact.setText(f"Exacts ({c_exact})")
        self.btn_f_fuzzy.setText(f"Fuzzy / Variantes ({c_fuzzy})")
        self.btn_f_diff.setText(f"Avec écarts ({c_diff})")
        self.btn_f_grouped.setText(f"Groupés ({c_grouped})")
        self.btn_f_manual.setText(f"Manuels ({c_manual})")

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
            self.render_single_table(self.table_man_a, self.current_results.get("orphans_a", []), "A", self.search_man_a.text())
            self.render_single_table(self.table_man_b, self.current_results.get("orphans_b", []), "B", self.search_man_b.text())
            self.on_manual_selection_changed()

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
        if self.current_view == "matched":
            self.apply_sub_filter(self.current_sub_filter)
        elif self.current_view == "orphans_a":
            self.render_single_table(self.table_orphans_a, self.current_results.get("orphans_a", []), "A")
        elif self.current_view == "orphans_b":
            self.render_single_table(self.table_orphans_b, self.current_results.get("orphans_b", []), "B")

    def on_search_man_a_changed(self, text: str):
        self.render_single_table(self.table_man_a, self.current_results.get("orphans_a", []), "A", search_text=text)
        self.on_manual_selection_changed()

    def on_search_man_b_changed(self, text: str):
        self.render_single_table(self.table_man_b, self.current_results.get("orphans_b", []), "B", search_text=text)
        self.on_manual_selection_changed()

    def on_matched_selection_changed(self):
        has_sel = bool(self.table_matched.selectionModel().selectedRows())
        self.btn_dissociate.setEnabled(has_sel)

    def on_manual_selection_changed(self):
        sel_a = self.table_man_a.selectionModel().selectedRows()
        sel_b = self.table_man_b.selectionModel().selectedRows()

        row_a = None
        row_b = None
        if sel_a:
            item_a = self.table_man_a.item(sel_a[0].row(), 0)
            if item_a:
                row_a = item_a.data(Qt.UserRole)
        if sel_b:
            item_b = self.table_man_b.item(sel_b[0].row(), 0)
            if item_b:
                row_b = item_b.data(Qt.UserRole)

        if row_a and row_b:
            self.btn_link_manual.setEnabled(True)
            self.lbl_man_status.setText("✅ <b>Paire sélectionnée</b>")
            self.lbl_man_status.setStyleSheet("font-size: 11px; color: #15803d; font-weight: 700; background: transparent; border: none;")

            # Calcul en direct de l'écart montant si colonnes identifiées
            kpis = self.current_results.get("kpis", {})
            col_amt_a = kpis.get("amount_col_a")
            col_amt_b = kpis.get("amount_col_b")
            if col_amt_a and col_amt_b and col_amt_a in row_a and col_amt_b in row_b:
                val_a = parse_amount(row_a.get(col_amt_a))
                val_b = parse_amount(row_b.get(col_amt_b))
                delta = val_a - val_b
                col_hex = "#15803d" if abs(delta) < 0.01 else "#b45309"
                self.lbl_man_delta.setText(f"<b style='color:{col_hex};'>Écart: {delta:+.2f} DA</b>")
            else:
                self.lbl_man_delta.setText("<span style='color:#64748b;'>Prêt à rapprocher</span>")
        elif row_a:
            self.btn_link_manual.setEnabled(False)
            self.lbl_man_status.setText("✔ Ligne A choisie<br><span style='color:#b45309;'>En attente de ligne B</span>")
            self.lbl_man_status.setStyleSheet("font-size: 11px; color: #b45309; font-weight: 600; background: transparent; border: none;")
            self.lbl_man_delta.setText("")
        elif row_b:
            self.btn_link_manual.setEnabled(False)
            self.lbl_man_status.setText("✔ Ligne B choisie<br><span style='color:#b45309;'>En attente de ligne A</span>")
            self.lbl_man_status.setStyleSheet("font-size: 11px; color: #b91c1c; font-weight: 600; background: transparent; border: none;")
            self.lbl_man_delta.setText("")
        else:
            self.btn_link_manual.setEnabled(False)
            self.lbl_man_status.setText("Sélectionnez 1 ligne dans A et 1 dans B")
            self.lbl_man_status.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 600; background: transparent; border: none;")
            self.lbl_man_delta.setText("")

    def clear_manual_selection(self):
        self.table_man_a.clearSelection()
        self.table_man_b.clearSelection()
        self.on_manual_selection_changed()

    def render_matched_table(self, items: List[Dict[str, Any]]):
        q = self.edit_search.text().strip().lower()
        if q:
            filtered = []
            for r in items:
                text_all = " ".join(
                    [str(v) for v in r["row_a"].values()] + 
                    [str(v) for v in r["row_b"].values()] + 
                    [r.get("statut", ""), r.get("explication", ""), f"passe {r.get('passe', '')}"]
                ).lower()
                if q in text_all:
                    filtered.append(r)
            items = filtered

        self.table_matched.setUpdatesEnabled(False)
        self.table_matched.setSortingEnabled(False)
        self.table_matched.setRowCount(0)

        if not items:
            self.table_matched.setColumnCount(1)
            self.table_matched.setHorizontalHeaderLabels(["Résultat"])
            self.table_matched.insertRow(0)
            msg = "Aucun dossier correspondant à la recherche." if q else "Aucun dossier correspondant."
            self.table_matched.setItem(0, 0, QTableWidgetItem(msg))
            self.table_matched.setUpdatesEnabled(True)
            self.btn_dissociate.setEnabled(False)
            return

        all_a = list(items[0]["row_a"].keys())
        all_b = list(items[0]["row_b"].keys())
        cols_a = [c for c in self.selected_cols_a if c in all_a] if self.selected_cols_a else all_a
        cols_b = [c for c in self.selected_cols_b if c in all_b] if self.selected_cols_b else all_b

        headers = (
            ["Statut Rapprochement", "Passe", "Score", "Écart Montant", "Justification & Détails"] 
            + [f"[A] {c}" for c in cols_a] 
            + [f"[B] {c}" for c in cols_b]
        )
        self.table_matched.setColumnCount(len(headers))
        self.table_matched.setHorizontalHeaderLabels(headers)

        badge_palette = {
            "exact": "#059669",
            "fuzzy": "#0284c7",
            "warning": "#d97706",
            "grouped": "#7c3aed",
            "manual": "#1e3a8a",
        }

        display_limit = min(len(items), 800)
        self.table_matched.setRowCount(display_limit)
        for r_idx, it in enumerate(items[:display_limit]):
            b_type = it.get("badge_type", "exact")
            color_hex = badge_palette.get(b_type, "#1e293b")
            brush_color = QBrush(QColor(color_hex))

            # Col 0: Statut
            item_statut = QTableWidgetItem(f"● {it.get('statut', '')}")
            item_statut.setData(Qt.UserRole, it)
            item_statut.setForeground(brush_color)
            font_bold = item_statut.font()
            font_bold.setBold(True)
            item_statut.setFont(font_bold)
            self.table_matched.setItem(r_idx, 0, item_statut)

            # Col 1: Passe
            passe_val = it.get('passe', 1)
            item_passe = QTableWidgetItem(f"Passe {passe_val}" if isinstance(passe_val, int) else str(passe_val))
            item_passe.setTextAlignment(Qt.AlignCenter)
            item_passe.setForeground(brush_color)
            self.table_matched.setItem(r_idx, 1, item_passe)

            # Col 2: Score
            item_score = QTableWidgetItem(f"{it.get('score_pct', 0)}%")
            item_score.setTextAlignment(Qt.AlignCenter)
            self.table_matched.setItem(r_idx, 2, item_score)

            # Col 3: Écart Montant
            delta = it.get('delta_amount', 0.0)
            item_delta = QTableWidgetItem(f"{delta:+.2f} DA" if delta != 0.0 else "0.00 DA")
            item_delta.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if abs(delta) >= 0.01:
                item_delta.setForeground(QBrush(QColor("#d97706")))
            else:
                item_delta.setForeground(QBrush(QColor("#059669")))
            self.table_matched.setItem(r_idx, 3, item_delta)

            # Col 4: Justification / Explication
            explication = it.get("explication", "")
            item_exp = QTableWidgetItem(explication)
            item_exp.setToolTip(explication)
            self.table_matched.setItem(r_idx, 4, item_exp)

            curr_c = 5
            for ca in cols_a:
                self.table_matched.setItem(r_idx, curr_c, QTableWidgetItem(str(it["row_a"].get(ca, ""))))
                curr_c += 1
            for cb in cols_b:
                self.table_matched.setItem(r_idx, curr_c, QTableWidgetItem(str(it["row_b"].get(cb, ""))))
                curr_c += 1

        self.table_matched.resizeColumnsToContents()
        for col_idx in range(self.table_matched.columnCount()):
            if self.table_matched.columnWidth(col_idx) < 95:
                self.table_matched.setColumnWidth(col_idx, 95)

        self.table_matched.setSortingEnabled(True)
        self.table_matched.setUpdatesEnabled(True)
        self.btn_dissociate.setEnabled(False)

    def render_single_table(
        self,
        table: QTableWidget,
        rows: List[Dict[str, Any]],
        prefix: str,
        search_text: Optional[str] = None
    ):
        q = (search_text if search_text is not None else self.edit_search.text()).strip().lower()
        if q:
            rows = [r for r in rows if q in " ".join(str(v) for v in r.values()).lower()]

        table.setUpdatesEnabled(False)
        table.setSortingEnabled(False)
        table.setRowCount(0)

        if not rows:
            table.setColumnCount(1)
            table.setHorizontalHeaderLabels(["Information"])
            table.insertRow(0)
            msg = f"Aucun résultat trouvé dans le Tableau {prefix}." if q else f"Aucun suspens dans le Tableau {prefix}."
            table.setItem(0, 0, QTableWidgetItem(msg))
            table.setUpdatesEnabled(True)
            return

        all_cols = list(rows[0].keys())
        selected = self.selected_cols_a if prefix == "A" else self.selected_cols_b
        cols = [c for c in selected if c in all_cols] if selected else all_cols
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels([f"[{prefix}] {c}" for c in cols])

        display_limit = min(len(rows), 800)
        table.setRowCount(display_limit)
        for r_idx, r_data in enumerate(rows[:display_limit]):
            for c_idx, col_name in enumerate(cols):
                it = QTableWidgetItem(str(r_data.get(col_name, "")))
                if c_idx == 0:
                    it.setData(Qt.UserRole, r_data)
                table.setItem(r_idx, c_idx, it)

        table.resizeColumnsToContents()
        for col_idx in range(table.columnCount()):
            if table.columnWidth(col_idx) < 95:
                table.setColumnWidth(col_idx, 95)

        table.setSortingEnabled(True)
        table.setUpdatesEnabled(True)

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
        if col_amt_a and col_amt_b and col_amt_a in row_a and col_amt_b in row_b:
            delta = parse_amount(row_a.get(col_amt_a)) - parse_amount(row_b.get(col_amt_b))

        new_match = {
            "statut": "Rapproché Manuellement",
            "badge_type": "manual",
            "passe": "Manuel",
            "score_pct": 100,
            "delta_amount": round(delta, 2),
            "explication": f"Association manuelle forcée par l'opérateur (Écart: {delta:+.2f} DA)",
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
        self.render_single_table(self.table_man_a, orphans_a, "A", self.search_man_a.text())
        self.render_single_table(self.table_man_b, orphans_b, "B", self.search_man_b.text())
        self.on_manual_selection_changed()
        self.results_updated.emit(self.current_results)

        QMessageBox.information(
            self, "Succès",
            "Les deux lignes ont été associées manuellement avec succès !"
        )
