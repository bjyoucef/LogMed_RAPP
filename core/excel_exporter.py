"""
Générateur professionnel de classeur Excel à 4 onglets stylisés.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from typing import Dict, Any, List

def format_cell_header(cell, text: str, fill_hex: str = "1E3A8A"):
    """Applique le style d'en-tête SaaS LogMed."""
    cell.value = text
    cell.font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    cell.fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

def export_reconciliation_excel(
    output_path: str,
    reconciliation_results: Dict[str, Any],
    criteria: List[Dict[str, Any]],
    file_a_name: str = "Tableau A",
    file_b_name: str = "Tableau B"
):
    """Génère le classeur Excel multi-onglets complet."""
    wb = openpyxl.Workbook()
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )
    
    kpis = reconciliation_results.get("kpis", {})
    matched = reconciliation_results.get("matched", [])
    orphans_a = reconciliation_results.get("orphans_a", [])
    orphans_b = reconciliation_results.get("orphans_b", [])
    
    # -------------------------------------------------------------
    # 1. FEUILLE : SYNTHÈSE & DASHBOARD
    # -------------------------------------------------------------
    ws_syn = wb.active
    ws_syn.title = "Synthèse & KPIs"
    ws_syn.views.sheetView[0].showGridLines = True
    
    # Titre Hero
    ws_syn.merge_cells("A1:G2")
    hero_cell = ws_syn["A1"]
    hero_cell.value = "LOGMED RAPP — RAPPORT DE RAPPROCHEMENT INTELLIGENT"
    hero_cell.font = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
    hero_cell.fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    hero_cell.alignment = Alignment(horizontal="center", vertical="center")
    
    ws_syn["A3"].value = f"Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M')} | Fichier A : {file_a_name} | Fichier B : {file_b_name}"
    ws_syn["A3"].font = Font(name="Segoe UI", size=9, italic=True, color="64748B")
    
    # Tableaux de KPIs
    kpi_cards = [
        ("TOTAL LIGNES (A)", kpis.get("total_a", 0), "1E3A8A"),
        ("TOTAL LIGNES (B)", kpis.get("total_b", 0), "0284C7"),
        ("RAPPROCHÉS", f"{kpis.get('matched_count', 0)} ({kpis.get('matched_pct', 0)}%)", "059669"),
        ("SUSPENS (A)", kpis.get("orphans_a_count", 0), "D97706"),
        ("SUSPENS (B)", kpis.get("orphans_b_count", 0), "991B1B"),
    ]
    
    col_idx = 1
    for title, val, color in kpi_cards:
        c_title = ws_syn.cell(row=5, column=col_idx, value=title)
        c_title.font = Font(name="Segoe UI", size=8, bold=True, color="FFFFFF")
        c_title.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
        c_title.alignment = Alignment(horizontal="center", vertical="center")
        
        c_val = ws_syn.cell(row=6, column=col_idx, value=val)
        c_val.font = Font(name="Segoe UI", size=12, bold=True, color="1E293B")
        c_val.alignment = Alignment(horizontal="center", vertical="center")
        c_val.border = thin_border
        
        ws_syn.column_dimensions[get_column_letter(col_idx)].width = 22
        col_idx += 1
        
    # Table des critères utilisés
    ws_syn.cell(row=9, column=1, value="CRITÈRES DE RAPPROCHEMENT UTILISÉS").font = Font(name="Segoe UI", size=11, bold=True, color="1E3A8A")
    crit_headers = ["N°", "Colonne Fichier A", "Colonne Fichier B", "Type de Règle", "Tolérance", "Poids"]
    for i, h in enumerate(crit_headers, 1):
        format_cell_header(ws_syn.cell(row=10, column=i), h, "334155")
        
    for r_idx, cr in enumerate(criteria, 11):
        ws_syn.cell(row=r_idx, column=1, value=r_idx - 10).alignment = Alignment(horizontal="center")
        ws_syn.cell(row=r_idx, column=2, value=cr.get("col_a"))
        ws_syn.cell(row=r_idx, column=3, value=cr.get("col_b"))
        ws_syn.cell(row=r_idx, column=4, value=cr.get("rule_type"))
        ws_syn.cell(row=r_idx, column=5, value=str(cr.get("tolerance")))
        ws_syn.cell(row=r_idx, column=6, value=cr.get("weight", 1.0)).alignment = Alignment(horizontal="center")
        for c in range(1, 7):
            ws_syn.cell(row=r_idx, column=c).border = thin_border
            
    # -------------------------------------------------------------
    # 2. FEUILLE : DOSSIERS RAPPROCHÉS
    # -------------------------------------------------------------
    ws_mat = wb.create_sheet(title="Rapprochés")
    ws_mat.views.sheetView[0].showGridLines = True
    
    if matched:
        cols_a = list(matched[0]["row_a"].keys())
        cols_b = list(matched[0]["row_b"].keys())
        
        headers = ["N°", "STATUT RAPPROCHEMENT", "SCORE (%)", "ÉCART MONTANT"] + [f"[A] {c}" for c in cols_a] + [f"[B] {c}" for c in cols_b]
        for col_i, h in enumerate(headers, 1):
            fill_c = "1E3A8A" if "[A]" in h else ("0284C7" if "[B]" in h else "0F172A")
            format_cell_header(ws_mat.cell(row=1, column=col_i), h, fill_c)
            
        for row_i, m in enumerate(matched, 2):
            ws_mat.cell(row=row_i, column=1, value=row_i - 1).alignment = Alignment(horizontal="center")
            ws_mat.cell(row=row_i, column=2, value=m["statut"])
            ws_mat.cell(row=row_i, column=3, value=f"{m['score_pct']}%").alignment = Alignment(horizontal="center")
            
            c_delta = ws_mat.cell(row=row_i, column=4, value=m["delta_amount"])
            c_delta.number_format = '#,##0.00'
            
            # Données A
            curr_c = 5
            for c_name in cols_a:
                ws_mat.cell(row=row_i, column=curr_c, value=m["row_a"].get(c_name))
                curr_c += 1
            # Données B
            for c_name in cols_b:
                ws_mat.cell(row=row_i, column=curr_c, value=m["row_b"].get(c_name))
                curr_c += 1
                
            for col_k in range(1, len(headers) + 1):
                ws_mat.cell(row=row_i, column=col_k).border = thin_border
                
        # Auto-fit dimensions
        for c in range(1, min(len(headers) + 1, 35)):
            ws_mat.column_dimensions[get_column_letter(c)].width = 18
            
    # -------------------------------------------------------------
    # 3. FEUILLE : SUSPENS TABLEAU A
    # -------------------------------------------------------------
    ws_oa = wb.create_sheet(title="Suspens Tableau A")
    ws_oa.views.sheetView[0].showGridLines = True
    if orphans_a:
        cols_oa = list(orphans_a[0].keys())
        for c_i, h in enumerate(["N°"] + cols_oa, 1):
            format_cell_header(ws_oa.cell(row=1, column=c_i), h, "D97706")
        for r_i, o in enumerate(orphans_a, 2):
            ws_oa.cell(row=r_i, column=1, value=r_i - 1).alignment = Alignment(horizontal="center")
            for c_i, c_name in enumerate(cols_oa, 2):
                ws_oa.cell(row=r_i, column=c_i, value=o.get(c_name))
                ws_oa.cell(row=r_i, column=c_i).border = thin_border
            ws_oa.cell(row=r_i, column=1).border = thin_border
            
    # -------------------------------------------------------------
    # 4. FEUILLE : SUSPENS TABLEAU B
    # -------------------------------------------------------------
    ws_ob = wb.create_sheet(title="Suspens Tableau B")
    ws_ob.views.sheetView[0].showGridLines = True
    if orphans_b:
        cols_ob = list(orphans_b[0].keys())
        for c_i, h in enumerate(["N°"] + cols_ob, 1):
            format_cell_header(ws_ob.cell(row=1, column=c_i), h, "991B1B")
        for r_i, o in enumerate(orphans_b, 2):
            ws_ob.cell(row=r_i, column=1, value=r_i - 1).alignment = Alignment(horizontal="center")
            for c_i, c_name in enumerate(cols_ob, 2):
                ws_ob.cell(row=r_i, column=c_i, value=o.get(c_name))
                ws_ob.cell(row=r_i, column=c_i).border = thin_border
            ws_ob.cell(row=r_i, column=1).border = thin_border
            
    wb.save(output_path)
    wb.close()
    return output_path
