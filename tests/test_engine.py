"""
Tests unitaires et d'intégration du moteur de réconciliation LogMed RAPP.
"""
import os
import sys
import unittest
import pandas as pd

# Ajout du chemin racine de LogMed_RAPP
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from core.column_detector import detect_column_type, suggest_column_pairs
from core.matching_engine import reconcile_tables, compute_text_similarity
from core.excel_exporter import export_reconciliation_excel
from core.profile_manager import save_profile, load_profile, list_profiles

class TestReconciliationEngine(unittest.TestCase):

    def setUp(self):
        # Création de deux jeux de données de test (Cas concret Comptabilité / Santé)
        self.df_a = pd.DataFrame({
            "N_Dossier": ["101", "102", "103", "104"],
            "Patient": ["BENALI MOHAMED", "KADA AHMED", "DJOUADI LAHCENE", "ORPHELIN A"],
            "Montant": [15000.0, 45000.50, 120000.0, 30000.0],
            "Date_Acte": ["2026-05-10", "2026-05-12", "2026-05-15", "2026-05-20"],
        })
        
        self.df_b = pd.DataFrame({
            "Num_Facture": ["F-101", "F-102", "F-103", "F-999"],
            # Test d'inversion Prénom/Nom et légère faute de frappe
            "Nom_Assure": ["MOHAMED BENALI", "KADA AHMED", "DJOUADI LAHSENE", "ORPHELIN B"],
            # Test d'écart minime de centimes
            "Total_Regle": [15000.0, 45000.50, 119999.50, 80000.0],
            "Date_Reglement": ["2026-05-11", "2026-05-12", "2026-05-16", "2026-05-25"],
        })

    def test_text_similarity(self):
        # Test inversion
        sim_inv = compute_text_similarity("BENALI MOHAMED", "MOHAMED BENALI")
        self.assertGreaterEqual(sim_inv, 0.95)
        
        # Test similarité phonétique / typo
        sim_typo = compute_text_similarity("DJOUADI LAHCENE", "DJOUADI LAHSENE")
        self.assertGreaterEqual(sim_typo, 0.85)

    def test_column_detector(self):
        self.assertEqual(detect_column_type(self.df_a, "Montant"), "amount")
        self.assertEqual(detect_column_type(self.df_a, "Date_Acte"), "date")
        self.assertEqual(detect_column_type(self.df_a, "Patient"), "name")
        
        suggestions = suggest_column_pairs(self.df_a, self.df_b)
        self.assertGreaterEqual(len(suggestions), 2)
        
        col_names_a = [s["col_a"] for s in suggestions]
        self.assertIn("Patient", col_names_a)
        self.assertIn("Montant", col_names_a)

    def test_reconcile_tables(self):
        criteria = [
            {"col_a": "Patient", "col_b": "Nom_Assure", "rule_type": "text_fuzzy", "tolerance": 85.0, "weight": 1.0},
            {"col_a": "Montant", "col_b": "Total_Regle", "rule_type": "amount", "tolerance": 1.0, "weight": 1.0},
        ]
        
        results = reconcile_tables(self.df_a, self.df_b, criteria)
        
        matched = results["matched"]
        orphans_a = results["orphans_a"]
        orphans_b = results["orphans_b"]
        kpis = results["kpis"]
        
        self.assertEqual(len(matched), 3)
        self.assertEqual(len(orphans_a), 1)
        self.assertEqual(len(orphans_b), 1)
        self.assertEqual(kpis["matched_count"], 3)
        self.assertEqual(kpis["matched_pct"], 75.0)

    def test_excel_export(self):
        criteria = [
            {"col_a": "Patient", "col_b": "Nom_Assure", "rule_type": "text_fuzzy", "tolerance": 85.0, "weight": 1.0},
            {"col_a": "Montant", "col_b": "Total_Regle", "rule_type": "amount", "tolerance": 1.0, "weight": 1.0},
        ]
        results = reconcile_tables(self.df_a, self.df_b, criteria)
        
        out_excel = os.path.join(APP_ROOT, "tests", "test_output.xlsx")
        export_reconciliation_excel(out_excel, results, criteria, "Test_A.xlsx", "Test_B.xlsx")
        
        self.assertTrue(os.path.exists(out_excel))
        self.assertGreater(os.path.getsize(out_excel), 5000)
        
        # Nettoyage
        try:
            os.remove(out_excel)
        except Exception:
            pass

    def test_excel_export_custom_columns(self):
        criteria = [
            {"col_a": "Patient", "col_b": "Nom_Assure", "rule_type": "text_fuzzy", "tolerance": 85.0, "weight": 1.0},
            {"col_a": "Montant", "col_b": "Total_Regle", "rule_type": "amount", "tolerance": 1.0, "weight": 1.0},
        ]
        results = reconcile_tables(self.df_a, self.df_b, criteria)
        out_excel = os.path.join(APP_ROOT, "tests", "test_output_custom.xlsx")

        selected_a = ["Patient", "Montant"]
        selected_b = ["Nom_Assure"]
        export_reconciliation_excel(
            out_excel, results, criteria, "Test_A.xlsx", "Test_B.xlsx",
            selected_cols_a=selected_a, selected_cols_b=selected_b
        )
        self.assertTrue(os.path.exists(out_excel))

        import openpyxl
        wb = openpyxl.load_workbook(out_excel)
        ws_mat = wb["Rapprochés"]
        headers = [cell.value for cell in ws_mat[1]]
        self.assertIn("[A] Patient", headers)
        self.assertIn("[A] Montant", headers)
        self.assertNotIn("[A] N_Dossier", headers)
        self.assertNotIn("[A] Date_Acte", headers)
        self.assertIn("[B] Nom_Assure", headers)
        self.assertNotIn("[B] Num_Facture", headers)
        self.assertNotIn("[B] Total_Regle", headers)

        ws_oa = wb["Suspens Tableau A"]
        headers_oa = [cell.value for cell in ws_oa[1]]
        self.assertEqual(headers_oa, ["N°", "Patient", "Montant"])

        wb.close()
        try:
            os.remove(out_excel)
        except Exception:
            pass

    def test_profile_manager(self):
        criteria = [{"col_a": "X", "col_b": "Y", "rule_type": "text_exact"}]
        path = save_profile(
            "Profil_Test", criteria, "Test description",
            selected_cols_a=["Col1", "Col2"],
            selected_cols_b=["ColB"]
        )
        self.assertTrue(os.path.exists(path))
        
        loaded = load_profile("Profil_Test")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["name"], "Profil_Test")
        self.assertEqual(loaded.get("selected_cols_a"), ["Col1", "Col2"])
        self.assertEqual(loaded.get("selected_cols_b"), ["ColB"])
        profiles = list_profiles()
        self.assertIn("Profil_Test", profiles)
        self.assertIn("CNAS vs Facturation", profiles)
        self.assertIn("Banque vs Grand Livre", profiles)
        
        # Nettoyage
        try:
            os.remove(path)
        except Exception:
            pass

    def test_reconcile_grouped(self):
        # Cas 2 factures dans A (10 000 + 15 000) = 1 virement groupé dans B (25 000)
        df_a_grp = pd.DataFrame({
            "Client": ["CLINIQUE DU NORD", "CLINIQUE DU NORD", "AUTRE CLIENT"],
            "Montant": [10000.0, 15000.0, 5000.0]
        })
        df_b_grp = pd.DataFrame({
            "Tiers": ["CLINIQUE DU NORD", "INCONNU"],
            "Reglement": [25000.0, 9999.0]
        })
        criteria = [
            {"col_a": "Client", "col_b": "Tiers", "rule_type": "text_fuzzy", "tolerance": 80.0, "weight": 1.0},
            {"col_a": "Montant", "col_b": "Reglement", "rule_type": "amount", "tolerance": 0.05, "weight": 2.0}
        ]
        res = reconcile_tables(df_a_grp, df_b_grp, criteria)
        grouped_items = [m for m in res["matched"] if m.get("badge_type") == "grouped"]
        self.assertEqual(len(grouped_items), 2) # Les 2 lignes A associées au virement de 25000
        self.assertEqual(len(res["orphans_a"]), 1)
    def test_advanced_text_and_stopwords(self):
        # Test stop words médicaux et sociétaires
        sim_corp = compute_text_similarity("CLINIQUE EL AMEL SARL", "EL AMEL")
        self.assertGreaterEqual(sim_corp, 0.95)

        sim_doc = compute_text_similarity("DR KADA AHMED", "KADA AHMED")
        self.assertGreaterEqual(sim_doc, 0.95)

        sim_hopital = compute_text_similarity("EPH BORDJ MENAIEL", "HOPITAL BORDJ MENAIEL")
        self.assertGreaterEqual(sim_hopital, 0.90)

    def test_global_optimal_matching_vs_greedy(self):
        """Vérifie que l'algorithme global ne laisse pas une ligne imparfaite voler le candidat idéal d'une autre."""
        df_a = pd.DataFrame({
            "Ref": ["A1", "A2"],
            "Nom": ["BENALI MOHAMED", "KADA AHMED"],
            "Montant": [1000.0, 2000.0]
        })
        # B a KADA AHMED (2000) et BENALI (1000)
        df_b = pd.DataFrame({
            "Ref": ["B1", "B2"],
            "Nom": ["KADA AHMED", "BENALI MOHAMED"],
            "Montant": [2000.0, 1000.0]
        })
        criteria = [
            {"col_a": "Nom", "col_b": "Nom", "rule_type": "text_fuzzy", "tolerance": 80.0, "weight": 1.0},
            {"col_a": "Montant", "col_b": "Montant", "rule_type": "amount", "tolerance": 0.0, "weight": 2.0}
        ]
        results = reconcile_tables(df_a, df_b, criteria)
        matched = results["matched"]
        self.assertEqual(len(matched), 2)
        # Vérifier que A1 est bien avec B2 (1000) et A2 avec B1 (2000)
        m_a1 = next(m for m in matched if m["row_a"]["Ref"] == "A1")
        self.assertEqual(m_a1["row_b"]["Ref"], "B2")
        self.assertEqual(m_a1["passe"], 1)

    def test_cascade_multipasses_and_explanations(self):
        """Vérifie l'attribution correcte des passes et la génération des justifications."""
        results = reconcile_tables(self.df_a, self.df_b, [
            {"col_a": "Patient", "col_b": "Nom_Assure", "rule_type": "text_fuzzy", "tolerance": 85.0, "weight": 1.0},
            {"col_a": "Montant", "col_b": "Total_Regle", "rule_type": "amount", "tolerance": 1.0, "weight": 1.0},
        ])
        matched = results["matched"]
        self.assertEqual(len(matched), 3)

        # Passe 1 (Exact : BENALI MOHAMED / KADA AHMED)
        exact_matches = [m for m in matched if m["passe"] == 1]
        self.assertGreaterEqual(len(exact_matches), 2)
        for m in exact_matches:
            self.assertEqual(m["badge_type"], "exact")
            self.assertIn("Montant identique", m["explication"])

        # Passe 3 (Écart montant : DJOUADI LAHCENE avec écart de 0.50 DA)
        diff_matches = [m for m in matched if m["passe"] == 3]
        self.assertEqual(len(diff_matches), 1)
        self.assertEqual(diff_matches[0]["badge_type"], "warning")
        self.assertIn("Écart montant", diff_matches[0]["explication"])
        self.assertIn("Variante orthographe", diff_matches[0]["explication"])

    def test_column_selector_dialog(self):
        """Vérifie le fonctionnement de la boîte de sélection des colonnes."""
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        from ui.column_selector_dialog import ColumnSelectorDialog
        dlg = ColumnSelectorDialog(["A1", "A2"], ["B1", "B2"], ["A1"], ["B2"])
        sel_a, sel_b = dlg.get_selected_columns()
        self.assertEqual(sel_a, ["A1"])
        self.assertEqual(sel_b, ["B2"])

        # Test tout cocher / tout décocher
        dlg.set_all_checked(dlg.list_a, True)
        self.assertEqual(dlg.get_checked_items(dlg.list_a), ["A1", "A2"])
        dlg.set_all_checked(dlg.list_a, False)
        self.assertEqual(dlg.get_checked_items(dlg.list_a), [])

    def test_preview_widget_ui_and_manual_mode(self):
        """Vérifie le bon fonctionnement du PreviewWidget, des onglets et de l'Atelier Manuel."""
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        from ui.preview_widget import PreviewWidget

        results = reconcile_tables(self.df_a, self.df_b, [
            {"col_a": "Patient", "col_b": "Nom_Assure", "rule_type": "text_fuzzy", "tolerance": 85.0, "weight": 1.0},
            {"col_a": "Montant", "col_b": "Total_Regle", "rule_type": "amount", "tolerance": 1.0, "weight": 1.0},
        ])

        pw = PreviewWidget()
        pw.display_results(results)

        # Vérifier que les compteurs sont bien initialisés
        self.assertEqual(pw.card_matched.findChild(type(pw.card_matched), "val") is not None, True)
        self.assertIn("Dossiers Rapprochés (3)", pw.btn_view_matched.text())
        self.assertIn("Suspens Tableau A (1)", pw.btn_view_orphans_a.text())
        self.assertIn("Suspens Tableau B (1)", pw.btn_view_orphans_b.text())

        # Vérifier le switch vers l'Atelier Manuel
        pw.switch_view("manual")
        self.assertEqual(pw.current_view, "manual")
        self.assertEqual(pw.table_man_a.rowCount(), 1)
        self.assertEqual(pw.table_man_b.rowCount(), 1)
        self.assertFalse(pw.btn_link_manual.isEnabled())

        # Test de recherche locale dans le panneau A
        pw.search_man_a.setText("NON_EXISTANT")
        self.assertEqual(pw.table_man_a.rowCount(), 1)
        self.assertIn("Aucun", pw.table_man_a.item(0, 0).text())
        pw.search_man_a.clear()
        self.assertEqual(pw.table_man_a.rowCount(), 1)

if __name__ == "__main__":
    unittest.main()
