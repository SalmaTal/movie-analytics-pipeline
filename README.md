# Movie Data analytics pipeline
Un projet scolaire réalisé par :
Ndeye Aida NDOUR
Yannis STAALI
Salma TALIB
formation Data Engineer expert en IA (Ynov)

Dataset publié : <lien vers le dépôt Hugging Face>

Construction de Pipeline de données complet : collecte de métadonnées de films depuis l'API TMDB, transformation, stockage dans une base SQL, puis publication d'un dataset sur le Hugging Face Hub.

## Données disponibles pour la transformation

**Le fichier à utiliser : [`data/raw/movies/year=2010.jsonl`](data/raw/movies/year=2010.jsonl)**

- **Une ligne = la fiche complète d'un film**, casting compris (réponse brute de `/movie/{id}?append_to_response=credits`).
- **Contenu actuel :** un échantillon de **200 films** sortis de janvier à mars 2010, avec au moins 50 votes, en anglais.
- **Pour le récupérer :** `git pull`.
- `data/raw/discover/` ne sert qu'à l'ingestion (la liste des ids) : pas besoin pour la transformation.

**Les pièges principaux :**

- `budget`, `revenue` et `runtime` valent `0` quand ils sont inconnus (56 % des budgets de l'échantillon) ;
- `release_date` est du texte ;
- dans `credits.crew`, une même personne peut avoir plusieurs postes ;
- il faut dédoublonner sur `id`.

Le mode d'emploi complet (lecture en Python, contenu d'une fiche, tous les pièges) est dans **[data/raw/README.md](data/raw/README.md)**. Le détail de chaque champ est dans [docs/note_exploration.md](docs/note_exploration.md).

**La suite :** même format, un fichier par année de `year=2000.jsonl` à `year=2026.jsonl` (~24 000 films), dès que la version rapide de l'ingestion sera prête.


## Architecture
API TMDB(ingestion asynchrone)  ──▶ data/raw (JSON Lines)──▶ data/processed/(Parquet )──► Base SQL (PostgreSQL)──▶ Hugging Face Hub


## Structure du dépôt
movie_analytics_pipeline/
├── sql/ # Requêtes SQL
├── scripts/
│ ├── ingest/ # Collecte asynchrone
│ └── transform/ # Transformations
├── data/
│ ├── raw/ # Données brutes, jamais modifiées
│ └── processed/ # Données propres (Parquet)
├── tests/ # Tests pytest
└── README.md # Documentation et Dataset Card

Les dossiers data/raw/ et data/processed/ ne sont pas versionnés dans Git (voir .gitignore).


## Prérequis et installation
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # puis renseigner les valeurs


## Configuration
...

## Utilisation
...

## Tests
pytest

## Données et analyses
Source : API TMDB (/discover/movie, /movie/{id})
Période couverte : <à compléter>
Volume : <nombre de films, de lignes par table>
Fréquence de mise à jour : <à compléter>
...
## Licence et attribution
This product uses the TMDB API but is not endorsed or certified by TMDB.
Licence de la source : conditions d'utilisation de l'API TMDB (usage non commercial), <à confirmer avant publication>
Licence du dataset : <à compléter>
Licence du code : <à compléter>

...

## Dataset Card


## Limites et pistes d'amélioration
