# Tester tout le pipeline sur un VPS, depuis zéro

But : partir d'un serveur vide, cloner le dépôt et relancer **toutes** les étapes (ingestion → transformation → tests → PostgreSQL → analyses → index → Hub), pour vérifier que tout marche et noter les chiffres mesurés.

Pourquoi le VPS : il sort sur Internet sans proxy (le réseau Thales bloque TMDB), et c'est l'endroit prévu pour la mise en production (idée Airflow).

> Les commandes sont pour un VPS **Linux (Debian / Ubuntu)**. Elles se lancent depuis la racine du dépôt cloné, sauf mention contraire.

---

## 0. Prérequis sur le VPS

```bash
sudo apt update
sudo apt install -y git python3 python3-venv time   # time : pour mesurer durée et RAM
```

**PostgreSQL :** le plus simple est **Docker**, qui servira aussi pour Airflow. Si Docker n'est pas installé : <https://docs.docker.com/engine/install/> (Docker Engine, gratuit sous Linux).

Il faut aussi :
- la **clé TMDB** (v3) ;
- environ **2 Go d'espace disque** (600 Mo de JSON, 80 Mo de Parquet, la base PostgreSQL) ;
- au moins **1 Go de RAM libre** (la transformation monte à environ 400 Mo).

---

## 1. Page blanche : cloner le dépôt

```bash
git clone https://github.com/SalmaTal/movie-analytics-pipeline.git
cd movie-analytics-pipeline
ls data/raw data/processed        # doit montrer seulement .gitkeep (et README.md dans raw)
```

Comme `data/` n'est plus versionné, un clone neuf part **sans aucune donnée** : c'est la page blanche.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env                         # renseigner TMDB_API_KEY=... (rien d'autre pour l'instant)
python -m scripts.ingest.config   # doit afficher « Clé TMDB trouvée : xxxx… »
```

**À vérifier :** `pip install` se termine sans erreur ; la clé est trouvée.

---

## 2. Ingestion (étape ①)

```bash
/usr/bin/time -v python -m scripts.ingest.fetch_async 2>&1 | tee ingestion.log
```

`/usr/bin/time -v` affiche à la fin la durée (`Elapsed (wall clock) time`) et la RAM maximale (`Maximum resident set size`, en Ko). `tee` garde une copie de l'affichage dans `ingestion.log`.

**À vérifier :**
- 27 fichiers `data/raw/movies/year=AAAA.jsonl` (2000 à 2026) et aucun `.part` restant :
  ```bash
  ls data/raw/movies | wc -l                 # 27
  ls data/raw/movies/*.part 2>/dev/null      # rien
  ```
- le nombre de films et d'erreurs par année, dans les lignes `AAAA : N fiches écrites ..., 0 erreurs` ;
- le total :
  ```bash
  cat data/raw/movies/*.jsonl | wc -l
  ```

**Attendu :** environ **25 389 films**, valeur du 2026-11-09. TMDB évolue, donc le total sera un peu différent : des films passent la barre des 50 votes, surtout en 2025-2026. Un écart de quelques centaines est normal.

**Test de la reprise (checkpoint)** : relancer la même commande. Toutes les années doivent afficher `déjà récupérée, on passe`, et le script doit finir en quelques secondes.

À noter : **durée**, **RAM max**, **nombre de films**, **taille** (`du -sh data/raw`).

---

## 3. Transformation (étape ②)

```bash
/usr/bin/time -v python -m scripts.transform.transform 2>&1 | tee transform.log
```

**À vérifier :** 5 dossiers dans `data/processed/` (`movies`, `genres`, `movie_genres`, `people`, `credits`) remplis de fichiers `.parquet`.

```bash
python -c "
import pyarrow.dataset as ds
for t in ['movies','genres','movie_genres','people','credits']:
    print(t, ds.dataset(f'data/processed/{t}').count_rows())
"
```

**Attendu** (valeurs du 2026-11-12, à quelques écarts près si l'ingestion a ramené un nombre de films différent) :

| Tableau | Lignes |
|---|---|
| movies | 25 389 |
| genres | 19 |
| movie_genres | 60 263 |
| people | 674 561 |
| credits | 1 914 840 |

À noter : **durée** (référence : environ 33 s), **RAM max** (référence : environ 400 Mo), **taille** (`du -sh data/processed`, référence : environ 80 Mo).

---

## 4. Tests pytest

```bash
python -m pytest -v
```

**Attendu :** **25 tests passent** (17 d'ingestion, 8 de transformation). Les tests n'appellent pas TMDB et ne touchent pas à `data/` : ils écrivent dans un dossier temporaire. Ils peuvent donc se lancer avant l'ingestion, sur un clone neuf.

---

## 5. Base PostgreSQL (étape ③)

Le script de chargement a ses réglages **écrits en dur** : `localhost`, port **5433**, utilisateur `postgres`, base `movie_analytics`, et le mot de passe demandé au clavier. On crée donc la base avec exactement ces réglages.

### 5.1 Lancer PostgreSQL

```bash
docker run -d --name tmdb-postgres \
  -e POSTGRES_PASSWORD='choisis_un_mot_de_passe' \
  -e POSTGRES_DB=movie_analytics \
  -p 127.0.0.1:5433:5432 \
  -v tmdb-pgdata:/var/lib/postgresql/data \
  postgres:16
```

- `-p 127.0.0.1:5433:5432` : le port 5433 n'est ouvert **que sur le VPS lui-même**, pas sur Internet. C'est important sur un serveur public.
- `-v tmdb-pgdata:...` : les données de la base survivent à un redémarrage du conteneur.
- `POSTGRES_DB` crée la base `movie_analytics` directement : c'est l'étape « créer la base » qui n'était documentée nulle part.

Raccourci pour lancer `psql` dans le conteneur, à utiliser dans la suite :

```bash
alias psqlt='docker exec -i tmdb-postgres psql -U postgres -d movie_analytics'
```

### 5.2 Créer le schéma et les tables

```bash
psqlt < sql/schema.sql
psqlt -c '\dt pipeline.*'          # doit lister les 5 tables
```

### 5.3 Charger les Parquet, deux fois

```bash
/usr/bin/time -v python scripts/load/load_all_parquet.py 2>&1 | tee load1.log
python scripts/load/load_all_parquet.py 2>&1 | tee load2.log
```

Le mot de passe demandé est celui du `docker run`.

**À vérifier :**
- au 1er lancement, chaque table affiche `N lignes traitées ; N lignes en base` avec les mêmes chiffres qu'à l'étape 3 (total de référence : **2 675 072 lignes**) ;
- au **2e lancement**, les nombres « en base » sont **identiques** au 1er : c'est la preuve que le chargement peut être relancé sans doublons (exigence de la fiche).

```bash
psqlt -c "SELECT 'movies', COUNT(*) FROM pipeline.movies
          UNION ALL SELECT 'credits', COUNT(*) FROM pipeline.credits;"
```

À noter : **durée** et **RAM max** du chargement.

---

## 6. Analyses SQL

```bash
psqlt < sql/analyses.sql
```

**À vérifier :** les 5 requêtes renvoient des résultats, sans erreur : top recettes, note par genre, top 5 par année, réalisateurs, recettes annuelles avec l'écart d'une année sur l'autre.

---

## 7. Index justifié par EXPLAIN ANALYZE

```bash
psqlt < sql/benchmark.sql > benchmark1.txt
psqlt < sql/benchmark.sql > benchmark2.txt     # garder cette 2e mesure (cache chaud)
grep -E "Seq Scan|Index Scan|Bitmap|Execution Time" benchmark2.txt
```

**Attendu :**
- **avant l'index** : `Seq Scan` (ou `Parallel Seq Scan`) sur `credits`, PostgreSQL lit toute la table ;
- **après l'index** : `Index Scan` ou `Bitmap Index Scan` sur `idx_credits_person_id` ;
- un `Execution Time` **nettement plus bas** après l'index : la requête ne vise que 57 lignes sur 1,9 million.

À noter : les deux `Execution Time`, à reporter dans `docs/note_cenception_sql.md` à la place de l'ancienne mesure sur `credits(job)`.

---

## 8. Hub Hugging Face (étape ④) : lecture seulement

On **ne relance pas** `publish.py` : il enverrait les fichiers sur le dataset public d'Aida. On vérifie seulement que le dataset publié existe et se lit.

```bash
python -c "
from huggingface_hub import HfApi
api = HfApi()
repo = 'NdeyeAidaNdour/tmdb-movies-2000-2026'
info = api.dataset_info(repo)
print('privé :', info.private)
print('tags  :', [t.name for t in api.list_repo_refs(repo, repo_type='dataset').tags])
files = api.list_repo_files(repo, repo_type='dataset')
print('fichiers parquet :', sum(f.endswith('.parquet') for f in files))
print('README (Dataset Card) :', 'README.md' in files)
"
```

**Attendu :** `privé : False`, tag `v1.0.0`, **153** fichiers Parquet, `README.md` présent. Le dataset étant public, aucun jeton n'est nécessaire.

---

## 9. Récapitulatif à remplir

| Étape | Commande | OK ? | Chiffres mesurés |
|---|---|---|---|
| ① Ingestion | `fetch_async` | | films : … · durée : … · RAM : … · taille : … |
| ① Reprise | `fetch_async` relancé | | années sautées : …/27 |
| ② Transformation | `transform` | | durée : … · RAM : … · taille : … |
| Tests | `pytest` | | … / 25 |
| ③ Schéma | `schema.sql` | | 5 tables : … |
| ③ Chargement ×2 | `load_all_parquet.py` | | lignes : … · durée : … · identique au 2e : … |
| ③ Analyses | `analyses.sql` | | 5 requêtes : … |
| ③ Index | `benchmark.sql` (2e passage) | | sans : … ms · avec : … ms |
| ④ Hub | lecture | | public, v1.0.0, 153 Parquet : … |

---

## Points faibles connus (à garder en tête pendant le test)

- **Réglages de connexion en dur** dans `load_all_parquet.py` (`localhost`, `5433`, `postgres`) et mot de passe demandé au clavier : impossible à lancer sans personne devant, donc bloquant pour une automatisation (Airflow). Il faudrait lire `DATABASE_URL` dans `.env`, comme `.env.example` le prévoit déjà.
- **Le README ne documente pas l'étape ③** (il indique « À venir ») : les commandes de la section 5 ci-dessus pourraient y être reprises.
- **`publish.py` crée le dépôt en `private=True`** alors que le dataset est maintenant public. `exist_ok=True` ne change pas la visibilité d'un dépôt existant, donc sans effet aujourd'hui. Mais si quelqu'un publie sous un autre compte, son dataset sera privé.
