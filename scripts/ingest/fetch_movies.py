"""Ingestion asynchrone depuis l'API TMDB.

Pour chaque année :
  1. /discover/movie, page par page, pour obtenir les ids des films
     -> data/raw/discover/year=YYYY.jsonl (une ligne par page, réponse brute)
  2. /movie/{id}?append_to_response=credits pour la fiche complète et le casting
     -> data/raw/movies/year=YYYY.jsonl (une ligne par film, réponse brute)

Reprise après interruption :
  - les pages discover déjà présentes dans le fichier ne sont pas redemandées ;
  - les ids terminés sont notés dans data/raw/checkpoints/movies_YYYY.txt.

Usage :
    python -m scripts.ingest.fetch_movies --years 2010 --max-pages 5
"""
import argparse
import asyncio
import json
import logging
import os
import random
import sys
import time
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

BASE_URL = "https://api.themoviedb.org/3"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RETRY_STATUSES = {429, 500, 502, 503, 504}
TMDB_MAX_PAGES = 500  # TMDB refuse les pages au-delà de 500 pour une même recherche

log = logging.getLogger("ingest")


async def get_json(session, sem, path, params, tries=5):
    """GET avec nouvelles tentatives et attente exponentielle. Renvoie None sur 404."""
    for attempt in range(1, tries + 1):
        wait = 2 ** (attempt - 1) + random.random()
        try:
            # Le sémaphore n'est tenu que pendant la requête, pas pendant l'attente
            async with sem, session.get(BASE_URL + path, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                if resp.status == 404:
                    return None
                if resp.status not in RETRY_STATUSES:
                    raise RuntimeError(f"HTTP {resp.status} sur {path}")
                retry_after = resp.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    wait = max(wait, int(retry_after))
                log.warning("HTTP %s sur %s (essai %d/%d)", resp.status, path, attempt, tries)
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            log.warning("%s sur %s (essai %d/%d)", type(exc).__name__, path, attempt, tries)
        if attempt < tries:
            await asyncio.sleep(wait)
    raise RuntimeError(f"Échec après {tries} essais : {path}")


def read_jsonl(path):
    """Lit un fichier JSON Lines ; une dernière ligne tronquée par un arrêt brutal est ignorée."""
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                log.warning("Ligne illisible ignorée dans %s", path)
    return rows


def read_checkpoint(path):
    """Ensemble des ids déjà traités."""
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return {int(line) for line in f if line.strip()}


def ids_from_pages(pages):
    """Ids des films, dans l'ordre des pages, sans doublon."""
    ids = []
    seen = set()
    for page in sorted(pages, key=lambda p: p["page"]):
        for movie in page.get("results", []):
            if movie["id"] not in seen:
                seen.add(movie["id"])
                ids.append(movie["id"])
    return ids


def append_line(f, text):
    f.write(text + "\n")
    f.flush()


async def discover_ids(session, sem, year, max_pages, language):
    path = RAW_DIR / "discover" / f"year={year}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    pages = {p["page"]: p for p in read_jsonl(path)}
    params = {
        "primary_release_year": year,
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "language": language,
    }

    with path.open("a", encoding="utf-8") as out:
        async def fetch_page(n):
            data = await get_json(session, sem, "/discover/movie", {**params, "page": n})
            if data is not None:
                append_line(out, json.dumps(data, ensure_ascii=False))
                pages[n] = data

        # La page 1 donne le nombre total de pages
        if 1 not in pages:
            await fetch_page(1)
        total = min(pages[1]["total_pages"], max_pages, TMDB_MAX_PAGES)
        missing = [n for n in range(2, total + 1) if n not in pages]
        await asyncio.gather(*(fetch_page(n) for n in missing))

    wanted = [p for n, p in pages.items() if n <= total]
    log.info("%d : %d pages discover (%d nouvelles)", year, len(wanted), len(missing))
    return ids_from_pages(wanted)


async def fetch_details(session, sem, year, ids, language):
    movies_path = RAW_DIR / "movies" / f"year={year}.jsonl"
    ckpt_path = RAW_DIR / "checkpoints" / f"movies_{year}.txt"
    movies_path.parent.mkdir(parents=True, exist_ok=True)
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)

    done = read_checkpoint(ckpt_path)
    todo = [i for i in ids if i not in done]
    log.info("%d : %d films, %d déjà faits, %d à récupérer", year, len(ids), len(ids) - len(todo), len(todo))
    params = {"append_to_response": "credits", "language": language}
    failed = []

    with movies_path.open("a", encoding="utf-8") as out, ckpt_path.open("a", encoding="utf-8") as ckpt:
        async def fetch_one(movie_id):
            try:
                movie = await get_json(session, sem, f"/movie/{movie_id}", params)
            except RuntimeError as exc:
                # Pas de checkpoint : le film sera retenté au prochain lancement
                log.error("%s", exc)
                failed.append(movie_id)
                return
            # Un arrêt entre ces deux écritures peut dupliquer un film dans le JSONL :
            # la transformation supprime les doublons.
            if movie is not None:
                append_line(out, json.dumps(movie, ensure_ascii=False))
            append_line(ckpt, str(movie_id))

        await asyncio.gather(*(fetch_one(i) for i in todo))

    return len(todo) - len(failed), failed


async def run(years, max_pages, concurrency, language):
    headers = {
        "Authorization": f"Bearer {os.environ['TMDB_TOKEN']}",
        "Accept": "application/json",
    }
    sem = asyncio.Semaphore(concurrency)
    timeout = aiohttp.ClientTimeout(total=15)
    all_failed = []

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        for year in years:
            start = time.perf_counter()
            ids = await discover_ids(session, sem, year, max_pages, language)
            fetched, failed = await fetch_details(session, sem, year, ids, language)
            all_failed += failed
            log.info("%d : %d films récupérés, %d échecs, %.1f s",
                     year, fetched, len(failed), time.perf_counter() - start)
    return all_failed


def main():
    parser = argparse.ArgumentParser(description="Ingestion asynchrone des films TMDB")
    parser.add_argument("--years", type=int, nargs="+", required=True, help="ex. : --years 2010 2011")
    parser.add_argument("--max-pages", type=int, default=5, help="pages discover par année (20 films par page)")
    parser.add_argument("--concurrency", type=int, default=20, help="requêtes simultanées maximum")
    parser.add_argument("--language", default="fr-FR")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    if not os.environ.get("TMDB_TOKEN"):
        sys.exit("TMDB_TOKEN manquant : renseignez-le dans .env (voir .env.example)")

    failed = asyncio.run(run(args.years, args.max_pages, args.concurrency, args.language))
    if failed:
        log.error("%d films en échec, relancez la commande pour les retenter", len(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
