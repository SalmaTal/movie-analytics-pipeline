"""Réglages de l'ingestion : clé API, adresse de TMDB, périmètre et dossiers.

Tout ce que le script doit savoir est regroupé ici, pour le modifier à un seul endroit.
Les valeurs du périmètre viennent de docs/note_exploration.md.

Pour vérifier que la clé est bien lue :
    python -m scripts.ingest.config
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# --- Dossiers ---------------------------------------------------------------
# __file__ est le chemin de ce fichier : .../scripts/ingest/config.py
# parents[2] remonte de deux dossiers (ingest -> scripts -> racine du projet).
# On calcule les chemins à partir de ce fichier, et non du dossier courant,
# pour que le script marche d'où qu'on le lance.
ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"

# --- Secrets ----------------------------------------------------------------
# load_dotenv lit le fichier .env et range chaque ligne NOM=valeur
# dans les variables d'environnement. os.environ permet ensuite de les lire.
load_dotenv(ROOT / ".env")
API_KEY = os.environ.get("TMDB_API_KEY")  # None si la variable est absente

# --- API TMDB ---------------------------------------------------------------
BASE_URL = "https://api.themoviedb.org/3"

# --- Périmètre (note d'exploration) ------------------------------------------
YEARS = range(2000, 2027)  # range s'arrête juste avant 2027 : 2000 à 2026 inclus
MIN_VOTES = 50             # vote_count.gte : écarte les fiches presque vides
LANGUAGE = "en-US"         # résumés plus complets qu'en français


# Ce bloc ne s'exécute que si on lance ce fichier directement,
# pas quand un autre script fait « from scripts.ingest import config ».
if __name__ == "__main__":
    if API_KEY:
        # On n'affiche que le début de la clé : un secret ne s'imprime jamais en entier
        print(f"Clé TMDB trouvée : {API_KEY[:4]}…")
    else:
        print("Clé TMDB introuvable : ajoute TMDB_API_KEY=... dans le fichier .env")
    print(f"Racine du projet : {ROOT}")
    print(f"Dossier des données brutes : {RAW_DIR}")
    print(f"Périmètre : {YEARS[0]} à {YEARS[-1]}, au moins {MIN_VOTES} votes, langue {LANGUAGE}")
