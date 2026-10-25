"""
Moteur de rapprochement multi-critères haute performance.
Supporte Texte Exact, Texte Tolérant/Fuzzy, Inversion Nom/Prénom, Montant et Date.
"""
import re
import unicodedata
import itertools
from difflib import SequenceMatcher
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any, Tuple

def normalize_text(val: Any) -> str:
    """Normalise une chaîne : sans accents, majuscules, espaces consolidés."""
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    return re.sub(r"\s+", " ", s)

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

def compute_text_similarity(str_a: str, str_b: str) -> float:
    """Similarité avec support de l'inversion de mots (ex: Nom Prénom vs Prénom Nom)."""
    norm_a = normalize_text(str_a)
    norm_b = normalize_text(str_b)
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 1.0
        
    tok_a = norm_a.split()
    tok_b = norm_b.split()
    
    # 1. Direct SequenceMatcher
    ratio_direct = SequenceMatcher(None, norm_a, norm_b).ratio()
    
    # 2. Inversion si 2 mots
    ratio_inverted = 0.0
    if len(tok_a) == 2 and len(tok_b) == 2:
        rev_b = f"{tok_b[1]} {tok_b[0]}"
        ratio_inverted = SequenceMatcher(None, norm_a, rev_b).ratio()
    elif set(tok_a) == set(tok_b):
        return 0.98
        
    # 3. Ratio par composantes minimales
    ratio_comp = 0.0
    if len(tok_a) >= 2 and len(tok_b) >= 2:
        sim_d = min(SequenceMatcher(None, tok_a[0], tok_b[0]).ratio(), SequenceMatcher(None, tok_a[-1], tok_b[-1]).ratio())
        sim_x = min(SequenceMatcher(None, tok_a[0], tok_b[-1]).ratio(), SequenceMatcher(None, tok_a[-1], tok_b[0]).ratio())
        ratio_comp = max(sim_d, sim_x)
        
    return max(ratio_direct, ratio_inverted, ratio_comp)

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

    # 1. Passe N-à-1 : Plusieurs lignes A = 1 ligne B
    idx_b = 0
    while idx_b < len(remaining_b):
        row_b = remaining_b[idx_b]
        target_amt_b = parse_amount(row_b.get(col_b))
        if invert_sign:
            target_amt_b = -target_amt_b

        found_combo = None
        max_k = min(4, len(remaining_a))
        
        # Filtrer candidats ayant un montant non nul et même signe
        cand_indices = [
            i for i, r in enumerate(remaining_a)
            if (parse_amount(r.get(col_a)) * target_amt_b) >= 0 and abs(parse_amount(r.get(col_a))) <= abs(target_amt_b) + 1.0
        ]

        for k in range(2, max_k + 1):
            if len(cand_indices) < k:
                break
            for combo in itertools.combinations(cand_indices[:25], k):
                sum_a = sum(parse_amount(remaining_a[i].get(col_a)) for i in combo)
                diff = abs(sum_a - target_amt_b)
                
                is_match = False
                if 0 < tol <= 1.0 and target_amt_b != 0:
                    is_match = (diff / abs(target_amt_b)) <= tol
                else:
                    is_match = diff <= tol
                
                if is_match:
                    if text_crit:
                        txt_b = str(row_b.get(text_crit["col_b"], ""))
                        if len(txt_b.strip()) > 3:
                            has_txt = any(
                                compute_text_similarity(str(remaining_a[i].get(text_crit["col_a"], "")), txt_b) >= 0.4
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
            delta = sum(parse_amount(r.get(col_a)) for r in group_a_rows) - target_amt_b
            grp_id = f"GRP-{len(matched_grouped) + 1}"
            for r_a in group_a_rows:
                matched_grouped.append({
                    "statut": f"Rapproché N-à-1 ({len(group_a_rows)} lig. A = 1 lig. B)",
                    "badge_type": "grouped",
                    "score_pct": 95,
                    "delta_amount": round(delta, 2),
                    "row_a": r_a,
                    "row_b": row_b,
                    "group_id": grp_id,
                })
            for i in sorted(found_combo, reverse=True):
                del remaining_a[i]
            del remaining_b[idx_b]
        else:
            idx_b += 1

    # 2. Passe 1-à-N : 1 ligne A = Plusieurs lignes B
    idx_a = 0
    while idx_a < len(remaining_a):
        row_a = remaining_a[idx_a]
        target_amt_a = parse_amount(row_a.get(col_a))
        found_combo = None
        max_k = min(4, len(remaining_b))
        
        cand_indices = []
        for j, r in enumerate(remaining_b):
            amt_b = -parse_amount(r.get(col_b)) if invert_sign else parse_amount(r.get(col_b))
            if (amt_b * target_amt_a) >= 0 and abs(amt_b) <= abs(target_amt_a) + 1.0:
                cand_indices.append(j)

        for k in range(2, max_k + 1):
            if len(cand_indices) < k:
                break
            for combo in itertools.combinations(cand_indices[:25], k):
                sum_b = sum(
                    (-parse_amount(remaining_b[j].get(col_b)) if invert_sign else parse_amount(remaining_b[j].get(col_b)))
                    for j in combo
                )
                diff = abs(target_amt_a - sum_b)
                is_match = False
                if 0 < tol <= 1.0 and target_amt_a != 0:
                    is_match = (diff / abs(target_amt_a)) <= tol
                else:
                    is_match = diff <= tol
                
                if is_match:
                    if text_crit:
                        txt_a = str(row_a.get(text_crit["col_a"], ""))
                        if len(txt_a.strip()) > 3:
                            has_txt = any(
                                compute_text_similarity(txt_a, str(remaining_b[j].get(text_crit["col_b"], ""))) >= 0.4
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
            sum_b = sum(
                (-parse_amount(r.get(col_b)) if invert_sign else parse_amount(r.get(col_b)))
                for r in group_b_rows
            )
            delta = target_amt_a - sum_b
            grp_id = f"GRP-{len(matched_grouped) + 1}"
            for r_b in group_b_rows:
                matched_grouped.append({
                    "statut": f"Rapproché 1-à-N (1 lig. A = {len(group_b_rows)} lig. B)",
                    "badge_type": "grouped",
                    "score_pct": 95,
                    "delta_amount": round(delta, 2),
                    "row_a": row_a,
                    "row_b": r_b,
                    "group_id": grp_id,
                })
            for j in sorted(found_combo, reverse=True):
                del remaining_b[j]
            del remaining_a[idx_a]
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
    Exécute le rapprochement complet 1-à-1 entre df_a et df_b selon les critères fournis.
    """
    options = options or {}
    matched = []
    orphans_a = []
    orphans_b = []
    
    records_a = df_a.to_dict(orient="records")
    records_b = df_b.to_dict(orient="records")
    
    len_a = len(records_a)
    len_b = len(records_b)
    
    if not criteria:
        return {
            "matched": [],
            "orphans_a": records_a,
            "orphans_b": records_b,
            "kpis": {"total_a": len_a, "total_b": len_b, "matched_count": 0, "matched_pct": 0.0}
        }
        
    # Préparation des index et des valeurs nettoyées pour la rapidité
    used_b_indices = set()
    
    # Évaluation paire à paire
    for idx_a, row_a in enumerate(records_a):
        best_b_idx = None
        best_score = 0.0
        best_match_rule = ""
        best_delta_amount = 0.0
        
        for idx_b, row_b in enumerate(records_b):
            if idx_b in used_b_indices:
                continue
                
            total_weight = 0.0
            accumulated_score = 0.0
            matches_all_strict = True
            delta_amount_candidate = 0.0
            
            for crit in criteria:
                col_a = crit["col_a"]
                col_b = crit["col_b"]
                rule_type = crit.get("rule_type", "text_exact")
                tol = float(crit.get("tolerance", 0.0))
                weight = float(crit.get("weight", 1.0))
                invert_sign = bool(crit.get("invert_sign", False))
                
                val_a = row_a.get(col_a)
                val_b = row_b.get(col_b)
                
                total_weight += weight
                
                if rule_type == "text_exact":
                    na = normalize_text(val_a)
                    nb = normalize_text(val_b)
                    if na and na == nb:
                        accumulated_score += 1.0 * weight
                    else:
                        matches_all_strict = False
                        break
                        
                elif rule_type == "text_fuzzy":
                    sim = compute_text_similarity(str(val_a or ""), str(val_b or ""))
                    min_sim = tol / 100.0 if tol > 1.0 else tol
                    if sim >= min_sim:
                        accumulated_score += sim * weight
                    else:
                        matches_all_strict = False
                        break
                        
                elif rule_type == "amount":
                    amt_a = parse_amount(val_a)
                    amt_b = parse_amount(val_b)
                    if invert_sign:
                        amt_b = -amt_b
                    diff = abs(amt_a - amt_b)
                    delta_amount_candidate = amt_a - amt_b
                    
                    # Tolérance absolue ou pourcentage
                    if tol > 0 and tol <= 1.0 and amt_a != 0:
                        pct_diff = diff / abs(amt_a)
                        if pct_diff <= tol:
                            accumulated_score += (1.0 - pct_diff) * weight
                        else:
                            matches_all_strict = False
                            break
                    else:
                        if diff <= tol:
                            accumulated_score += 1.0 * weight
                        else:
                            matches_all_strict = False
                            break
                            
                elif rule_type == "date":
                    dt_a = parse_date(val_a)
                    dt_b = parse_date(val_b)
                    if dt_a and dt_b:
                        diff_days = abs((dt_a - dt_b).days)
                        if diff_days <= tol:
                            accumulated_score += max(0.0, 1.0 - (diff_days / (tol + 1))) * weight
                        else:
                            matches_all_strict = False
                            break
                    else:
                        matches_all_strict = False
                        break
                        
            if matches_all_strict and total_weight > 0:
                final_score = accumulated_score / total_weight
                if final_score > best_score:
                    best_score = final_score
                    best_b_idx = idx_b
                    best_delta_amount = delta_amount_candidate
                    
        if best_b_idx is not None and best_score > 0.0:
            used_b_indices.add(best_b_idx)
            matched_b_row = records_b[best_b_idx]
            
            # Qualification du statut
            pct = int(best_score * 100)
            if pct >= 99 and abs(best_delta_amount) < 0.01:
                statut = "Rapproché (Exact 100%)"
                badge_type = "exact"
            elif abs(best_delta_amount) >= 0.01:
                statut = f"Rapproché avec écart ({best_delta_amount:+.2f} DA)"
                badge_type = "warning"
            else:
                statut = f"Rapproché (Variante d'orthographe {pct}%)"
                badge_type = "fuzzy"
                
            matched.append({
                "statut": statut,
                "badge_type": badge_type,
                "score_pct": pct,
                "delta_amount": best_delta_amount,
                "row_a": row_a,
                "row_b": matched_b_row,
            })
        else:
            orphans_a.append(row_a)
            
    # Orphelins B
    for idx_b, row_b in enumerate(records_b):
        if idx_b not in used_b_indices:
            orphans_b.append(row_b)

    # Passe multi-lignes N-à-1 et 1-à-N sur les suspens
    if options.get("allow_grouping", True):
        matched_grouped, orphans_a, orphans_b = reconcile_grouped_candidates(orphans_a, orphans_b, criteria)
        matched.extend(matched_grouped)
            
    # Calcul des KPIs
    matched_count = len(matched)
    matched_pct = round((matched_count / len_a * 100) if len_a > 0 else 0.0, 1)
    
    # Sommes montants si colonne montant présente
    amount_col_a = next((c["col_a"] for c in criteria if c.get("rule_type") == "amount"), None)
    amount_col_b = next((c["col_b"] for c in criteria if c.get("rule_type") == "amount"), None)
    
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
