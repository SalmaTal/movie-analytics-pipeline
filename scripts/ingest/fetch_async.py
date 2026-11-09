"""Ingestion asynchrone : plusieurs requêtes à la fois, avec nouvelles tentatives.

Même résultat que fetch_sync.py (mêmes fichiers, même format), en beaucoup plus rapide :
pendant qu'une requête attend la réponse de TMDB, les autres avancent.

- aiohttp + asyncio : jusqu'à CONCURRENCY requêtes en cours en même temps
- sémaphore : limite ce nombre pour ne pas surcharger TMDB
- nouvelles tentatives : sur 429, 5xx ou délai dépassé, on réessaie après 1 s, 2 s, 4 s, 8 s
- reprise : une année terminée n'est jamais refaite (fichier .part renommé à la fin)

Usage :
    python -m scripts.ingest.fetch_async
"""
import asyncio
import os
import ssl

import aiohttp

from scripts.ingest import config
# On réutilise les fonctions qui ne parlent pas à TMDB : elles marchent déjà
from scripts.ingest.fetch_sync import TMDB_MAX_PAGES, append_jsonl, month_ranges, movies_path

CONCURRENCY = 20                        # requêtes en cours en même temps, au maximum
MAX_TRIES = 5                           # essais par requête avant d'abandonner
RETRY_STATUSES = {429, 500, 502, 503, 504}  # erreurs passagères : ça vaut le coup de réessayer


async def get_json(session, sem, path, params=None):
    """Envoie une requête GET à TMDB et renvoie la réponse en dictionnaire.

    Renvoie None si la ressource n'existe pas (404).
    Réessaie sur les erreurs passagères, en doublant l'attente à chaque fois.
    """
    all_params = {"api_key": config.API_KEY, "language": config.LANGUAGE}
    all_params.update(params or {})

    for attempt in range(1, MAX_TRIES + 1):
        # Attente avant le prochain essai : 1 s, 2 s, 4 s, 8 s (2 puissance attempt-1)
        wait = 2 ** (attempt - 1)
        try:
            # « async with sem » : on prend une des 20 places ; on la rend en sortant du bloc.
            # La place n'est tenue que pendant la requête, pas pendant l'attente entre deux essais.
            async with sem:
                async with session.get(config.BASE_URL + path, params=all_params) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.status == 404:
                        return None
                    if response.status not in RETRY_STATUSES:
                        # 401 (clé refusée) par exemple : réessayer ne servirait à rien
                        raise RuntimeError(f"HTTP {response.status} sur {path}")
                    # Sur un 429, TMDB indique parfois combien de secondes attendre
                    retry_after = response.headers.get("Retry-After", "")
                    if retry_after.isdigit():
                        wait = max(wait, int(retry_after))
                    reason = f"HTTP {response.status}"
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            # Problème réseau ou délai de 15 s dépassé : erreur passagère, on réessaie
            reason = type(error).__name__

        if attempt < MAX_TRIES:
            # On signale chaque nouvelle tentative, pour voir ce qui se passe
            print(f"\n  {reason} sur {path}, nouvel essai dans {wait} s ({attempt}/{MAX_TRIES})", flush=True)
            # await asyncio.sleep : on attend SANS bloquer les autres requêtes
            await asyncio.sleep(wait)

    raise RuntimeError(f"{reason} sur {path} après {MAX_TRIES} essais")


async def get_discover_page(session, sem, start_date, end_date, page):
    """Une page (20 films) de la liste des films sortis entre deux dates incluses."""
    params = {
        "primary_release_date.gte": start_date,
        "primary_release_date.lte": end_date,
        "vote_count.gte": config.MIN_VOTES,
        "include_adult": "false",
        "sort_by": "primary_release_date.asc",  # tri stable : voir fetch_sync.py
        "page": page,
    }
    return await get_json(session, sem, "/discover/movie", params)


async def get_all_pages(session, sem, start_date, end_date):
    """Toutes les pages de discover entre deux dates, dans l'ordre."""
    # La page 1 d'abord : elle donne le nombre total de pages
    first_page = await get_discover_page(session, sem, start_date, end_date, 1)
    total_pages = min(first_page["total_pages"], TMDB_MAX_PAGES)

    # Puis les pages 2 à N, toutes lancées en même temps.
    # gather renvoie les résultats dans l'ordre où on les a demandés.
    other_pages = await asyncio.gather(*(
        get_discover_page(session, sem, start_date, end_date, page)
        for page in range(2, total_pages + 1)
    ))
    # Progression : une ligne par mois, dès qu'il est fini (les mois finissent dans le désordre)
    print(f"  {start_date[:7]} : {first_page['total_results']} films, {total_pages} pages", flush=True)
    return [first_page] + list(other_pages)


async def get_movie_ids(session, sem, year):
    """Ids des films sortis une année donnée, sans doublon. Écrit les pages dans discover/."""
    # Les 12 mois en même temps
    months = await asyncio.gather(*(
        get_all_pages(session, sem, start_date, end_date)
        for start_date, end_date in month_ranges(year)
    ))

    out_path = config.RAW_DIR / "discover" / f"year={year}.jsonl"
    out_path.unlink(missing_ok=True)  # on repart de zéro pour cette année

    ids = []
    films_lus = 0
    for pages in months:            # les mois, dans l'ordre (janvier d'abord)
        for data in pages:          # les pages du mois
            append_jsonl(out_path, data)
            for movie in data["results"]:
                films_lus += 1
                if movie["id"] not in ids:
                    ids.append(movie["id"])

    print(f"{year} : {films_lus} films lus, {len(ids)} uniques, {films_lus - len(ids)} doublons")
    return ids


async def fetch_movies(session, sem, year, ids):
    """Fiches complètes des films, écrites dans movies/year=AAAA.jsonl (via un .part)."""
    out_path = movies_path(year)
    part_path = out_path.with_name(out_path.name + ".part")
    part_path.unlink(missing_ok=True)  # reste d'une collecte interrompue

    done = 0
    errors = 0

    async def fetch_one(movie_id):
        # « nonlocal » : on modifie les compteurs de fetch_movies, pas des copies
        nonlocal done, errors
        try:
            movie = await get_json(session, sem, f"/movie/{movie_id}", {"append_to_response": "credits"})
        except RuntimeError as error:
            print(f"\n  film {movie_id} ignoré : {error}")
            movie = None
        if movie is None:
            errors += 1
        else:
            # Chaque fiche est écrite dès qu'elle arrive : l'ordre des lignes suit
            # l'arrivée des réponses, pas la date de sortie.
            append_jsonl(part_path, movie)
        done += 1
        print(f"  film {done}/{len(ids)}", end="\r", flush=True)

    # Toutes les fiches de l'année lancées en même temps ; le sémaphore en laisse passer 20 à la fois
    await asyncio.gather(*(fetch_one(movie_id) for movie_id in ids))
    print()

    part_path.replace(out_path)  # année finie : le .part devient le .jsonl
    print(f"{year} : {len(ids) - errors} fiches écrites dans {out_path}, {errors} erreurs")


def make_ssl_context():
    """Contexte SSL : utilise le certificat indiqué par REQUESTS_CA_BUNDLE s'il existe.

    Sur un réseau d'entreprise qui inspecte le HTTPS, cette variable pointe vers le
    certificat du proxy. requests la lit tout seul, aiohttp non : on la lui donne.
    """
    return ssl.create_default_context(cafile=os.environ.get("REQUESTS_CA_BUNDLE"))


async def main(years, sample_size=None):
    sem = asyncio.Semaphore(CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=15)  # 15 s maximum par requête
    connector = aiohttp.TCPConnector(ssl=make_ssl_context())

    # Une seule session pour toutes les requêtes : elle réutilise les connexions ouvertes.
    # trust_env=True : passe par le proxy indiqué dans HTTPS_PROXY / HTTP_PROXY, comme requests.
    # Sans ça, aiohttp tente une connexion directe, bloquée sur un réseau d'entreprise (timeout).
    async with aiohttp.ClientSession(timeout=timeout, connector=connector, trust_env=True) as session:
        for year in years:  # une année après l'autre ; à l'intérieur, tout va en parallèle
            if movies_path(year).exists():
                print(f"{year} : déjà récupérée, on passe")
                continue
            ids = await get_movie_ids(session, sem, year)
            await fetch_movies(session, sem, year, ids[:sample_size])


if __name__ == "__main__":
    # Les années à récupérer. Pour un essai sur 2 ans : YEARS = range(2000, 2002)
    YEARS = config.YEARS
    SAMPLE_SIZE = None  # None : tous les films ; un nombre (200...) pour un échantillon

    # asyncio.run lance la fonction asynchrone main et attend qu'elle soit finie
    asyncio.run(main(YEARS, SAMPLE_SIZE))
