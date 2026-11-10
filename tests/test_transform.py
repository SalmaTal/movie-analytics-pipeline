"""Tests de validation de la transformation TMDB -> Parquet.

Verification des règles métier de nettoyage et la déduplication du script
`scripts/transform/transform.py` :
- les valeurs "vides" doivent devenir `None` ;
- les textes doivent être nettoyés ;
- les dates doivent être converties en objets `date` ;
- les films, genres et personnes doivent être cohérents ;
- le script principal doit ignorer les doublons lors d'une relance.
"""

import json
from datetime import date

import pyarrow.dataset as ds

from scripts.transform import transform
from scripts.transform.transform import (
    clean_date, clean_movie, clean_text, extract_credits, extract_genres,
    zero_to_none,
)


# --- Cas de base : règles de nettoyage ----------------------------------------
# Test de la convertion des valeurs TMDB ambiguës en format exploitable par le pipeline.



def test_zero_devient_vide():
    # Trois cas : un 0 devient vide, un vide reste vide, et une vraie valeur (148) reste intacte.
    # Le troisième cas est important : il garantit qu’on n’efface pas tout par erreur.
    assert zero_to_none(0) is None
    assert zero_to_none(None) is None
    assert zero_to_none(148) == 148


def test_clean_text():
    #" bonjour " doit devenir "bonjour" (espaces retirés). 
    #Une chaîne vide "", une chaîne d’espaces " " et None doivent toutes donner None.
    assert clean_text("  bonjour ") == "bonjour"
    assert clean_text("") is None
    assert clean_text("   ") is None
    assert clean_text(None) is None


def test_clean_date():
    #"2010-07-15" doit donner date(2010, 7, 15), une vraie date Python. "" et
    #  None doivent donner None, sans faire planter le script.
    assert clean_date("2010-07-15") == date(2010, 7, 15)
    assert clean_date("") is None
    assert clean_date(None) is None


# --- Film minimal : valeurs manquantes ----------------------------------------
# On vérifie qu'une fiche incomplète conserve une structure stable et que les champs
# absents ou à 0 deviennent bien `None` plutôt que des zéros parasites.
def test_clean_movie_valeurs_manquantes():
    #On donne un film presque vide : il lui manque quasiment tous les champs. On vérifie que :
    # le budget à 0 devient None ;
    # l’imdb_id, absent, devient None (au lieu de provoquer une erreur) ;
    # la collection None donne un collection_id à None.
    
    r = clean_movie({"id": 1, "title": "A", "budget": 0,
                     "belongs_to_collection": None})
    assert r["budget"] is None
    assert r["imdb_id"] is None
    assert r["collection_id"] is None


# --- Genres et crédits --------------------------------------------------------
# Ces fonctions créent les tables de jointure et les lignes de personnes.
# On vérifie ici que les relations film-genre et film-personne sont bien construites.


def test_genres_deplies():
    #Un film avec 2 genres doit produire :
    #2 liens {"movie_id": 5, "genre_id": 28} et {"movie_id": 5, "genre_id": 80} ;
    #2 genres rencontrés, dont on compare les id ([28, 80]).
    film = {"id": 5, "genres": [{"id": 28, "name": "Action"},
                                {"id": 80, "name": "Crime"}]}
    links, genres = extract_genres(film)
    assert links == [{"movie_id": 5, "genre_id": 28},
                     {"movie_id": 5, "genre_id": 80}]
    assert [g["id"] for g in genres] == [28, 80]


def test_une_personne_deux_postes():
    #Une personne peut avoir deux postes différents sur le même film. On vérifie que
    # les deux postes sont bien conservés, avec des credit_id différents.
    film = {"id": 7, "credits": {"cast": [], "crew": [
        {"id": 525, "name": "N", "job": "Producer", "credit_id": "a"},
        {"id": 525, "name": "N", "job": "Writer", "credit_id": "b"},
    ]}}
    credits, _ = extract_credits(film)
    assert len(credits) == 2
    assert {c["credit_id"] for c in credits} == {"a", "b"}


def test_gender_zero_devient_vide():
    #On vérifie que le gender 0 devient None dans la table people.
    film = {"id": 7, "credits": {"cast": [
        {"id": 10, "name": "X", "credit_id": "c", "gender": 0}], "crew": []}}
    _, people = extract_credits(film)
    assert people[0]["gender"] is None


# --- Intégration du script principal -------------------------------------------
#Le seul test qui lance tout le script, de bout en bout.
# On simule une relance de l'ingestion : même film répété dans le même fichier.
# Le programme doit produire une seule ligne par film et garder les valeurs
# normalisées dans les Parquet sortants.
def test_main_dedoublonne(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    film = {
        "id": 1, "title": "A", "runtime": 0,
        "genres": [{"id": 28, "name": "Action"}],
        "credits": {"cast": [{"id": 10, "name": "X", "credit_id": "c1",
                              "order": 0, "gender": 0}], "crew": []},
    }
    # le même film deux fois, comme après une relance de l'ingestion
    (raw / "year=2010.jsonl").write_text(
        "\n".join(json.dumps(film) for _ in range(2)), encoding="utf-8")
    monkeypatch.setattr(transform, "RAW", raw)
    monkeypatch.setattr(transform, "OUT", tmp_path / "out")

    transform.main()

    movies = ds.dataset(tmp_path / "out" / "movies").to_table()
    assert movies.num_rows == 1                    # le doublon a disparu
    assert movies["runtime"].null_count == 1          # 0 -> vide
    assert ds.dataset(tmp_path / "out" / "genres").count_rows() == 1   # le genre n'est pas dupliqué
    assert ds.dataset(tmp_path / "out" / "credits").count_rows() == 1   # une seule ligne de casting

