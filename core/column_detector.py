"""
Détection automatique et heuristiques de suggestion de paires de colonnes.
"""
import re
import unicodedata
from difflib import SequenceMatcher
import pandas as pd
from typing import List, Dict, Any

def clean_str(val: Any) -> str:
    """Supprime accents et minusculise."""
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    return re.sub(r"[^a-z0-9]", "", s)

# Mots-clés de catégorisation sémantique
TAXONOMY = {
    "id": [
        "id", "code", "num", "numero", "nss", "pec", "ref", "reference", 
        "piece", "facture", "bordereau", "matricule", "dossier", "admission",
        "cin", "rib", "compte"
    ],
    "name": [
        "nom", "prenom", "patient", "assure", "tiers", "client", "fournisseur", 
        "beneficiaire", "personne", "libelle", "designation", "intitule", "medecin", "doctor"
    ],
    "amount": [
        "montant", "total", "prix", "dette", "credit", "debit", "solde", 
        "ttc", "ht", "tva", "versement", "reglement", "recu", "attendu", "reste",
        "net", "brut", "honoraires", "part"
    ],
    "date": [
        "date", "jour", "echeance", "periode", "annee", "mois", "creation", 
        "admission", "naissance", "acte"
    ],
}

def detect_column_type(df: pd.DataFrame, col_name: str) -> str:
    """Détecte si une colonne est plutôt 'amount', 'date', 'id' ou 'text'."""
    clean_col = clean_str(col_name)
    
    # 1. Correspondance par nom
    for cat, keywords in TAXONOMY.items():
        for kw in keywords:
            if kw in clean_col:
                return cat
                
    # 2. Analyse des données d'échantillon
    sample = df[col_name].dropna().head(30).astype(str).tolist()
    if not sample:
        return "text"
        
    # Test montant numérique
    numeric_count = 0
    date_count = 0
    for val in sample:
        val_clean = val.replace(" ", "").replace(",", ".").replace("DA", "").replace("€", "").replace("$", "")
        try:
            float(val_clean)
            numeric_count += 1
            continue
        except ValueError:
            pass
        if re.search(r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b", val) or re.search(r"\b\d{4}-\d{2}-\d{2}\b", val):
            date_count += 1
            
    if numeric_count / len(sample) >= 0.7:
        return "amount"
    if date_count / len(sample) >= 0.5:
        return "date"
        
    return "text"

def suggest_column_pairs(df_a: pd.DataFrame, df_b: pd.DataFrame) -> List[Dict[str, Any]]:
    """Propose automatiquement des associations logiques de colonnes entre A et B."""
    suggestions = []
    cols_a = list(df_a.columns)
    cols_b = list(df_b.columns)
    
    types_a = {c: detect_column_type(df_a, c) for c in cols_a}
    types_b = {c: detect_column_type(df_b, c) for c in cols_b}
    
    used_b = set()
    
    # Score de chaque paire possible
    for col_a in cols_a:
        ca_clean = clean_str(col_a)
        type_a = types_a[col_a]
        best_match = None
        best_score = 0.0
        
        for col_b in cols_b:
            if col_b in used_b:
                continue
            cb_clean = clean_str(col_b)
            type_b = types_b[col_b]
            
            # Similarité lexicale directe
            ratio = SequenceMatcher(None, ca_clean, cb_clean).ratio()
            
            # Égalité exacte nettoyée
            if ca_clean == cb_clean:
                ratio = 1.0
            elif type_a != "text" and type_a == type_b:
                # Même catégorie sémantique (ex: tous deux montants ou tous deux noms de tiers)
                ratio = max(ratio, 0.65)
                # Si des sous-mots clés matchent dans la taxonomie
                for kw in TAXONOMY.get(type_a, []):
                    if kw in ca_clean and kw in cb_clean:
                        ratio = max(ratio, 0.85)
            elif type_a == "text" and type_b == "text":
                # Vérifier si un mot commun existe (ex: 'patient' ou 'assure')
                toks_a = set(re.findall(r"[a-z0-9]+", col_a.lower()))
                toks_b = set(re.findall(r"[a-z0-9]+", col_b.lower()))
                if toks_a.intersection(toks_b):
                    ratio = max(ratio, 0.75)
                
            if ratio > best_score:
                best_score = ratio
                best_match = col_b
                
        if best_match and best_score >= 0.60:
            assigned_type = types_a[col_a]
            rule_type = "text_fuzzy"
            tolerance = 85.0
            
            if assigned_type == "amount":
                rule_type = "amount"
                tolerance = 0.05
            elif assigned_type == "date":
                rule_type = "date"
                tolerance = 3
            elif assigned_type == "id":
                rule_type = "text_exact"
                tolerance = 100.0
            elif assigned_type == "name":
                rule_type = "text_fuzzy"
                tolerance = 85.0
                
            suggestions.append({
                "col_a": col_a,
                "col_b": best_match,
                "type_semantic": assigned_type,
                "rule_type": rule_type,
                "tolerance": tolerance,
                "confidence": min(100, int(best_score * 100)),
                "weight": 1.0,
            })
            used_b.add(best_match)
            
    # Trier par confiance décroissante
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)
    return suggestions
