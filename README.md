# Movie Data analytics pipeline
Un projet scolaire réalisé par :
Ndeye Aida NDOUR
Yannis STAALI
Salma TALIB
formation Data Engineer expert en IA (Ynov)

Dataset publié : <lien vers le dépôt Hugging Face>

Construction de Pipeline de données complet : collecte de métadonnées de films depuis l'API TMDB, transformation, stockage dans une base SQL, puis publication d'un dataset sur le Hugging Face Hub.


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
### 1. Ingestion (API TMDB → data/raw/)
python -m scripts.ingest.fetch_movies --years 2010 --max-pages 5

- `--years` : une ou plusieurs années (`--years 2010 2011 2012`)
- `--max-pages` : pages `/discover/movie` par année, 20 films par page (5 pages = 100 films, max 500)
- `--concurrency` : requêtes simultanées (sémaphore, 20 par défaut)

Fichiers produits :
- `data/raw/discover/year=YYYY.jsonl` : une ligne par page de résultats
- `data/raw/movies/year=YYYY.jsonl` : une ligne par film (fiche + casting)
- `data/raw/checkpoints/movies_YYYY.txt` : ids déjà traités

En cas d'interruption, relancer la même commande : les pages et films déjà récupérés sont sautés.

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
