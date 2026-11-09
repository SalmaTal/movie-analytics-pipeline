# Movie Analytics Pipeline

Pipeline de données sur les films : collecte depuis l'API [TMDB](https://www.themoviedb.org/), nettoyage, stockage dans PostgreSQL, puis publication d'un dataset sur le Hugging Face Hub.

Projet de groupe de la formation **Data Engineer expert en IA** (Ynov) : Ndeye Aida NDOUR, Yannis STAALI, Salma TALIB.

## Le pipeline

```
API TMDB ──▶ data/raw/          ──▶ data/processed/  ──┬──▶ PostgreSQL
             JSON Lines bruts       Parquet nettoyé    └──▶ Hugging Face Hub
   ① Ingestion            ② Transformation      ③ Base SQL    ④ Publication
```

| Étape | Dossier | État |
|---|---|---|
| ① Ingestion | `scripts/ingest/` | En cours : échantillon de 200 films disponible |
| ② Transformation | `scripts/transform/` | À venir |
| ③ Base SQL | `sql/`, `scripts/load/` | À venir |
| ④ Publication | `scripts/publish/` | À venir |

## Périmètre des données

| Réglage | Valeur |
|---|---|
| Films | sortis de 2000 à 2026, avec au moins 50 votes sur TMDB |
| Volume attendu | ~24 000 films (environ 900 par an) |
| Langue des textes | anglais (`en-US`) |
| Contenu d'un film | fiche complète : dates, durée, budget, recettes, notes, genres, sociétés, pays, casting et équipe technique |

## Données disponibles

**Pour la transformation, le fichier à utiliser est [`data/raw/movies/year=2010.jsonl`](data/raw/movies/year=2010.jsonl).** Une ligne = la fiche complète d'un film. Il contient pour l'instant un échantillon de **200 films** (janvier à mars 2010).

| Fichier | Une ligne = | Utilisé par |
|---|---|---|
| `data/raw/movies/year=AAAA.jsonl` | la fiche complète d'un film, casting compris | la transformation |
| `data/raw/discover/year=AAAA.jsonl` | une page de la liste des films (résumés) | l'ingestion seulement |

Mode d'emploi, lecture en Python et pièges à connaître : **[data/raw/README.md](data/raw/README.md)**.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1            # macOS / Linux : source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                # macOS / Linux : cp .env.example .env
```

Dans `.env`, renseigner la clé de l'API TMDB (gratuite, à demander sur [themoviedb.org](https://www.themoviedb.org/settings/api)) :

```
TMDB_API_KEY=ta_cle
```

Le fichier `.env` n'est jamais versionné.

## Utilisation

### ① Ingestion

```powershell
python -m scripts.ingest.fetch_sync
```

Récupère les films de 2010 (année et taille de l'échantillon réglables en bas du script) :

1. la liste des films, mois par mois, avec `/discover/movie`, dans `data/raw/discover/` ;
2. la fiche complète de chaque film avec `/movie/{id}`, dans `data/raw/movies/`.

Chaque lancement repart de zéro pour l'année demandée. La version asynchrone (plus rapide, avec reprise après interruption) est en cours.

Les étapes suivantes seront documentées ici au fur et à mesure.

## Structure du dépôt

```
movie-analytics-pipeline/
├── scripts/
│   ├── ingest/
│   │   ├── config.py        # clé API, périmètre, dossiers
│   │   └── fetch_sync.py    # ingestion (version synchrone)
│   ├── transform/           # nettoyage → Parquet
│   ├── load/                # chargement dans PostgreSQL
│   └── publish/             # publication sur Hugging Face
├── sql/                     # schéma, requêtes d'analyse, index
├── data/
│   ├── raw/                 # réponses brutes de TMDB (versionnées)
│   └── processed/           # données nettoyées (non versionnées)
├── tests/                   # tests pytest
└── docs/                    # documentation du projet
```

## Documentation

- **[docs/index.html](docs/index.html)** : la doc du projet (étapes, API TMDB, cadrage). À ouvrir dans un navigateur.
- **[docs/note_exploration.md](docs/note_exploration.md)** : ce que l'ingestion récupère, champ par champ.
- **[docs/HISTORIQUE.md](docs/HISTORIQUE.md)** : l'avancement et les décisions.

## Licence et attribution

This product uses the TMDB API but is not endorsed or certified by TMDB.

Les données proviennent de TMDB et sont soumises à ses [conditions d'utilisation](https://www.themoviedb.org/api-terms-of-use) (usage non commercial, attribution obligatoire).
