"""Tests de l'ingestion asynchrone (scripts/ingest/fetch_async.py).

On vérifie chaque exigence de la fiche pour l'ingestion :
- nommage déterministe et écriture en JSON Lines ;
- nouvelles tentatives avec attente exponentielle (1 s, 2 s, 4 s, 8 s) ;
- concurrence limitée par le sémaphore ;
- reprise après interruption (checkpoint par année, fichier .part).

Aucun test n'appelle la vraie API TMDB : on remplace TMDB par un faux serveur
écrit en Python (FakeSession). Les tests sont donc rapides, ne demandent pas de
clé, marchent sans Internet et donnent toujours le même résultat.

Lancer : python -m pytest tests/test_ingest.py -v
"""
import asyncio
import json

import aiohttp
import pytest

from scripts.ingest import config, fetch_async
from scripts.ingest.fetch_sync import append_jsonl, month_ranges, movies_path


# --- Outils : un faux TMDB ----------------------------------------------------
# fetch_async fait : « async with session.get(url, params=...) as response ».
# On fabrique des objets qui se comportent pareil, mais qui répondent ce qu'on veut.

class FakeResponse:
    """Une fausse réponse HTTP : un code (200, 404...), des en-têtes et un contenu JSON."""

    def __init__(self, status, data=None, headers=None):
        self.status = status
        self.data = data
        self.headers = headers or {}

    async def json(self):
        return self.data

    # Ces deux méthodes permettent d'écrire « async with ... as response »
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeError:
    """Remplace une réponse : lève une erreur au moment de la requête (timeout, réseau coupé)."""

    def __init__(self, error):
        self.error = error

    async def __aenter__(self):
        raise self.error

    async def __aexit__(self, *args):
        return False


class FakeSession:
    """Faux TMDB : renvoie, dans l'ordre, les réponses qu'on lui a données.

    Il compte aussi les appels, pour vérifier combien d'essais ont été faits.
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, url, params=None):
        self.calls += 1
        return self.responses.pop(0)


@pytest.fixture
def waits(monkeypatch):
    """Remplace asyncio.sleep : on note les attentes au lieu d'attendre vraiment.

    Sans ça, le test des 5 essais durerait 1 + 2 + 4 + 8 = 15 secondes.
    """
    noted = []

    async def fake_sleep(seconds):
        noted.append(seconds)

    monkeypatch.setattr(fetch_async.asyncio, "sleep", fake_sleep)
    return noted


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    """Fait écrire les fichiers dans un dossier temporaire, jamais dans le vrai data/raw/.

    tmp_path est un dossier vide fourni par pytest, supprimé après les tests.
    """
    monkeypatch.setattr(config, "RAW_DIR", tmp_path)
    return tmp_path


def run(coroutine):
    """Lance une fonction asynchrone et attend son résultat (comme dans le script)."""
    return asyncio.run(coroutine)


def get(session, path="/movie/1"):
    """Appelle get_json avec un sémaphore neuf de 20 places."""
    return run(fetch_async.get_json(session, asyncio.Semaphore(20), path))


# --- Nommage déterministe et JSON Lines ---------------------------------------

def test_les_12_mois_d_une_annee():
    mois = month_ranges(2024)
    assert len(mois) == 12
    assert mois[0] == ("2024-01-01", "2024-01-31")
    assert mois[1] == ("2024-02-01", "2024-02-29")   # 2024 est bissextile
    assert mois[11] == ("2024-12-01", "2024-12-31")
    assert month_ranges(2023)[1][1] == "2023-02-28"  # 2023 ne l'est pas


def test_nom_de_fichier_deterministe(raw_dir):
    # Même année = toujours le même nom : c'est ce qui permet la reprise
    assert movies_path(2010) == raw_dir / "movies" / "year=2010.jsonl"
    assert movies_path(2010) == movies_path(2010)


def test_append_jsonl_une_ligne_par_objet(tmp_path):
    path = tmp_path / "sous_dossier" / "films.jsonl"   # le dossier n'existe pas encore
    append_jsonl(path, {"id": 1, "title": "Amélie"})
    append_jsonl(path, {"id": 2, "title": "渡辺謙"})

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2                              # 2 objets = 2 lignes
    assert json.loads(lines[0]) == {"id": 1, "title": "Amélie"}
    assert "渡辺謙" in lines[1]                          # caractères gardés lisibles


# --- get_json : réponses et nouvelles tentatives ------------------------------

def test_200_renvoie_le_json(waits):
    session = FakeSession([FakeResponse(200, {"id": 27205, "title": "Inception"})])
    assert get(session) == {"id": 27205, "title": "Inception"}
    assert session.calls == 1
    assert waits == []          # aucune attente


def test_404_renvoie_none_sans_reessayer(waits):
    session = FakeSession([FakeResponse(404)])
    assert get(session) is None
    assert session.calls == 1   # un film absent ne sert à rien de redemander


def test_401_s_arrete_tout_de_suite(waits):
    # Clé refusée : réessayer ne changerait rien, on s'arrête au 1er essai
    session = FakeSession([FakeResponse(401)])
    with pytest.raises(RuntimeError, match="HTTP 401"):
        get(session)
    assert session.calls == 1


def test_429_puis_200_reessaie(waits):
    session = FakeSession([FakeResponse(429), FakeResponse(200, {"id": 1})])
    assert get(session) == {"id": 1}
    assert session.calls == 2
    assert waits == [1]         # 1 seconde avant le 2e essai


def test_timeout_puis_200_reessaie(waits):
    session = FakeSession([FakeError(asyncio.TimeoutError()), FakeResponse(200, {"id": 1})])
    assert get(session) == {"id": 1}
    assert waits == [1]


def test_erreur_reseau_puis_200_reessaie(waits):
    session = FakeSession([FakeError(aiohttp.ClientConnectionError()), FakeResponse(200, {"id": 1})])
    assert get(session) == {"id": 1}


def test_attente_exponentielle_puis_abandon(waits):
    # TMDB répond 503 à chaque fois : 5 essais, puis on abandonne
    session = FakeSession([FakeResponse(503) for _ in range(5)])
    with pytest.raises(RuntimeError, match="après 5 essais"):
        get(session)
    assert session.calls == 5
    assert waits == [1, 2, 4, 8]  # l'attente double à chaque fois


def test_retry_after_est_respecte(waits):
    # TMDB demande d'attendre 10 s : on attend 10 s, pas seulement 1 s
    session = FakeSession([FakeResponse(429, headers={"Retry-After": "10"}), FakeResponse(200, {})])
    get(session)
    assert waits == [10]


# --- Sémaphore : concurrence limitée ------------------------------------------

def test_semaphore_limite_les_requetes_simultanees():
    """On lance 30 requêtes avec un sémaphore de 3 places : jamais plus de 3 à la fois."""
    en_cours = 0
    maximum = 0

    class SlowResponse(FakeResponse):
        async def __aenter__(self):
            nonlocal en_cours, maximum
            en_cours += 1
            maximum = max(maximum, en_cours)
            await asyncio.sleep(0.01)    # la réponse « met du temps » à arriver
            return self

        async def __aexit__(self, *args):
            nonlocal en_cours
            en_cours -= 1
            return False

    class SlowSession:
        def get(self, url, params=None):
            return SlowResponse(200, {})

    async def lancer_30():
        sem = asyncio.Semaphore(3)
        session = SlowSession()
        await asyncio.gather(*(fetch_async.get_json(session, sem, f"/movie/{i}") for i in range(30)))

    run(lancer_30())
    assert maximum == 3


# --- Discover : pages et doublons ---------------------------------------------

def test_pages_limitees_a_500(monkeypatch):
    # TMDB annonce 600 pages, mais refuse au-delà de 500 : on n'en demande que 500
    demandees = []

    async def fake_page(session, sem, start, end, page):
        demandees.append(page)
        return {"total_pages": 600, "total_results": 12000, "results": []}

    monkeypatch.setattr(fetch_async, "get_discover_page", fake_page)
    pages = run(fetch_async.get_all_pages(None, None, "2010-01-01", "2010-01-31"))
    assert len(pages) == 500
    assert max(demandees) == 500


def test_ids_sans_doublon(raw_dir, monkeypatch):
    # Le film 2 apparaît en janvier ET en février : il ne doit être gardé qu'une fois
    async def fake_all_pages(session, sem, start, end):
        if start.endswith("-01-01"):
            return [{"results": [{"id": 1}, {"id": 2}]}]
        if start.endswith("-02-01"):
            return [{"results": [{"id": 2}, {"id": 3}]}]
        return [{"results": []}]

    monkeypatch.setattr(fetch_async, "get_all_pages", fake_all_pages)
    ids = run(fetch_async.get_movie_ids(None, None, 2010))
    assert ids == [1, 2, 3]
    # Les pages de discover sont gardées comme trace (12 mois = 12 lignes)
    trace = raw_dir / "discover" / "year=2010.jsonl"
    assert len(trace.read_text(encoding="utf-8").splitlines()) == 12


# --- Fiches des films et reprise (checkpoint) ---------------------------------

def test_fiches_ecrites_et_part_renomme(raw_dir, monkeypatch):
    # Faux TMDB : le film 404 n'existe pas, les autres oui
    async def fake_get_json(session, sem, path, params=None):
        movie_id = int(path.split("/")[-1])
        return None if movie_id == 404 else {"id": movie_id}

    monkeypatch.setattr(fetch_async, "get_json", fake_get_json)
    run(fetch_async.fetch_movies(None, asyncio.Semaphore(20), 2010, [1, 2, 404]))

    out = movies_path(2010)
    assert out.exists()
    assert not out.with_name(out.name + ".part").exists()   # le .part a été renommé
    ids = {json.loads(line)["id"] for line in out.read_text(encoding="utf-8").splitlines()}
    assert ids == {1, 2}                                     # le film absent est ignoré


def test_part_d_une_coupure_est_efface(raw_dir, monkeypatch):
    # Une coupure a laissé un .part avec une fiche à moitié écrite
    part = raw_dir / "movies" / "year=2010.jsonl.part"
    part.parent.mkdir(parents=True)
    part.write_text('{"id": 1, "title": "coup', encoding="utf-8")

    async def fake_get_json(session, sem, path, params=None):
        return {"id": int(path.split("/")[-1])}

    monkeypatch.setattr(fetch_async, "get_json", fake_get_json)
    run(fetch_async.fetch_movies(None, asyncio.Semaphore(20), 2010, [1]))

    # L'année est refaite proprement : une seule ligne, lisible
    lines = movies_path(2010).read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [{"id": 1}]


def test_annee_deja_recuperee_est_sautee(raw_dir, monkeypatch):
    # 2010 est déjà finie, 2011 non : seule 2011 doit être récupérée
    movies_path(2010).parent.mkdir(parents=True)
    movies_path(2010).write_text('{"id": 1}\n', encoding="utf-8")
    annees_faites = []

    async def fake_ids(session, sem, year):
        annees_faites.append(year)
        return []

    async def fake_fetch(session, sem, year, ids):
        pass

    monkeypatch.setattr(fetch_async, "get_movie_ids", fake_ids)
    monkeypatch.setattr(fetch_async, "fetch_movies", fake_fetch)
    run(fetch_async.main([2010, 2011]))

    assert annees_faites == [2011]
    assert movies_path(2010).read_text(encoding="utf-8") == '{"id": 1}\n'   # pas touché
