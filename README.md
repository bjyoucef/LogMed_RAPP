# LogMed RAPP — Rapprochement Intelligent de Tableaux Excel

Application de bureau autonome (PyQt5) développée pour réconcilier de manière intelligente et rapide deux fichiers Excel ou CSV.

## Fonctionnalités
- **Glisser-Déposer (Drag & Drop)** : Déposez directement les deux tableaux à comparer.
- **Support multi-onglets** : Choisissez la feuille souhaitée pour chaque classeur Excel.
- **Détection automatique des colonnes** : L'algorithme suggère les colonnes correspondantes (Texte, Montants, Dates, Identifiants).
- **Règles multi-critères configurables** :
  - Texte Exact ou Tolérance orthographique (Fuzzy matching, inversion Prénom/Nom).
  - Montants avec tolérance absolue (ex: ± 0,05 DA) ou en pourcentage, avec gestion Débit/Crédit.
  - Dates avec tolérance de jours.
  - **Rapprochement multi-lignes (N-à-1 et 1-à-N)** : Rapprochement automatique de plusieurs lignes dont la somme correspond à un montant global (ex: factures individuelles vs virement groupé).
- **Aperçu interactif & Atelier d'ajustement manuel** :
  - Consultation détaillée des *Dossiers Rapprochés*, *Suspens Tableau A* et *Suspens Tableau B*.
  - Recherche instantanée et tri sur toutes les colonnes.
  - **Dissociation en 1 clic** d'une paire rapprochée si nécessaire.
  - **Atelier d'Association Manuelle** pour lier directement une ligne orpheline de A et une de B.
  - Recalcul automatique en temps réel des KPIs et synchronisation avec l'export.
- **Export Excel Pro (4 feuilles)** :
  1. *Synthèse & KPIs* : Taux de rapprochement, montants totaux, écart net et paramètres.
  2. *Dossiers Rapprochés* : Lignes côte à côte avec badges de statut et écarts calculés.
  3. *Suspens Tableau A* : Lignes orphelines du premier fichier.
  4. *Suspens Tableau B* : Lignes orphelines du second fichier.
- **Modèles & Profils sectoriels prédéfinis** :
  - Modèles intégrés prêts à l'emploi : *CNAS vs Facturation*, *Banque vs Grand Livre*, *Factures vs Règlements*.
  - Reconnaissance automatique et intelligente des colonnes selon le profil sélectionné.
  - Sauvegarde de vos propres profils récurrents personnalisés.

## Démarrage rapide
1. Double-cliquez sur `setup_env.bat` (une seule fois pour installer l'environnement).
2. Lancez `run_app.bat` pour démarrer l'application.
