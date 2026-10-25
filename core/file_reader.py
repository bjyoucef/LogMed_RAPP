"""
Module de lecture robuste de fichiers Excel (.xlsx, .xls) et CSV.
"""
import os
import csv
import pandas as pd
from typing import List, Tuple, Dict, Any, Optional

def get_file_sheets(file_path: str) -> List[str]:
    """Retourne la liste des feuilles pour un classeur Excel, ou ['Données CSV']."""
    if not os.path.exists(file_path):
        return []
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ('.xlsx', '.xlsm', '.xltx', '.xltm'):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True, keep_links=False)
            names = wb.sheetnames
            wb.close()
            return names
        except Exception:
            pass
        try:
            xl = pd.ExcelFile(file_path)
            return xl.sheet_names
        except Exception:
            return ["Feuil1"]
    elif ext == '.xls':
        try:
            xl = pd.ExcelFile(file_path)
            return xl.sheet_names
        except Exception:
            return ["Feuil1"]
    elif ext in ('.csv', '.tsv', '.txt'):
        return ["Données CSV"]
    return ["Données"]

def detect_csv_separator(file_path: str) -> str:
    """Détecte automatiquement le séparateur CSV (, ; \t ou |)."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(4096)
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=',;\t|')
            return dialect.delimiter
    except Exception:
        # Analyse de fréquence
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = "".join([f.readline() for _ in range(5)])
                counts = {sep: first_lines.count(sep) for sep in [';', ',', '\t', '|']}
                best_sep = max(counts, key=counts.get)
                return best_sep if counts[best_sep] > 0 else ';'
        except Exception:
            return ';'

def read_full_table(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """Charge l'intégralité du fichier en DataFrame pandas nettoyé."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ('.xlsx', '.xlsm', '.xls'):
        sheet = sheet_name if sheet_name and sheet_name != "Toutes" else 0
        df = pd.read_excel(file_path, sheet_name=sheet, dtype=object)
    elif ext in ('.csv', '.tsv', '.txt'):
        sep = detect_csv_separator(file_path)
        try:
            df = pd.read_csv(file_path, sep=sep, encoding='utf-8', dtype=object)
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, sep=sep, encoding='cp1252', dtype=object)
    else:
        raise ValueError(f"Format de fichier non pris en charge : {ext}")

    # Nettoyage des noms de colonnes
    df.columns = [str(c).strip() if c is not None else f"Col_{i}" for i, c in enumerate(df.columns)]
    # Supprimer les lignes et colonnes entièrement vides
    df = df.dropna(how='all')
    df = df.dropna(axis=1, how='all')
    df = df.reset_index(drop=True)
    return df

def read_table_sample(file_path: str, sheet_name: Optional[str] = None, nrows: int = 5) -> Tuple[List[str], List[Dict[str, Any]], int]:
    """Retourne (colonnes, 5 premières lignes, nombre total estimé de lignes)."""
    df = read_full_table(file_path, sheet_name=sheet_name)
    columns = list(df.columns)
    total_rows = len(df)
    sample_df = df.head(nrows).fillna('')
    sample_rows = sample_df.to_dict(orient='records')
    return columns, sample_rows, total_rows
