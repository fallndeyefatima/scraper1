# Scraper — Délibérations CCPA

## Objectif
Extraire les métadonnées des délibérations du Conseil Communautaire
des Pyrénées Audoises depuis :
https://www.pyreneesaudoises.fr/document-publics/délibérations-ccpa/délibérations-conseil-communautaire/

## Ce qu'on extrait
Pour chaque document PDF :
- Titre / nom du fichier
- Date (héritée du bloc h2/h3 parent)
- URL de téléchargement
- Type (ODJ, Délibération, Liste, PV)
- Identifiant (DC_YYYY_NNN)

## Problèmes rencontrés

### 403 Forbidden
Le site est hébergé sur Jimdo qui bloque les requêtes automatiques.
Solution : ajout de headers HTTP pour simuler un vrai navigateur.
Si le 403 persiste → fallback sur le fichier page.html sauvegardé localement.

### Noms de fichiers tronqués
Le nom affiché dans le HTML est tronqué visuellement.
Solution : extraire le vrai nom complet depuis l'URL de téléchargement.

### Date absente dans les fichiers
Les PDFs n'ont pas de date propre dans le HTML.
Solution : parcours séquentiel h2 (année) → h3 (mois) → date attribuée à chaque fichier du bloc.

### Numéros de délibération non uniformes
Les identifiants existent en plusieurs formats : DC_2025-109, dc-2026-012, DC_2025-021BIS
Solution : regex robuste qui gère les variantes (tirets/underscores/BIS).

## Structure du projet
scraper1/
├── venv/          # environnement virtuel Python
├── page.html      # HTML sauvegardé (fallback si 403)
├── test2.py       # script principal
├── resultats.csv  # fichier généré par le script
└── README.md      # ce fichier

## Comment lancer le script

# 1. Activer le venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 2. Installer les dépendances
pip install beautifulsoup4 requests

# 3. Lancer
python test2.py

## Résultat attendu
Status code : 200 (ou 403 → fallback local)
✅ X documents trouvés
✅ resultats.csv créé !
