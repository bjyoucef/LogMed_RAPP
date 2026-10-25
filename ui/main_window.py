"""
Fenêtre principale orchestrant le workflow en 3 étapes de LogMed RAPP.
"""
import os
import pandas as pd
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFileDialog, QMessageBox,
    QProgressBar, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from ui.drop_zone import DropZoneCard
from ui.mapping_widget import MappingWidget
from ui.preview_widget import PreviewWidget
from core.file_reader import read_full_table
from core.column_detector import suggest_column_pairs
from core.matching_engine import reconcile_tables
from core.excel_exporter import export_reconciliation_excel

class WorkerThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, df_a, df_b, criteria):
        super().__init__()
        self.df_a = df_a
        self.df_b = df_b
        self.criteria = criteria

    def run(self):
        try:
            results = reconcile_tables(self.df_a, self.df_b, self.criteria)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LogMed RAPP — Rapprochement Intelligent de Tableaux")
        self.resize(1180, 780)

        self.df_a: pd.DataFrame = None
        self.df_b: pd.DataFrame = None
        self.file_a_path = ""
        self.file_b_path = ""
        self.sheet_a = ""
        self.sheet_b = ""
        self.results: dict = None

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. Hero Header & Stepper
        hero = QFrame()
        hero.setObjectName("heroCard")
        hero.setProperty("class", "hero-card")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 16, 22, 16)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        lbl_app = QLabel("LogMed RAPP")
        lbl_app.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold; background: transparent;")
        lbl_sub = QLabel("Rapprochement & Réconciliation de Tableaux Excel / CSV")
        lbl_sub.setStyleSheet("color: rgba(255,255,255,0.75); font-size: 12px; background: transparent;")
        title_box.addWidget(lbl_app)
        title_box.addWidget(lbl_sub)
        hero_layout.addLayout(title_box)

        hero_layout.addStretch()

        # Indicateur d'étapes
        self.lbl_step1 = QLabel("1. Fichiers")
        self.lbl_step2 = QLabel("2. Règles")
        self.lbl_step3 = QLabel("3. Résultats & Export")
        for lbl in (self.lbl_step1, self.lbl_step2, self.lbl_step3):
            hero_layout.addWidget(lbl)
        self.update_step_labels(0)

        main_layout.addWidget(hero)

        # 2. Stacked Pages
        self.stack = QStackedWidget()

        # ÉTAPE 1 : Fichiers
        self.page_files = QWidget()
        page1_layout = QVBoxLayout(self.page_files)
        page1_layout.setContentsMargins(0, 10, 0, 0)
        
        cards_layout = QHBoxLayout()
        self.card_a = DropZoneCard("Tableau Source A", "Ex: Grand Livre, Factures, Rapprochement KT")
        self.card_a.file_loaded.connect(self.on_file_a_loaded)
        cards_layout.addWidget(self.card_a)

        self.card_b = DropZoneCard("Tableau Source B", "Ex: Relevé Bancaire, Portail PNC, Encaissements")
        self.card_b.file_loaded.connect(self.on_file_b_loaded)
        cards_layout.addWidget(self.card_b)
        page1_layout.addLayout(cards_layout)

        self.stack.addWidget(self.page_files)

        # ÉTAPE 2 : Règles & Mappage
        self.page_mapping = QWidget()
        page2_layout = QVBoxLayout(self.page_mapping)
        page2_layout.setContentsMargins(0, 10, 0, 0)
        self.mapping_widget = MappingWidget()
        page2_layout.addWidget(self.mapping_widget)
        self.stack.addWidget(self.page_mapping)

        # ÉTAPE 3 : Résultats & Export
        self.page_results = QWidget()
        page3_layout = QVBoxLayout(self.page_results)
        page3_layout.setContentsMargins(0, 10, 0, 0)
        self.preview_widget = PreviewWidget()
        page3_layout.addWidget(self.preview_widget)
        self.stack.addWidget(self.page_results)

        main_layout.addWidget(self.stack, 1)

        # 3. Barre de progression (cachée par défaut)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 4. Footer de Navigation
        footer = QHBoxLayout()
        self.btn_prev = QPushButton("< Précédent")
        self.btn_prev.clicked.connect(self.go_prev)
        self.btn_prev.setVisible(False)
        footer.addWidget(self.btn_prev)

        footer.addStretch()

        self.btn_next = QPushButton("Passer aux règles >")
        self.btn_next.setProperty("class", "btn-primary")
        self.btn_next.clicked.connect(self.go_next)
        footer.addWidget(self.btn_next)

        self.btn_export = QPushButton("Exporter le Classeur Excel (.xlsx)")
        self.btn_export.setProperty("class", "btn-success")
        self.btn_export.setVisible(False)
        self.btn_export.clicked.connect(self.export_excel)
        footer.addWidget(self.btn_export)

        main_layout.addLayout(footer)

    def update_step_labels(self, step_idx: int):
        labels = [self.lbl_step1, self.lbl_step2, self.lbl_step3]
        for i, lbl in enumerate(labels):
            if i == step_idx:
                lbl.setStyleSheet("""
                    background-color: rgba(255, 255, 255, 0.22);
                    color: #ffffff;
                    font-weight: 700;
                    font-size: 13px;
                    padding: 7px 14px;
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 0.35);
                """)
            elif i < step_idx:
                lbl.setStyleSheet("""
                    background-color: rgba(16, 185, 129, 0.25);
                    color: #a7f3d0;
                    font-weight: 600;
                    font-size: 13px;
                    padding: 7px 14px;
                    border-radius: 8px;
                    border: 1px solid rgba(16, 185, 129, 0.4);
                """)
            else:
                lbl.setStyleSheet("""
                    background-color: transparent;
                    color: rgba(255, 255, 255, 0.55);
                    font-weight: 600;
                    font-size: 13px;
                    padding: 7px 14px;
                    border-radius: 8px;
                    border: 1px solid transparent;
                """)

    def on_file_a_loaded(self, path: str, sheet: str):
        self.file_a_path = path
        self.sheet_a = sheet

    def on_file_b_loaded(self, path: str, sheet: str):
        self.file_b_path = path
        self.sheet_b = sheet

    def go_next(self):
        curr = self.stack.currentIndex()
        if curr == 0:
            if not self.file_a_path or not self.file_b_path:
                QMessageBox.warning(self, "Fichiers manquants", "Veuillez charger les deux fichiers avant de continuer.")
                return
            # Charger les DataFrames
            try:
                self.df_a = read_full_table(self.file_a_path, self.sheet_a)
                self.df_b = read_full_table(self.file_b_path, self.sheet_b)
            except Exception as e:
                QMessageBox.critical(self, "Erreur de lecture", f"Impossible de lire les fichiers :\n{str(e)}")
                return

            self.mapping_widget.set_columns(list(self.df_a.columns), list(self.df_b.columns))
            # Suggérer automatiquement
            suggestions = suggest_column_pairs(self.df_a, self.df_b)
            self.mapping_widget.set_criteria(suggestions)

            self.stack.setCurrentIndex(1)
            self.update_step_labels(1)
            self.btn_prev.setVisible(True)
            self.btn_next.setText("Lancer le Rapprochement >")

        elif curr == 1:
            criteria = self.mapping_widget.get_configured_criteria()
            if not criteria:
                QMessageBox.warning(self, "Critères manquants", "Veuillez définir au moins un critère de rapprochement.")
                return

            self.progress_bar.setVisible(True)
            self.btn_next.setEnabled(False)

            self.worker = WorkerThread(self.df_a, self.df_b, criteria)
            self.worker.finished.connect(self.on_reconciliation_finished)
            self.worker.error.connect(self.on_reconciliation_error)
            self.worker.start()

    def go_prev(self):
        curr = self.stack.currentIndex()
        if curr == 1:
            self.stack.setCurrentIndex(0)
            self.update_step_labels(0)
            self.btn_prev.setVisible(False)
            self.btn_next.setText("Passer aux règles >")
        elif curr == 2:
            self.stack.setCurrentIndex(1)
            self.update_step_labels(1)
            self.btn_next.setVisible(True)
            self.btn_export.setVisible(False)
            self.btn_next.setText("Relancer le Rapprochement >")

    def on_reconciliation_finished(self, results: dict):
        self.progress_bar.setVisible(False)
        self.btn_next.setEnabled(True)
        self.results = results
        self.preview_widget.display_results(results)

        self.stack.setCurrentIndex(2)
        self.update_step_labels(2)
        self.btn_next.setVisible(False)
        self.btn_export.setVisible(True)

    def on_reconciliation_error(self, err_msg: str):
        self.progress_bar.setVisible(False)
        self.btn_next.setEnabled(True)
        QMessageBox.critical(self, "Erreur de calcul", f"Une erreur s'est produite :\n{err_msg}")

    def export_excel(self):
        results_to_export = self.preview_widget.get_results() or self.results
        if not results_to_export:
            return
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer le rapport de rapprochement",
            f"Rapprochement_{os.path.splitext(os.path.basename(self.file_a_path))[0]}.xlsx",
            "Classeur Excel (*.xlsx)"
        )
        if out_path:
            try:
                criteria = self.mapping_widget.get_configured_criteria()
                export_reconciliation_excel(
                    out_path,
                    results_to_export,
                    criteria,
                    os.path.basename(self.file_a_path),
                    os.path.basename(self.file_b_path)
                )
                QMessageBox.information(
                    self, "Export Réussi", 
                    f"Le fichier a été généré avec succès !\n\nChemin : {out_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Erreur d'exportation", f"Impossible d'enregistrer l'Excel :\n{str(e)}")
