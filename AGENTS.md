# AGENTS.md — LogMed RAPP

French-language PyQt5 desktop app that reconciles two Excel/CSV tables and exports a 4-sheet `.xlsx` report. UI labels, comments, and README are French; keep new user-facing text and comments French.

## Commands (Windows / PowerShell, run from repo root)

- Setup: `.\setup_env.bat` (creates `.venv` from local Python; current venv is CPython 3.14 at `.venv`)
- Run: `.\.venv\Scripts\python.exe main.py` — prefer this over `run_app.bat`, which uses `start` and hides tracebacks
- All tests: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
- Single test: `.\.venv\Scripts\python.exe -m unittest tests.test_engine.TestReconciliationEngine.test_reconcile_tables -v`
- Build exe: `.\build_exe.bat` → `dist\LogMed_RAPP\` (PyInstaller `--onedir --windowed`)
- No lint, formatter, typecheck, CI, or pre-commit config exists. Tests use `unittest`, not pytest (`.pytest_cache` is stale; pytest is not installed).

Imports are root-relative (`from core...`, `from ui...`). Always launch/test from the repo root; `main.py` is the only entrypoint.

## Layout

- `main.py` — QApplication bootstrap and global stylesheet
- `core/` — GUI-free logic: `file_reader`, `column_detector`, `matching_engine`, `excel_exporter`, `profile_manager`
- `ui/` — PyQt5 widgets: 3-step wizard in `main_window.py` (files → mapping/rules → preview/export)
- `tests/test_engine.py` — covers core modules only; no fixtures or UI/file-reader tests
- `profiles/` — runtime JSON profiles written by `profile_manager` (path derived from package location, not CWD); tests create and delete `profiles/Profil_Test.json`

## Reconciliation semantics (non-obvious)

- Criterion shape: `{"col_a", "col_b", "rule_type", "tolerance", "weight"}` plus optional `"invert_sign"`. Rule types: `text_exact`, `text_fuzzy`, `amount`, `date`.
- `amount` tolerance is ambiguous: `0 < tolerance <= 1.0` is treated as a **fraction of A** (0.05 = 5%), while `> 1.0` is an **absolute amount**. This contradicts README wording about ±0.05 DA.
- `text_fuzzy` tolerance: `> 1.0` is a percentage (85.0), otherwise a fraction (0.85).
- `date` tolerance is in days.
- Auto-suggested defaults in `column_detector.py`: amount `0.05` (thus 5%, not ±0.05 DA), `text_fuzzy` `85.0`, date `3` days, `id` `text_exact`.
- Matching is greedy one-to-one: each A row takes its best still-unused B row; it is not a globally optimal assignment. `matched_pct` divides by `len(A)`.
- Text similarity is implemented with `difflib.SequenceMatcher`, **not** `rapidfuzz`, despite RapidFuzz being in `requirements.txt`. Excel export uses `openpyxl`, not `xlsxwriter`; both are currently unused dependencies.
- Export sheet titles are relied on downstream: `Synthèse & KPIs`, `Rapprochés`, `Suspens Tableau A`, `Suspens Tableau B`.
- Heavy reconciliation runs in `WorkerThread`; keep long work off the GUI thread and report failures via the `error` signal.

## File reading quirks

- Excel read with `dtype=object`; all-empty rows/columns dropped.
- CSV/TSV separator auto-sniffed (`, ; \t |`), UTF-8 then `cp1252` fallback.
- `.xls` support relies on pandas' Excel engine; only `.xlsx/.xlsm/.xltx/.xltm` are opened with openpyxl for sheet listing.
