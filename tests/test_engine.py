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

    def test_profile_manager(self):
        criteria = [{"col_a": "X", "col_b": "Y", "rule_type": "text_exact"}]
        path = save_profile("Profil_Test", criteria, "Test description")
        self.assertTrue(os.path.exists(path))
        
        loaded = load_profile("Profil_Test")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["name"], "Profil_Test")
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
        self.assertEqual(len(res["orphans_b"]), 1)

if __name__ == "__main__":
    unittest.main()
