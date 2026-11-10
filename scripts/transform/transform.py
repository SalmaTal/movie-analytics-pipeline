"""Nettoyage des fichiers JSONL TMDB bruts et transformation en Parquet par lots.

Le pipeline lit les données brutes stockées dans data/raw/movies/ et les transforme
en tables Parquet utilisables par la couche SQL. Ici, on centralise la logique de
validation et de normalisation :
- les champs TMDB sont convertis en types cohérents ;
- les valeurs "inconnues" (0, vide, null) sont standardisées ;
- les doublons sont éliminés avant écriture ;
- les partitions Parquet sont écrites par paquets pour tenir la mémoire.

Ce fichier est volontairement séparé des appels API : l'ingestion produit des JSONL,
la transformation les transforme en schémas prêts à être chargés.
"""

import json
import shutil
from datetime import date
from pathlib import Path

#pyarrow (pa, pq) sert à créer et écrire les fichiers Parquet.
import pyarrow as pa
import pyarrow.parquet as pq

# --- Dossiers ---------------------------------------------------------------
# __file__ est le chemin de ce fichier : .../scripts/transform/transform.py
# parents[2] remonte de deux dossiers (transform -> scripts -> racine du projet).
# On calcule les chemins à partir de ce fichier, et non du dossier courant,
# pour que le script marche d'où qu'on le lance.
# RAW est le dossier d’entrée, OUT celui de sortie, et BATCH_SIZE la taille d’un paquet.
ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "movies"
OUT = ROOT / "data" / "processed"
BATCH_SIZE = 1000

# --- Contrat de données -------------------------------------------------------
# Il s'agit d'un contrat entre la couche de transformation et la couche SQL : 
# les tables que Salma lira pour construire sa base SQL.
# Chaque table a un schéma explicite : nom de colonne + type PyArrow.
# Pour chaque tableau, on écrit la liste des colonnes et leur type : int64 pour un entier, string pour du texte, 
# date32 pour une date, float64 pour un décimal, bool_ pour vrai/faux. Ces types sont forcés à l’écriture,
#  cela évite des données incohérentes (texte au lieu de nombre, date non normalisée, entier de devenir 148.0. etc)

SCHEMAS = {
    "movies": pa.schema([
        ("id", pa.int64()),
        ("imdb_id", pa.string()),
        ("title", pa.string()),
        ("original_title", pa.string()),
        ("original_language", pa.string()),
        ("status", pa.string()),
        ("overview", pa.string()),
        ("tagline", pa.string()),
        ("homepage", pa.string()),
        ("release_date", pa.date32()),
        ("runtime", pa.int64()),
        ("budget", pa.int64()),
        ("revenue", pa.int64()),
        ("vote_average", pa.float64()),
        ("vote_count", pa.int64()),
        ("popularity", pa.float64()),
        ("adult", pa.bool_()),
        ("collection_id", pa.int64()),
    ]),
    "genres": pa.schema([
        ("id", pa.int64()),
        ("name", pa.string()),
    ]),
    "movie_genres": pa.schema([
        ("movie_id", pa.int64()),
        ("genre_id", pa.int64()),
    ]),
    "people": pa.schema([
        ("id", pa.int64()),
        ("name", pa.string()),
        ("gender", pa.int64()),
        ("known_for_department", pa.string()),
        ("popularity", pa.float64()),
    ]),
    "credits": pa.schema([
        ("credit_id", pa.string()),
        ("movie_id", pa.int64()),
        ("person_id", pa.int64()),
        ("type", pa.string()),          # "cast" ou "crew"
        ("character", pa.string()),
        ("order", pa.int64()),
        ("job", pa.string()),
        ("department", pa.string()),
    ]),
}


# --- Nettoyage des valeurs ----------------------------------------------------
# TMDB retourne souvent des valeurs "vides" ou ambiguës qui doivent être
# homogénéisées. L'idée est de convertir les JSON bruts en colonnes SQL lisibles,
# sans perdre la donnée utile, mais sans réintroduire les valeurs "0 = inconnu".


#Chez TMDB, un budget à 0 veut dire « on ne sait pas ». 
# On le remplace par None (case vide), pour ne pas fausser les moyennes.
def zero_to_none(v):
    return None if v in (0, None) else v


#strip() retire les espaces au début et à la fin. 
# v or None renvoie None si le texte est vide, sinon le texte.
def clean_text(v):
    if v is None:
        return None
    v = str(v).strip()
    return v or None

#"2010-07-15" devient une vraie date. Si la valeur est "" ou None, Python lève une erreur  
# le try/except l’attrape et renvoie None au lieu de faire planter tout le script.

def clean_date(v):
    try:
        return date.fromisoformat(v)
    except (TypeError, ValueError):
        return None


# --- Normalisation des objets métiers ------------------------------------------
# Chaque fonction prend un objet JSON d'un film et renvoie un dictionnaire prêt à
# être injecté dans une table Parquet. Le but est que les données soient déjà
# cohérentes avant même de passer dans PostgreSQL.

# Elle prend un film brut (un dictionnaire) et renvoie un dictionnaire avec seulement 
# les colonnes qu’on garde, nettoyées. raw.get("imdb_id") renvoie None si la clé n’existe pas,
#  alors que raw["id"] planterait : on utilise donc ["id"] seulement pour ce qui est obligatoire. 
# collection = raw.get("belongs_to_collection") or {} évite une erreur quand le film n’appartient
#  à aucune collection (valeur None).
def clean_movie(raw):
    collection = raw.get("belongs_to_collection") or {}
    return {
        "id": raw["id"],
        "imdb_id": clean_text(raw.get("imdb_id")),
        "title": clean_text(raw.get("title")),
        "original_title": clean_text(raw.get("original_title")),
        "original_language": clean_text(raw.get("original_language")),
        "status": clean_text(raw.get("status")),
        "overview": clean_text(raw.get("overview")),
        "tagline": clean_text(raw.get("tagline")),
        "homepage": clean_text(raw.get("homepage")),
        "release_date": clean_date(raw.get("release_date")),
        "runtime": zero_to_none(raw.get("runtime")),
        "budget": zero_to_none(raw.get("budget")),
        "revenue": zero_to_none(raw.get("revenue")),
        "vote_average": raw.get("vote_average"),
        "vote_count": raw.get("vote_count"),
        "popularity": raw.get("popularity"),
        "adult": raw.get("adult"),
        "collection_id": collection.get("id"),
    }

#Un film contient des listes (genres, casting). Une base SQL veut des lignes séparées. 
# Ces fonctions parcourent les listes et créent une ligne par genre, ou par poste.

# la fonction  extract_genres() parcourt la liste des genres d’un film et renvoie deux listes :
# - les liens film-genre (une ligne par genre)
# - les genres rencontrés (une ligne par genre, avec id et nom)


def extract_genres(raw):
    links, genres = [], []
    for g in raw.get("genres") or []:
        links.append({"movie_id": raw["id"], "genre_id": g["id"]})
        genres.append({"id": g["id"], "name": clean_text(g.get("name"))})
    return links, genres

# la fonction  extract_credits() parcourt les listes de casting et d’équipe technique d’un film et renvoie deux listes :
# - les crédits (une ligne par poste, avec credit_id, movie_id, person_id, type, character, order, job, department)
# - les personnes rencontrées (une ligne par personne, avec id, name, gender, known_for_department, popularity) 

def extract_credits(raw):
    credits, people = [], []
    block = raw.get("credits") or {}
    for kind in ("cast", "crew"):
        for p in block.get(kind) or []:
            credits.append({
                "credit_id": p["credit_id"],
                "movie_id": raw["id"],
                "person_id": p["id"],
                "type": kind,
                "character": clean_text(p.get("character")),
                "order": p.get("order"),
                "job": clean_text(p.get("job")),
                "department": clean_text(p.get("department")),
            })
            people.append({
                "id": p["id"],
                "name": clean_text(p.get("name")),
                "gender": zero_to_none(p.get("gender")),   # 0 = non renseigné
                "known_for_department": clean_text(p.get("known_for_department")),
                "popularity": p.get("popularity"),
            })
    return credits, people


# --- Lecture des JSONL par lots ------------------------------------------------
# On ne lit pas tout un fichier d'un coup : on lit des sous-ensembles de 1000 lignes,
# on les transforme, puis on les écrit. Cette approche est plus sûre et plus scalable
# qu'un chargement complet en mémoire, surtout avec des jeux de données de plusieurs Mo.

def read_batches(path, size):
    """Lit le fichier par paquets de `size` lignes (jamais tout en mémoire)."""
    batch = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            batch.append(json.loads(line))
            if len(batch) == size:
                yield batch
                batch = []
    if batch:
        yield batch


# --- Écriture Parquet ----------------------------------------------------------
# Chaque partition est écrite dans un dossier dédié :
# data/processed/movies/part-0000.parquet, etc.
# Cela évite d'écraser un fichier existant et permet de charger ensuite les tables
# par morceaux dans PostgreSQL ou dans d'autres outils.
def write_parquet(name, rows, part):
    if not rows:
        return
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=SCHEMAS[name])
    pq.write_table(table, folder / f"part-{part:04d}.parquet")


#---main ----------------------------------------------------------------
def main():
    # Il supprime d’abord les anciens dossiers de sortie, pour repartir propre, mais sans toucher à data/processed/.gitkeep.
    # Cela évite de conserver des anciennes partitions quand on relance le script sur
    # un périmètre différent ou après un correctif de transformation.
    for name in SCHEMAS:
        shutil.rmtree(OUT / name, ignore_errors=True)

    # Les trois sets servent à éliminer les doublons entre années et entre
    # plusieurs films ayant les mêmes ids ou personnes/genres. Les ensembles sont
    # beaucoup plus rapides qu'une recherche exhaustive dans chaque liste.
    # Un set répond instantanément à « ai-je déjà vu cet id ? ».
    seen_movies, seen_people, seen_genres = set(), set(), set()
    genres_rows = []
    part = 0
    for path in sorted(RAW.glob("year=*.jsonl")):
        for batch in read_batches(path, BATCH_SIZE):
            movies, links, credits, people = [], [], [], []
            for raw in batch:
                if raw["id"] in seen_movies:          # doublon : on ignore
                    continue
                seen_movies.add(raw["id"])
                movies.append(clean_movie(raw))

                film_links, film_genres = extract_genres(raw)
                links += film_links
                for g in film_genres:
                    if g["id"] not in seen_genres:
                        seen_genres.add(g["id"])
                        genres_rows.append(g)

                film_credits, film_people = extract_credits(raw)
                credits += film_credits
                for person in film_people:
                    if person["id"] not in seen_people:
                        seen_people.add(person["id"])
                        people.append(person)

            # On écrit chaque table dans le même lot, de façon cohérente :
            # les lignes du film, ses genres, ses crédits et les personnes associées
            # doivent être produites ensemble, même si par la suite elles seront
            # chargées séparément dans PostgreSQL.
            write_parquet("movies", movies, part)
            write_parquet("movie_genres", links, part)
            write_parquet("credits", credits, part)
            write_parquet("people", people, part)
            part += 1

    # Les genres sont écrits à la fin parce qu'on ne veut garder qu'une seule ligne
    # par genre global (id + nom), pas une copie pour chaque film.
    write_parquet("genres", genres_rows, 0)
    print(f"Terminé : {len(seen_movies)} films, {len(seen_genres)} genres, "
          f"{len(seen_people)} personnes")


if __name__ == "__main__":
    main()