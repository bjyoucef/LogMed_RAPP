"""
Gestionnaire de profils et modèles de rapprochement récurrents.
"""
import os
import sys
import json
from typing import List, Dict, Any, Optional

if getattr(sys, 'frozen', False):
    PROFILES_DIR = os.path.join(os.path.dirname(sys.executable), "profiles")
else:
    PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles")

DEFAULT_PROFILES = {
    "CNAS vs Facturation": {
        "description": "Rapprochement des bordereaux CNAS/CASNOS avec le système de facturation santé.",
        "criteria": [
            {"col_a": "N_Assure", "col_b": "Num_Secu", "rule_type": "text_exact", "tolerance": 100.0, "weight": 2.0},
            {"col_a": "Patient", "col_b": "Nom_Assure", "rule_type": "text_fuzzy", "tolerance": 85.0, "weight": 1.5},
            {"col_a": "Date_Acte", "col_b": "Date_Prestation", "rule_type": "date", "tolerance": 3.0, "weight": 1.0},
            {"col_a": "Montant", "col_b": "Montant_Rembourse", "rule_type": "amount", "tolerance": 0.05, "weight": 2.0}
        ]
    },
    "Banque vs Grand Livre": {
        "description": "Rapprochement bancaire (Relevé de compte vs Comptabilité générale).",
        "criteria": [
            {"col_a": "Libelle", "col_b": "Description", "rule_type": "text_fuzzy", "tolerance": 80.0, "weight": 1.2},
            {"col_a": "Date_Ecriture", "col_b": "Date_Valeur", "rule_type": "date", "tolerance": 5.0, "weight": 1.5},
            {"col_a": "Montant", "col_b": "Montant", "rule_type": "amount", "tolerance": 0.05, "weight": 2.5, "invert_sign": True}
        ]
    },
    "Factures vs Règlements": {
        "description": "Contrôle des factures émises et des encaissements / règlements reçus.",
        "criteria": [
            {"col_a": "Num_Facture", "col_b": "Reference", "rule_type": "text_fuzzy", "tolerance": 85.0, "weight": 2.0},
            {"col_a": "Client", "col_b": "Tiers", "rule_type": "text_fuzzy", "tolerance": 80.0, "weight": 1.2},
            {"col_a": "Total_TTC", "col_b": "Montant_Paye", "rule_type": "amount", "tolerance": 0.05, "weight": 2.0}
        ]
    }
}

def ensure_profiles_dir():
    os.makedirs(PROFILES_DIR, exist_ok=True)
    for name, data in DEFAULT_PROFILES.items():
        file_path = os.path.join(PROFILES_DIR, f"{name}.json")
        if not os.path.exists(file_path):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({"name": name, "description": data["description"], "criteria": data["criteria"]}, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

def list_profiles() -> List[str]:
    """Retourne la liste des noms de profils disponibles."""
    ensure_profiles_dir()
    files = [f[:-5] for f in os.listdir(PROFILES_DIR) if f.endswith(".json")]
    return sorted(files)

def save_profile(
    name: str,
    criteria: List[Dict[str, Any]],
    description: str = "",
    selected_cols_a: Optional[List[str]] = None,
    selected_cols_b: Optional[List[str]] = None
) -> str:
    """Enregistre un profil de configuration."""
    ensure_profiles_dir()
    clean_name = "".join([c for c in name if c.isalnum() or c in (" ", "_", "-")]).strip()
    file_path = os.path.join(PROFILES_DIR, f"{clean_name}.json")
    payload = {
        "name": clean_name,
        "description": description,
        "criteria": criteria
    }
    if selected_cols_a is not None:
        payload["selected_cols_a"] = selected_cols_a
    if selected_cols_b is not None:
        payload["selected_cols_b"] = selected_cols_b

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return file_path

def load_profile(name: str) -> Optional[Dict[str, Any]]:
    """Charge un profil existant."""
    ensure_profiles_dir()
    file_path = os.path.join(PROFILES_DIR, f"{name}.json")
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

