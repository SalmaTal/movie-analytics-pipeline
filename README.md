# Movie Analytics Pipeline

Pipeline de données sur les films : collecte depuis l'API [TMDB](https://www.themoviedb.org/), nettoyage, stockage dans PostgreSQL, puis publication d'un dataset sur le Hugging Face Hub.

Projet de groupe de la formation **Data Engineer expert en IA** (Ynov) : Ndeye Aida NDOUR, Yannis STAALI, Salma TALIB.

## Explication ingestion

Salut ! Voilà ce qu'il faut savoir pour attaquer la transformation :

- **Tes données sont dans [`data/raw/movies/`](data/raw/movies/)**. Il y a un fichier par année, de `year=2000.jsonl` à `year=2026.jsonl`, soit 25 389 films en tout. Chaque ligne, c'est la fiche complète d'un film, casting compris. C'est tout ce dont tu as besoin.
- **Le dossier [`data/raw/discover/`](data/raw/discover/), tu peux l'ignorer.** C'est juste la liste des films telle que TMDB nous l'a envoyée, page par page. Elle a servi à trouver les ids des films, et on la garde comme trace de la collecte.
- **Le script qui a récupéré les données, c'est [`scripts/ingest/fetch_async.py`](scripts/ingest/fetch_async.py).** `fetch_sync.py`, c'est la première version, plus lente, qui m'a servi à tester et à comprendre chaque étape. `config.py` contient les réglages : années, seuil de votes, langue.
- **Avant de te lancer, lis [`data/raw/README.md`](data/raw/README.md)** : comment lire les fichiers en Python, et les pièges à connaître (les `0` qui veulent dire « inconnu », les dates en texte, etc.).
- **Conseil :** commence par une seule année, par exemple `year=2010.jsonl`, et lis les fichiers ligne par ligne plutôt que tout charger d'un coup.

Si un truc n'est pas clair, demande-moi !

## Le pipeline

```
API TMDB ──▶ data/raw/          ──▶ data/processed/  ──┬──▶ PostgreSQL
             JSON Lines bruts       Parquet nettoyé    └──▶ Hugging Face Hub
   ① Ingestion            ② Transformation      ③ Base SQL    ④ Publication
```

| Étape | Dossier | État |
|---|---|---|
| ① Ingestion | `scripts/ingest/` | Collecte complète : 25 389 films de 2000 à 2026 ; tests en cours |
| ② Transformation | `scripts/transform/` | Faite : 25 389 films → 5 tableaux Parquet ; 8 tests pytest |
| ③ Base SQL | `sql/`, `scripts/load/` | À venir |
| ④ Publication | `scripts/publish/` | Faite : dataset privé sur le Hub, Dataset Card, tag v1.0.0 |

## Périmètre des données

| Réglage | Valeur |
|---|---|
| Films | sortis de 2000 à 2026, avec au moins 50 votes sur TMDB |
| Volume | **25 389 films** (de 422 en 2000 à 1 452 en 2018 ; 2026 incomplète), ~600 Mo de JSON bruts |
| Langue des textes | anglais (`en-US`) |
| Contenu d'un film | fiche complète : dates, durée, budget, recettes, notes, genres, sociétés, pays, casting et équipe technique |

## Données disponibles

**Pour la transformation, les fichiers à utiliser sont [`data/raw/movies/`](data/raw/movies/)`year=AAAA.jsonl`**, un par année de 2000 à 2026. Une ligne = la fiche complète d'un film.

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
python -m scripts.ingest.fetch_async
```

Récupère tous les films de 2000 à 2026 (années et taille d'échantillon réglables en bas du script). Pour chaque année :

1. la liste des films, mois par mois, avec `/discover/movie`, dans `data/raw/discover/` ;
2. la fiche complète de chaque film avec `/movie/{id}`, dans `data/raw/movies/`.

**Reprise après coupure :** une année terminée n'est jamais refaite. Si le script s'arrête, il suffit de le relancer : il saute les années déjà récupérées et refait l'année interrompue. Pour refaire une année, il faut supprimer son fichier `data/raw/movies/year=AAAA.jsonl`.

Le script est **asynchrone** (`aiohttp`) : jusqu'à 20 requêtes en même temps, limitées par un sémaphore. Une requête qui échoue de façon passagère (429, 5xx, délai de 15 s dépassé) est retentée jusqu'à 5 fois, avec une attente qui double à chaque essai (1 s, 2 s, 4 s, 8 s).

`fetch_sync.py` est la version simple, une requête à la fois, gardée pour comparaison.

Les étapes suivantes seront documentées ici au fur et à mesure.
### ② Transformation

```bash
python -m scripts.transform.transform
pytest
```

Lit `data/raw/movies/` par lots de 1 000 films, nettoie (0 « inconnus » devenus vides, dates typées, textes vides, doublons) et écrit 5 tableaux Parquet dans `data/processed/` : `movies`, `genres`, `movie_genres`, `people`, `credits`. Les colonnes et types sont décrits dans [docs/note_transformation.md](docs/note_transformation.md).

**Mesuré sur 25 389 films :** environ 33 s, environ 400 Mo de RAM au maximum, 589 Mo de JSON bruts pour XX Mo de Parquet.

`data/processed/` n'est pas versionné : après un `git pull`, il se régénère avec la commande ci-dessus.

### ④ Publication

```bash
python scripts/publish/publish.py                # envoie les Parquet et la Dataset Card (dépôt privé)
python scripts/publish/publish.py --tag v1.0.0   # pose le tag de version
```

Il faut un jeton Hugging Face de type Write dans `.env` (`HF_TOKEN=...`). Le dépôt est **privé** pendant le développement. Il peut etre changé en organisation et / ou public. La Dataset Card est écrite dans `scripts/publish/dataset_card.md` et envoyée comme `README.md` du dépôt. Le script peut être relancé sans danger : les fichiers identiques ne sont pas renvoyés.

**Mesuré :** 589 Mo de JSON bruts, environ 81 Mo de Parquet (153 fichiers).

## Structure du dépôt

```
movie-analytics-pipeline/
├── scripts/
│   ├── ingest/
│   │   ├── config.py        # clé API, périmètre, dossiers
│   │   ├── fetch_async.py   # ingestion (asynchrone) : le script à lancer
│   │   └── fetch_sync.py    # ingestion (version simple, une requête à la fois)
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
- **[docs/note_transformation.md](docs/note_transformation.md)** : les tableaux Parquet produits, colonnes et types.

## Licence et attribution

This product uses the TMDB API but is not endorsed or certified by TMDB.

Les données proviennent de TMDB et sont soumises à ses [conditions d'utilisation](https://www.themoviedb.org/api-terms-of-use) (usage non commercial, attribution obligatoire).
