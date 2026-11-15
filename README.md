# Movie Analytics Pipeline

Pipeline de données complet sur les films : collecte asynchrone depuis l'API [TMDB](https://www.themoviedb.org/), nettoyage en Parquet, stockage dans PostgreSQL et publication d'un dataset sur le Hugging Face Hub.

Projet de groupe, formation **Data Engineer expert en IA** (Ynov) : Ndeye Aida NDOUR, Yannis STAALI, Salma TALIB.

**Dataset publié :** [NdeyeAidaNdour/tmdb-movies-2000-2026](https://huggingface.co/datasets/NdeyeAidaNdour/tmdb-movies-2000-2026) (public, tag `v1.0.0`)

```
API TMDB ──▶ data/raw/        ──▶ data/processed/ ──┬──▶ PostgreSQL
             JSON Lines bruts     Parquet nettoyé   └──▶ Hugging Face Hub
  ① Ingestion          ② Transformation       ③ Base SQL    ④ Publication
```

## En chiffres

| | |
|---|---|
| Périmètre | films sortis de **2000 à 2026** (2026 incomplète), **au moins 50 votes**, textes en anglais |
| Films | **25 389** (de 422 en 2000 à 1 452 en 2018) |
| Données brutes | 589 Mo de JSON Lines, 27 fichiers (un par année) |
| Données nettoyées | 81 Mo de Parquet, 5 tableaux, **2 675 072 lignes** |
| Transformation | environ 33 s, environ 400 Mo de RAM au maximum |
| Tests | 25 tests pytest (17 ingestion, 8 transformation) |

## Les 4 étapes

| Étape | Code | Ce qu'elle fait |
|---|---|---|
| ① Ingestion | [`scripts/ingest/`](scripts/ingest/) | `aiohttp`, 20 requêtes en parallèle (sémaphore), timeout de 15 s, 5 essais avec attente exponentielle, JSON Lines `year=AAAA.jsonl`, reprise par année (fichier `.part`) |
| ② Transformation | [`scripts/transform/`](scripts/transform/) | lecture par lots de 1 000 films, nettoyage (`0` « inconnu » → vide, dates typées, doublons), 5 tableaux Parquet |
| ③ Base SQL | [`sql/`](sql/), [`scripts/load/`](scripts/load/) | schéma avec clés et contraintes, chargement relançable sans doublons (`COPY` + `INSERT … ON CONFLICT`), 5 analyses (jointures, `GROUP BY`, CTE, window functions), index mesuré par `EXPLAIN ANALYZE` |
| ④ Publication | [`scripts/publish/`](scripts/publish/) | envoi des Parquet et de la Dataset Card sur le Hub, version taguée |

**Les tables :** `movies` (25 389), `genres` (19), `movie_genres` (60 263), `people` (674 561), `credits` (1 914 840). Leurs colonnes sont décrites dans [docs/note_transformation.md](docs/note_transformation.md).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # puis renseigner TMDB_API_KEY (et HF_TOKEN pour publier)
```

Les secrets restent dans `.env`, et `data/` n'est jamais versionné : les données se régénèrent avec les commandes ci-dessous.

## Utilisation

```bash
# ① Ingestion : 2000 à 2026 ; relancer reprend là où ça s'est arrêté
python -m scripts.ingest.fetch_async

# ② Transformation, puis tests
python -m scripts.transform.transform
python -m pytest

# ③ Base SQL : PostgreSQL sur localhost:5433, base movie_analytics, utilisateur postgres
psql -h localhost -p 5433 -U postgres -d movie_analytics -f sql/schema.sql
python scripts/load/load_all_parquet.py        # demande le mot de passe
psql -h localhost -p 5433 -U postgres -d movie_analytics -f sql/analyses.sql
psql -h localhost -p 5433 -U postgres -d movie_analytics -f sql/benchmark.sql

# ④ Publication (jeton Hugging Face Write dans .env)
python scripts/publish/publish.py --tag v1.0.0
```

> Sur un réseau d'entreprise, le proxy peut bloquer TMDB : il faut lancer l'ingestion depuis une autre connexion.
> La procédure complète pour tout relancer depuis zéro, avec les valeurs attendues, est dans [docs/TEST_VPS.md](docs/TEST_VPS.md).

## Structure

```
├── scripts/
│   ├── ingest/      # ① config.py, fetch_async.py (fetch_sync.py : version simple, pour comparaison)
│   ├── transform/   # ② transform.py
│   ├── load/        # ③ load_all_parquet.py
│   └── publish/     # ④ publish.py, dataset_card.md
├── sql/             # schema.sql, analyses.sql, benchmark.sql
├── data/
│   ├── raw/         # JSON Lines bruts (non versionnés)
│   └── processed/   # Parquet (non versionnés)
├── tests/           # test_ingest.py, test_transform.py
└── docs/            # documentation
```

## Documentation

- [docs/index.html](docs/index.html) : le site du projet (étapes, API TMDB, cadrage, lexique), à ouvrir dans un navigateur
- [docs/note_exploration.md](docs/note_exploration.md) : les champs récupérés sur TMDB
- [data/raw/README.md](data/raw/README.md) : le format des données brutes et ses pièges
- [docs/note_transformation.md](docs/note_transformation.md) : les tableaux Parquet, avec leurs colonnes et leurs types
- [docs/note_cenception_sql.md](docs/note_cenception_sql.md) : la base SQL, les analyses et l'index
- [docs/HISTORIQUE.md](docs/HISTORIQUE.md) : le journal des avancées et des décisions

## Licence et attribution

This product uses the TMDB API but is not endorsed or certified by TMDB.

Les données proviennent de TMDB et sont soumises à ses [conditions d'utilisation](https://www.themoviedb.org/api-terms-of-use) : usage non commercial, attribution obligatoire. Le dataset est publié pour un usage pédagogique.
