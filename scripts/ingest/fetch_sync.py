"""Version simple de l'ingestion : une requête à la fois (synchrone).

Elle sert à comprendre chaque morceau, puis de point de comparaison
pour mesurer le gain de la version asynchrone.

Étape 2 : récupérer la fiche d'un film et l'écrire dans un fichier JSON Lines.
Étape 3 : récupérer la liste des films d'une année avec /discover/movie,
          mois par mois et triée par date de sortie (un tri stable).

Usage :
    python -m scripts.ingest.fetch_sync
"""
import calendar
import json

import requests

from scripts.ingest import config

TMDB_MAX_PAGES = 500  # TMDB refuse les pages au-delà de 500 pour une même recherche


def get_json(path, params=None):
    """Envoie une requête GET à TMDB et renvoie la réponse sous forme de dictionnaire.

    path   : la fin de l'adresse, par exemple "/movie/27205"
    params : les paramètres propres à cet appel (en plus de la clé et de la langue)
    """
    # Les paramètres communs à TOUS les appels...
    all_params = {"api_key": config.API_KEY, "language": config.LANGUAGE}
    # ... complétés par ceux de cet appel. « params or {} » : un dictionnaire vide si params vaut None.
    all_params.update(params or {})

    # timeout=15 : si TMDB ne répond pas en 15 secondes, on abandonne au lieu d'attendre
    # indéfiniment. On verra à l'étape 6 comment réessayer dans ce cas.
    response = requests.get(config.BASE_URL + path, params=all_params, timeout=15)

    # Si le code de réponse est une erreur (401 clé refusée, 404 introuvable...),
    # raise_for_status arrête le script avec un message clair.
    response.raise_for_status()

    # La réponse arrive en texte JSON ; .json() la transforme en dictionnaire Python.
    return response.json()


def get_movie(movie_id):
    """Fiche complète d'un film, casting compris."""
    return get_json(f"/movie/{movie_id}", {"append_to_response": "credits"})


def get_discover_page(start_date, end_date, page):
    """Une page (20 films) de la liste des films sortis entre deux dates incluses.

    Les dates sont du texte au format "AAAA-MM-JJ", par exemple "2010-01-31".
    """
    params = {
        "primary_release_date.gte": start_date,  # gte : sortis à partir de cette date
        "primary_release_date.lte": end_date,    # lte : jusqu'à cette date incluse
        "vote_count.gte": config.MIN_VOTES,      # au moins 50 votes
        "include_adult": "false",                # en texte : TMDB attend "false", pas False
        # Tri par date de sortie : contrairement à la popularité, une date ne change pas,
        # donc le classement reste stable pendant qu'on parcourt les pages.
        "sort_by": "primary_release_date.asc",
        "page": page,
    }
    return get_json("/discover/movie", params)


def month_ranges(year):
    """Les 12 mois d'une année, chacun sous la forme (premier jour, dernier jour).

    Exemple : month_ranges(2010)[1] vaut ("2010-02-01", "2010-02-28").
    """
    ranges = []
    for month in range(1, 13):  # de 1 à 12
        # calendar.monthrange renvoie (jour de la semaine du 1er, nombre de jours du mois).
        # On ne garde que le nombre de jours : 31, 30, ou 28/29 pour février.
        last_day = calendar.monthrange(year, month)[1]
        # :02d écrit le nombre sur 2 chiffres : 1 devient "01"
        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-{last_day:02d}"
        ranges.append((start, end))
    return ranges


def get_all_pages(start_date, end_date, out_path):
    """Récupère toutes les pages de discover entre deux dates et les écrit dans out_path.

    Renvoie la liste des pages (chacune est un dictionnaire, avec ses 20 films dans "results").
    """
    # 1. La page 1 nous dit combien de pages il y a en tout
    first_page = get_discover_page(start_date, end_date, 1)
    append_jsonl(out_path, first_page)
    total_pages = min(first_page["total_pages"], TMDB_MAX_PAGES)

    # 2. Puis les pages 2 à total_pages, qu'on garde dans une liste avec la première
    pages = [first_page]
    for page in range(2, total_pages + 1):
        data = get_discover_page(start_date, end_date, page)
        append_jsonl(out_path, data)
        pages.append(data)

    # Progression : une ligne par mois, par exemple « 2010-01 : 74 films, 4 pages »
    # start_date[:7] garde les 7 premiers caractères : "2010-01"
    print(f"  {start_date[:7]} : {first_page['total_results']} films, {total_pages} pages", flush=True)
    return pages


def get_movie_ids(year):
    """Renvoie la liste des ids des films sortis une année donnée, sans doublon.

    L'année est découpée en 12 mois : chaque recherche ne fait que quelques pages,
    donc le classement a très peu de temps pour bouger pendant la collecte.
    Toutes les pages brutes sont écrites dans data/raw/discover/year=YYYY.jsonl.
    """
    # Nom de fichier prévisible : on sait d'avance où trouver les données de 2010
    out_path = config.RAW_DIR / "discover" / f"year={year}.jsonl"

    ids = []
    films_lus = 0  # tous les films vus, doublons compris : pour mesurer les doublons
    for start_date, end_date in month_ranges(year):
        pages = get_all_pages(start_date, end_date, out_path)
        # On ramasse les ids de tous les films du mois, page après page
        for data in pages:
            for movie in data["results"]:
                films_lus += 1
                if movie["id"] not in ids:
                    ids.append(movie["id"])

    # Bilan : si les deux nombres sont égaux, aucun film n'a été vu deux fois
    print(f"{year} : {films_lus} films lus, {len(ids)} uniques, {films_lus - len(ids)} doublons")
    return ids


def append_jsonl(path, data):
    """Ajoute un dictionnaire à la fin d'un fichier JSON Lines (une ligne = un objet)."""
    # Crée le dossier s'il n'existe pas encore (parents=True : avec ses dossiers parents)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Mode "a" (append) : on écrit à la FIN du fichier, sans effacer ce qui y est déjà.
    # encoding="utf-8" : pour les accents et les autres alphabets (渡辺謙...).
    with open(path, "a", encoding="utf-8") as f:
        # json.dumps transforme le dictionnaire en texte JSON sur une seule ligne.
        # ensure_ascii=False garde les caractères lisibles (« é », « 渡 ») au lieu de codes comme é.
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    ids = get_movie_ids(2010)
    print(f"{len(ids)} ids récupérés, par exemple : {ids[:5]}")
