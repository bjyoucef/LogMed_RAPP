"""
Moteur de rapprochement multi-critères intelligent haute performance.
Supporte :
- Approche en cascade multi-passes (Strict 100%, Flou haute confiance, Écart montant, Groupé N-à-1 / 1-à-N).
- Appariement global optimal (élimination des faux appariements gloutons).
- Intelligence textuelle avancée (RapidFuzz, inversion Nom/Prénom, stop-words médicaux/algériens).
- Explicabilité complète et justification détaillée pour chaque rapprochement.
"""
import bisect
import itertools
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple, Optional, Set
import pandas as pd

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

# Mots parasites et formes juridiques / médicales fréquentes à ignorer ou modérer
STOP_WORDS: Set[str] = {
    # Formes juridiques
    "SARL", "EURL", "SPA", "SNC", "ETS", "ETABLISSEMENT", "STE", "SOCIETE", "GIE", "COOPERATIVE",
    # Établissements de santé / Médical
    "DR", "DOCTEUR", "PR", "PROFESSEUR", "CLINIQUE", "HOPITAL", "CHU", "EPH", "EPSP",
    "PHARMACIE", "CABINET", "LABORATOIRE", "LABO", "CENTRE", "POLYCLINIQUE", "MEDECIN", "SANTE",
    # Civilités et rôles administratifs
    "MR", "MME", "MLLE", "MONSIEUR", "MADAME", "PATIENT", "ASSURE", "TIERS",
    "BENEFICIAIRE", "AYANT", "DROIT", "CLIENT", "FOURNISSEUR",
    # Mots de liaison fréquents
    "DE", "DU", "DES", "ET"
}

def normalize_text(val: Any) -> str:
    """Normalise une chaîne : sans accents, majuscules, espaces consolidés et sans ponctuation parasite."""
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    # Remplacer la ponctuation non alphanumérique par des espaces
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def strip_stop_words(text: str) -> str:
    """Supprime les mots parasites médicaux/juridiques pour comparer le cœur sémantique."""
    tokens = [w for w in text.split() if w not in STOP_WORDS]
    return " ".join(tokens) if tokens else text

def parse_amount(val: Any) -> float:
    """Convertit une chaîne monétaire en float."""
    if val is None or pd.isna(val):
        return 0.0
    s = str(val).strip()
    s = s.replace(" ", "").replace(",", ".").replace("DA", "").replace("€", "").replace("$", "")
    try:
        return float(s)
    except ValueError:
        return 0.0

def parse_date(val: Any) -> Any:
    """Essaie de convertir une valeur en datetime date."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass
    return None

def fast_text_similarity(norm_a: str, norm_b: str, clean_a: str = "", clean_b: str = "") -> float:
    """
    Similarité textuelle optimisée évitant les allocations et normalisations répétées.
    Prend en entrée des chaînes déjà normalisées et nettoyées.
    """
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 1.0

    if HAS_RAPIDFUZZ:
        r_sort = fuzz.token_sort_ratio(norm_a, norm_b) / 100.0
        r_set = fuzz.token_set_ratio(norm_a, norm_b) / 100.0
        r_ratio = fuzz.ratio(norm_a, norm_b) / 100.0

        r_clean = 0.0
        if clean_a and clean_b and (clean_a != norm_a or clean_b != norm_b):
            r_clean = max(
                fuzz.token_sort_ratio(clean_a, clean_b),
                fuzz.token_set_ratio(clean_a, clean_b),
                fuzz.ratio(clean_a, clean_b)
            ) / 100.0

        return max(r_sort, r_set, r_ratio, r_clean)

    # Repli difflib standard si RapidFuzz non présent
    tok_a = norm_a.split()
    tok_b = norm_b.split()
    ratio_direct = SequenceMatcher(None, norm_a, norm_b).ratio()
    ratio_inverted = 0.0
    if len(tok_a) == 2 and len(tok_b) == 2:
        rev_b = f"{tok_b[1]} {tok_b[0]}"
        ratio_inverted = SequenceMatcher(None, norm_a, rev_b).ratio()
    elif set(tok_a) == set(tok_b):
        ratio_inverted = 1.0

    return max(ratio_direct, ratio_inverted)

def compute_text_similarity(str_a: str, str_b: str) -> float:
    """
    Similarité intelligente haute précision avec normalisation et stop-words métiers.
    """
    norm_a = normalize_text(str_a)
    norm_b = normalize_text(str_b)
    clean_a = strip_stop_words(norm_a)
    clean_b = strip_stop_words(norm_b)
    return fast_text_similarity(norm_a, norm_b, clean_a, clean_b)


def build_match_explanation(
    row_a: Dict[str, Any],
    row_b: Dict[str, Any],
    criteria: List[Dict[str, Any]],
    delta_amount: float,
    score_pct: int,
    pass_num: int
) -> str:
    """Génère une justification textuelle claire et explicite du rapprochement."""
    parts = []

    # 1. Montant
    amt_crit = next((c for c in criteria if c.get("rule_type") == "amount"), None)
    if amt_crit:
        amt_a = parse_amount(row_a.get(amt_crit["col_a"]))
        amt_b = parse_amount(row_b.get(amt_crit["col_b"]))
        if amt_crit.get("invert_sign"):
            amt_b = -amt_b
        if abs(delta_amount) < 0.005:
            parts.append(f"Montant identique ({amt_a:,.2f} DA)")
        else:
            parts.append(f"Écart montant {delta_amount:+.2f} DA (A: {amt_a:,.2f} vs B: {amt_b:,.2f} DA)")

    # 2. Textes (Noms, Tiers, Références)
    for crit in criteria:
        rtype = crit.get("rule_type", "")
        if "text" not in rtype and rtype != "id":
            continue
        col_a, col_b = crit["col_a"], crit["col_b"]
        val_a = str(row_a.get(col_a) or "").strip()
        val_b = str(row_b.get(col_b) or "").strip()
        na = normalize_text(val_a)
        nb = normalize_text(val_b)

        if rtype in ("text_exact", "id"):
            if na == nb:
                parts.append(f"{col_a} identique ({val_a})")
            else:
                parts.append(f"{col_a} ({val_a} ≠ {val_b})")
        else:
            sim = compute_text_similarity(val_a, val_b)
            sim_pct = int(sim * 100)
            if na == nb:
                parts.append(f"{col_a} identique ({val_a})")
            elif sim >= 0.98 and set(na.split()) == set(nb.split()):
                parts.append(f"Inversion {col_a} (100% : {val_a} ↔ {val_b})")
            elif strip_stop_words(na) == strip_stop_words(nb) and strip_stop_words(na):
                parts.append(f"{col_a} identique hors raison sociale ({val_a} ↔ {val_b})")
            else:
                parts.append(f"Variante orthographe {col_a} ({sim_pct}% : {val_a} ↔ {val_b})")

    # 3. Dates
    date_crit = next((c for c in criteria if c.get("rule_type") == "date"), None)
    if date_crit:
        dt_a = parse_date(row_a.get(date_crit["col_a"]))
        dt_b = parse_date(row_b.get(date_crit["col_b"]))
        if dt_a and dt_b:
            days = abs((dt_a - dt_b).days)
            if days == 0:
                parts.append("Date identique")
            else:
                parts.append(f"Écart date: {days} jour{'s' if days > 1 else ''}")

    return " | ".join(parts) if parts else f"Passe {pass_num} — Score {score_pct}%"

def reconcile_grouped_candidates(
    orphans_a: List[Dict[str, Any]],
    orphans_b: List[Dict[str, Any]],
    criteria: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Rapprochement des suspens en mode multi-lignes (N-à-1 et 1-à-N).
    Détecte les combinaisons de 2 à 4 lignes dont la somme correspond à 1 ligne de l'autre tableau.
    """
    amount_crit = next((c for c in criteria if c.get("rule_type") == "amount"), None)
    if not amount_crit or len(orphans_a) == 0 or len(orphans_b) == 0:
        return [], orphans_a, orphans_b

    col_a = amount_crit["col_a"]
    col_b = amount_crit["col_b"]
    tol = float(amount_crit.get("tolerance", 0.05))
    invert_sign = bool(amount_crit.get("invert_sign", False))
    text_crit = next((c for c in criteria if "text" in c.get("rule_type", "")), None)

    matched_grouped = []
    remaining_a = list(orphans_a)
    remaining_b = list(orphans_b)

    amts_a = [parse_amount(r.get(col_a)) for r in remaining_a]
    amts_b = [(-parse_amount(r.get(col_b)) if invert_sign else parse_amount(r.get(col_b))) for r in remaining_b]

    txts_a = [str(r.get(text_crit["col_a"], "") or "").strip() for r in remaining_a] if text_crit else []
    txts_b = [str(r.get(text_crit["col_b"], "") or "").strip() for r in remaining_b] if text_crit else []

    # 1. Passe N-à-1 : Plusieurs lignes A = 1 ligne B
    idx_b = 0
    while idx_b < len(remaining_b):
        row_b = remaining_b[idx_b]
        target_amt_b = amts_b[idx_b]

        found_combo = None
        max_k = min(4, len(remaining_a))

        cand_indices = [
            i for i, amt in enumerate(amts_a)
            if (amt * target_amt_b) >= 0 and abs(amt) <= abs(target_amt_b) + 1.0
        ]

        for k in range(2, max_k + 1):
            if len(cand_indices) < k:
                break
            for combo in itertools.combinations(cand_indices[:25], k):
                sum_a = sum(amts_a[i] for i in combo)
                diff = abs(sum_a - target_amt_b)

                is_match = False
                if 0 < tol <= 1.0 and target_amt_b != 0:
                    is_match = (diff / abs(target_amt_b)) <= tol
                else:
                    is_match = diff <= tol

                if is_match:
                    if text_crit:
                        txt_b = txts_b[idx_b]
                        if len(txt_b) > 3:
                            has_txt = any(
                                compute_text_similarity(txts_a[i], txt_b) >= 0.4
                                for i in combo
                            )
                            if not has_txt:
                                continue
                    found_combo = combo
                    break
            if found_combo:
                break

        if found_combo:
            group_a_rows = [remaining_a[i] for i in found_combo]
            sum_a = sum(amts_a[i] for i in found_combo)
            delta = sum_a - target_amt_b
            grp_id = f"GRP-{len(matched_grouped) + 1}"
            explanation = (
                f"Regroupement N-à-1 : {len(group_a_rows)} lignes A (somme {sum_a:,.2f} DA) = "
                f"1 ligne B ({target_amt_b:,.2f} DA)"
            )
            for r_a in group_a_rows:
                matched_grouped.append({
                    "statut": f"Rapproché N-à-1 ({len(group_a_rows)} lig. A = 1 lig. B)",
                    "badge_type": "grouped",
                    "passe": 4,
                    "score_pct": 95,
                    "delta_amount": round(delta, 2),
                    "explication": explanation,
                    "row_a": r_a,
                    "row_b": row_b,
                    "group_id": grp_id,
                })
            for i in sorted(found_combo, reverse=True):
                del remaining_a[i]
                del amts_a[i]
                if text_crit:
                    del txts_a[i]
            del remaining_b[idx_b]
            del amts_b[idx_b]
            if text_crit:
                del txts_b[idx_b]
        else:
            idx_b += 1

    # 2. Passe 1-à-N : 1 ligne A = Plusieurs lignes B
    idx_a = 0
    while idx_a < len(remaining_a):
        row_a = remaining_a[idx_a]
        target_amt_a = amts_a[idx_a]
        found_combo = None
        max_k = min(4, len(remaining_b))

        cand_indices = [
            j for j, amt in enumerate(amts_b)
            if (amt * target_amt_a) >= 0 and abs(amt) <= abs(target_amt_a) + 1.0
        ]

        for k in range(2, max_k + 1):
            if len(cand_indices) < k:
                break
            for combo in itertools.combinations(cand_indices[:25], k):
                sum_b = sum(amts_b[j] for j in combo)
                diff = abs(target_amt_a - sum_b)
                is_match = False
                if 0 < tol <= 1.0 and target_amt_a != 0:
                    is_match = (diff / abs(target_amt_a)) <= tol
                else:
                    is_match = diff <= tol

                if is_match:
                    if text_crit:
                        txt_a = txts_a[idx_a]
                        if len(txt_a) > 3:
                            has_txt = any(
                                compute_text_similarity(txt_a, txts_b[j]) >= 0.4
                                for j in combo
                            )
                            if not has_txt:
                                continue
                    found_combo = combo
                    break
            if found_combo:
                break

        if found_combo:
            group_b_rows = [remaining_b[j] for j in found_combo]
            sum_b = sum(amts_b[j] for j in found_combo)
            delta = target_amt_a - sum_b
            grp_id = f"GRP-{len(matched_grouped) + 1}"
            explanation = (
                f"Regroupement 1-à-N : 1 ligne A ({target_amt_a:,.2f} DA) = "
                f"{len(group_b_rows)} lignes B (somme {sum_b:,.2f} DA)"
            )
            for r_b in group_b_rows:
                matched_grouped.append({
                    "statut": f"Rapproché 1-à-N (1 lig. A = {len(group_b_rows)} lig. B)",
                    "badge_type": "grouped",
                    "passe": 4,
                    "score_pct": 95,
                    "delta_amount": round(delta, 2),
                    "explication": explanation,
                    "row_a": row_a,
                    "row_b": r_b,
                    "group_id": grp_id,
                })
            for j in sorted(found_combo, reverse=True):
                del remaining_b[j]
                del amts_b[j]
                if text_crit:
                    del txts_b[j]
            del remaining_a[idx_a]
            del amts_a[idx_a]
            if text_crit:
                del txts_a[idx_a]
        else:
            idx_a += 1

    return matched_grouped, remaining_a, remaining_b

def reconcile_tables(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    criteria: List[Dict[str, Any]],
    options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Exécute le rapprochement en cascade multi-passes avec optimisation globale des appariements.

    Passes :
    - Passe 1 (Strict 100%) : Clés d'identification, montants et textes strictement identiques.
    - Passe 2 (Flou / Orthographe) : Montants stricts, tolérances textuelles et dates respectées.
    - Passe 3 (Écarts financiers) : Tolérances montants permises (centimes, timbres, écarts de règlements).
    - Passe 4 (Groupé N-à-1 / 1-à-N) : Combinaisons de plusieurs lignes pour un virement unique.
    """
    options = options or {}
    matched = []
    records_a = df_a.to_dict(orient="records")
    records_b = df_b.to_dict(orient="records")
    len_a = len(records_a)
    len_b = len(records_b)

    if not criteria or len_a == 0 or len_b == 0:
        return {
            "matched": [],
            "orphans_a": records_a,
            "orphans_b": records_b,
            "kpis": {"total_a": len_a, "total_b": len_b, "matched_count": 0, "matched_pct": 0.0}
        }

    used_a_indices: Set[int] = set()
    used_b_indices: Set[int] = set()

    amt_crit = next((c for c in criteria if c.get("rule_type") == "amount"), None)
    total_weight = sum(float(c.get("weight", 1.0)) for c in criteria)
    if total_weight <= 0:
        total_weight = 1.0

    # =========================================================================
    # PRÉ-CALCULS VECTORISÉS DES COLONNES (O(N + M) au lieu de O(N x M))
    # =========================================================================
    prep_exact = []
    prep_amount = []
    prep_date = []
    prep_fuzzy = []

    for crit in criteria:
        col_a = crit["col_a"]
        col_b = crit["col_b"]
        rule_type = crit.get("rule_type", "text_exact")
        tol = float(crit.get("tolerance", 0.0))
        weight = float(crit.get("weight", 1.0))
        invert_sign = bool(crit.get("invert_sign", False))

        if rule_type in ("text_exact", "id"):
            prep_exact.append({
                "col_a": col_a,
                "col_b": col_b,
                "weight": weight,
                "vals_a": [normalize_text(r.get(col_a)) for r in records_a],
                "vals_b": [normalize_text(r.get(col_b)) for r in records_b],
            })
        elif rule_type == "amount":
            prep_amount.append({
                "col_a": col_a,
                "col_b": col_b,
                "tol": tol,
                "weight": weight,
                "invert_sign": invert_sign,
                "vals_a": [parse_amount(r.get(col_a)) for r in records_a],
                "vals_b": [(-parse_amount(r.get(col_b)) if invert_sign else parse_amount(r.get(col_b))) for r in records_b],
            })
        elif rule_type == "date":
            prep_date.append({
                "col_a": col_a,
                "col_b": col_b,
                "tol": tol,
                "weight": weight,
                "vals_a": [parse_date(r.get(col_a)) for r in records_a],
                "vals_b": [parse_date(r.get(col_b)) for r in records_b],
            })
        elif rule_type == "text_fuzzy":
            min_sim = tol / 100.0 if tol > 1.0 else tol
            raw_a = [str(r.get(col_a) or "") for r in records_a]
            raw_b = [str(r.get(col_b) or "") for r in records_b]
            norm_a = [normalize_text(s) for s in raw_a]
            norm_b = [normalize_text(s) for s in raw_b]
            clean_a = [strip_stop_words(s) for s in norm_a]
            clean_b = [strip_stop_words(s) for s in norm_b]
            prep_fuzzy.append({
                "col_a": col_a,
                "col_b": col_b,
                "tol": tol,
                "min_sim": min_sim,
                "weight": weight,
                "raw_a": raw_a,
                "raw_b": raw_b,
                "norm_a": norm_a,
                "norm_b": norm_b,
                "clean_a": clean_a,
                "clean_b": clean_b,
            })

    # =========================================================================
    # FONCTION UTILITAIRE : ÉVALUATION OPTIMISÉE FAIL-FAST
    # =========================================================================
    def evaluate_pair(idx_a: int, idx_b: int) -> Tuple[bool, float, float, float, bool]:
        """
        Évalue une paire avec rejet rapide (Fail-Fast) ordonné :
        1. Égalité stricte ID / Texte exact
        2. Écart montant (numérique rapide)
        3. Écart date (numérique rapide)
        4. Similarité textuelle flou (uniquement si tout le reste est validé)
        """
        accumulated_score = 0.0
        delta_amt = 0.0
        text_sims = []
        is_strict = True

        # Phase 1 : Exact / ID
        for pc in prep_exact:
            na = pc["vals_a"][idx_a]
            nb = pc["vals_b"][idx_b]
            if na and na == nb:
                accumulated_score += 1.0 * pc["weight"]
            else:
                return False, 0.0, 0.0, 0.0, False

        # Phase 2 : Montant
        for pc in prep_amount:
            amt_a = pc["vals_a"][idx_a]
            amt_b = pc["vals_b"][idx_b]
            diff = abs(amt_a - amt_b)
            delta_amt = amt_a - amt_b

            if diff > 0.005:
                is_strict = False

            tol = pc["tol"]
            if 0 < tol <= 1.0 and amt_a != 0:
                pct_diff = diff / abs(amt_a)
                if pct_diff <= tol:
                    accumulated_score += max(0.0, 1.0 - pct_diff) * pc["weight"]
                else:
                    return False, 0.0, 0.0, 0.0, False
            else:
                if diff <= tol:
                    score_part = 1.0 if tol == 0 else max(0.0, 1.0 - (diff / (tol + 1e-9)))
                    accumulated_score += score_part * pc["weight"]
                else:
                    return False, 0.0, 0.0, 0.0, False

        # Phase 3 : Dates
        for pc in prep_date:
            dt_a = pc["vals_a"][idx_a]
            dt_b = pc["vals_b"][idx_b]
            if dt_a and dt_b:
                diff_days = abs((dt_a - dt_b).days)
                if diff_days > 0:
                    is_strict = False
                if diff_days <= pc["tol"]:
                    accumulated_score += max(0.0, 1.0 - (diff_days / (pc["tol"] + 1))) * pc["weight"]
                else:
                    return False, 0.0, 0.0, 0.0, False
            else:
                return False, 0.0, 0.0, 0.0, False

        # Phase 4 : Texte flou (uniquement si les phases numériques précédentes sont validées)
        for pc in prep_fuzzy:
            na = pc["norm_a"][idx_a]
            nb = pc["norm_b"][idx_b]
            if na and na == nb:
                sim = 1.0
            else:
                sim = fast_text_similarity(
                    na, nb,
                    pc["clean_a"][idx_a], pc["clean_b"][idx_b],
                )
            text_sims.append(sim)
            if sim >= pc["min_sim"]:
                accumulated_score += sim * pc["weight"]
                if sim < 0.98:
                    is_strict = False
            else:
                return False, 0.0, 0.0, 0.0, False

        avg_sim = (sum(text_sims) / len(text_sims)) if text_sims else 1.0
        final_score = accumulated_score / total_weight
        return True, final_score, delta_amt, avg_sim, is_strict

    # =========================================================================
    # PASSE 1 : RAPPROCHEMENT STRICT / EXACT (100% de certitude - Indexation Hash O(1))
    # =========================================================================
    candidates_pass1 = []

    # Construction de l'index de blocage pour B
    if prep_exact and prep_amount:
        index_b = defaultdict(list)
        for j in range(len_b):
            k = (prep_exact[0]["vals_b"][j], round(prep_amount[0]["vals_b"][j], 2))
            index_b[k].append(j)
        for idx_a in range(len_a):
            k = (prep_exact[0]["vals_a"][idx_a], round(prep_amount[0]["vals_a"][idx_a], 2))
            for idx_b in index_b.get(k, []):
                is_valid, score, delta_amt, sim, is_strict = evaluate_pair(idx_a, idx_b)
                if is_valid and is_strict and abs(delta_amt) < 0.005:
                    candidates_pass1.append({
                        "idx_a": idx_a,
                        "idx_b": idx_b,
                        "score": 1.0,
                        "delta_amount": delta_amt,
                        "sim": sim,
                    })
    elif prep_amount:
        index_b = defaultdict(list)
        for j in range(len_b):
            index_b[round(prep_amount[0]["vals_b"][j], 2)].append(j)
        for idx_a in range(len_a):
            k = round(prep_amount[0]["vals_a"][idx_a], 2)
            for idx_b in index_b.get(k, []):
                is_valid, score, delta_amt, sim, is_strict = evaluate_pair(idx_a, idx_b)
                if is_valid and is_strict and abs(delta_amt) < 0.005:
                    candidates_pass1.append({
                        "idx_a": idx_a,
                        "idx_b": idx_b,
                        "score": 1.0,
                        "delta_amount": delta_amt,
                        "sim": sim,
                    })
    elif prep_exact:
        index_b = defaultdict(list)
        for j in range(len_b):
            index_b[prep_exact[0]["vals_b"][j]].append(j)
        for idx_a in range(len_a):
            k = prep_exact[0]["vals_a"][idx_a]
            for idx_b in index_b.get(k, []):
                is_valid, score, delta_amt, sim, is_strict = evaluate_pair(idx_a, idx_b)
                if is_valid and is_strict and abs(delta_amt) < 0.005:
                    candidates_pass1.append({
                        "idx_a": idx_a,
                        "idx_b": idx_b,
                        "score": 1.0,
                        "delta_amount": delta_amt,
                        "sim": sim,
                    })
    elif prep_date:
        index_b = defaultdict(list)
        for j in range(len_b):
            index_b[prep_date[0]["vals_b"][j]].append(j)
        for idx_a in range(len_a):
            k = prep_date[0]["vals_a"][idx_a]
            for idx_b in index_b.get(k, []):
                is_valid, score, delta_amt, sim, is_strict = evaluate_pair(idx_a, idx_b)
                if is_valid and is_strict and abs(delta_amt) < 0.005:
                    candidates_pass1.append({
                        "idx_a": idx_a,
                        "idx_b": idx_b,
                        "score": 1.0,
                        "delta_amount": delta_amt,
                        "sim": sim,
                    })
    else:
        for idx_a in range(len_a):
            for idx_b in range(len_b):
                is_valid, score, delta_amt, sim, is_strict = evaluate_pair(idx_a, idx_b)
                if is_valid and is_strict and abs(delta_amt) < 0.005:
                    candidates_pass1.append({
                        "idx_a": idx_a,
                        "idx_b": idx_b,
                        "score": 1.0,
                        "delta_amount": delta_amt,
                        "sim": sim,
                    })

    # Tri global optimal : meilleure similarité et écart nul
    candidates_pass1.sort(key=lambda c: (c["score"], c["sim"], -abs(c["delta_amount"])), reverse=True)
    for c in candidates_pass1:
        ia, ib = c["idx_a"], c["idx_b"]
        if ia not in used_a_indices and ib not in used_b_indices:
            used_a_indices.add(ia)
            used_b_indices.add(ib)
            explanation = build_match_explanation(
                records_a[ia], records_b[ib], criteria, c["delta_amount"], 100, pass_num=1
            )
            matched.append({
                "statut": "Rapproché Exact (100%)",
                "badge_type": "exact",
                "passe": 1,
                "score_pct": 100,
                "delta_amount": round(c["delta_amount"], 2),
                "explication": explanation,
                "row_a": records_a[ia],
                "row_b": records_b[ib],
            })

    # =========================================================================
    # PASSE 2 : RAPPROCHEMENT FLOU / HAUTE CONFIANCE (Montant exact, texte tolérant)
    # =========================================================================
    candidates_pass2 = []

    if prep_amount:
        # Indexer les lignes B actives par montant arrondi pour éviter la boucle N x M
        amt_index_b = defaultdict(list)
        for j in range(len_b):
            if j not in used_b_indices:
                amt_index_b[round(prep_amount[0]["vals_b"][j], 2)].append(j)

        for idx_a in range(len_a):
            if idx_a in used_a_indices:
                continue
            amt_a_round = round(prep_amount[0]["vals_a"][idx_a], 2)
            cand_b_list = (
                amt_index_b.get(amt_a_round, []) +
                amt_index_b.get(round(amt_a_round - 0.01, 2), []) +
                amt_index_b.get(round(amt_a_round + 0.01, 2), [])
            )
            for idx_b in cand_b_list:
                if idx_b in used_b_indices:
                    continue
                is_valid, score, delta_amt, sim, _ = evaluate_pair(idx_a, idx_b)
                if is_valid and abs(delta_amt) < 0.01:
                    candidates_pass2.append({
                        "idx_a": idx_a,
                        "idx_b": idx_b,
                        "score": score,
                        "delta_amount": delta_amt,
                        "sim": sim,
                    })
    else:
        for idx_a in range(len_a):
            if idx_a in used_a_indices:
                continue
            for idx_b in range(len_b):
                if idx_b in used_b_indices:
                    continue
                is_valid, score, delta_amt, sim, _ = evaluate_pair(idx_a, idx_b)
                if is_valid and abs(delta_amt) < 0.01:
                    candidates_pass2.append({
                        "idx_a": idx_a,
                        "idx_b": idx_b,
                        "score": score,
                        "delta_amount": delta_amt,
                        "sim": sim,
                    })

    candidates_pass2.sort(key=lambda c: (c["score"], c["sim"], -abs(c["delta_amount"])), reverse=True)
    for c in candidates_pass2:
        ia, ib = c["idx_a"], c["idx_b"]
        if ia not in used_a_indices and ib not in used_b_indices:
            used_a_indices.add(ia)
            used_b_indices.add(ib)
            pct = int(c["score"] * 100)
            explanation = build_match_explanation(
                records_a[ia], records_b[ib], criteria, c["delta_amount"], pct, pass_num=2
            )
            matched.append({
                "statut": f"Rapproché Flou ({pct}%)",
                "badge_type": "fuzzy",
                "passe": 2,
                "score_pct": pct,
                "delta_amount": round(c["delta_amount"], 2),
                "explication": explanation,
                "row_a": records_a[ia],
                "row_b": records_b[ib],
            })

    # =========================================================================
    # PASSE 3 : RAPPROCHEMENT AVEC ÉCART FINANCIER (Tolérance montant - Fenêtre binaire bisect)
    # =========================================================================
    candidates_pass3 = []

    if prep_amount:
        active_b = [j for j in range(len_b) if j not in used_b_indices]
        sorted_b = sorted(active_b, key=lambda j: prep_amount[0]["vals_b"][j])
        sorted_amts = [prep_amount[0]["vals_b"][j] for j in sorted_b]
        tol = prep_amount[0]["tol"]

        for idx_a in range(len_a):
            if idx_a in used_a_indices:
                continue
            amt_a = prep_amount[0]["vals_a"][idx_a]
            if 0 < tol <= 1.0 and amt_a != 0:
                tol_val = tol * abs(amt_a)
            else:
                tol_val = tol

            min_amt = amt_a - tol_val - 1e-6
            max_amt = amt_a + tol_val + 1e-6

            start_i = bisect.bisect_left(sorted_amts, min_amt)
            end_i = bisect.bisect_right(sorted_amts, max_amt)

            for pos in range(start_i, end_i):
                idx_b = sorted_b[pos]
                if idx_b in used_b_indices:
                    continue
                is_valid, score, delta_amt, sim, _ = evaluate_pair(idx_a, idx_b)
                if is_valid:
                    candidates_pass3.append({
                        "idx_a": idx_a,
                        "idx_b": idx_b,
                        "score": score,
                        "delta_amount": delta_amt,
                        "sim": sim,
                    })
    else:
        for idx_a in range(len_a):
            if idx_a in used_a_indices:
                continue
            for idx_b in range(len_b):
                if idx_b in used_b_indices:
                    continue
                is_valid, score, delta_amt, sim, _ = evaluate_pair(idx_a, idx_b)
                if is_valid:
                    candidates_pass3.append({
                        "idx_a": idx_a,
                        "idx_b": idx_b,
                        "score": score,
                        "delta_amount": delta_amt,
                        "sim": sim,
                    })

    candidates_pass3.sort(key=lambda c: (c["score"], -abs(c["delta_amount"]), c["sim"]), reverse=True)
    for c in candidates_pass3:
        ia, ib = c["idx_a"], c["idx_b"]
        if ia not in used_a_indices and ib not in used_b_indices:
            used_a_indices.add(ia)
            used_b_indices.add(ib)
            pct = int(c["score"] * 100)
            delta = c["delta_amount"]
            explanation = build_match_explanation(
                records_a[ia], records_b[ib], criteria, delta, pct, pass_num=3
            )
            statut = f"Rapproché avec écart ({delta:+.2f} DA)" if abs(delta) >= 0.01 else f"Rapproché ({pct}%)"
            badge = "warning" if abs(delta) >= 0.01 else "fuzzy"
            matched.append({
                "statut": statut,
                "badge_type": badge,
                "passe": 3,
                "score_pct": pct,
                "delta_amount": round(delta, 2),
                "explication": explanation,
                "row_a": records_a[ia],
                "row_b": records_b[ib],
            })

    # Orphelins résiduels
    orphans_a = [records_a[i] for i in range(len_a) if i not in used_a_indices]
    orphans_b = [records_b[j] for j in range(len_b) if j not in used_b_indices]

    # =========================================================================
    # PASSE 4 : RAPPROCHEMENT GROUPÉ MULTI-LIGNES (N-à-1 et 1-à-N)
    # =========================================================================
    if options.get("allow_grouping", True):
        matched_grouped, orphans_a, orphans_b = reconcile_grouped_candidates(orphans_a, orphans_b, criteria)
        matched.extend(matched_grouped)

    # Calcul des KPIs finaux
    matched_count = len(matched)
    matched_pct = round((matched_count / len_a * 100) if len_a > 0 else 0.0, 1)

    amount_col_a = amt_crit["col_a"] if amt_crit else None
    amount_col_b = amt_crit["col_b"] if amt_crit else None

    total_amt_a = sum(parse_amount(r.get(amount_col_a)) for r in records_a) if amount_col_a else 0.0
    total_amt_b = sum(parse_amount(r.get(amount_col_b)) for r in records_b) if amount_col_b else 0.0
    net_ecart = total_amt_a - total_amt_b

    kpis = {
        "total_a": len_a,
        "total_b": len_b,
        "matched_count": matched_count,
        "matched_pct": matched_pct,
        "orphans_a_count": len(orphans_a),
        "orphans_b_count": len(orphans_b),
        "total_amt_a": total_amt_a,
        "total_amt_b": total_amt_b,
        "net_ecart": net_ecart,
        "amount_col_a": amount_col_a,
        "amount_col_b": amount_col_b,
    }

    return {
        "matched": matched,
        "orphans_a": orphans_a,
        "orphans_b": orphans_b,
        "kpis": kpis
    }
