"""Publication des Parquet locaux et de la Dataset Card vers un dataset Hugging Face.

Le pipeline produit des fichiers Parquet dans `data/processed/` ; cette étape les
publie sur un dépôt Hugging Face de type dataset, avec une `README.md` explicative
(Dataset Card) pour donner du contexte au dataset lors de sa publication.

Le script ne fait pas de transformation métier : il vérifie seulement que les
résultats sont présents, que le secret est bien configuré, puis téléverse les pièces
nécessaires sur le Hub.
"""
import os
import sys
import argparse

from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi


# --- Dossiers et configuration --------------------------------------------------
# On part de la racine du projet pour retrouver `.env` et les données transformées,
# quelle que soit la position du terminal depuis lequel le script est lancé.
# Le `ROOT` sert aussi à calculer le chemin de la Dataset Card, en gardant le script
# portable et indépendant du dossier de travail courant.
ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
CARD = Path(__file__).with_name("dataset_card.md")
DATASET_NAME = "tmdb-movies-2000-2026"  # nom du dataset appelé sur le Hub


# --- Publication ----------------------------------------------------------------
# Étapes :
# 1) charger le token Hugging Face depuis `.env` ;
# 2) vérifier que des Parquet existent bien ;
# 3) créer le dataset privé s'il n'existe pas ;
# 4) téléverser les Parquet dans le dossier `data/` ;
# 5) téléverser la Dataset Card comme `README.md` du dépôt.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="pose ce tag sur la version publiée (ex. v1.0.0)")
    args = parser.parse_args()
    # Les secrets du projet sont dans `.env`, jamais dans le dépôt Git.
    # On charge explicitement le fichier local pour ne pas devoir hardcoder le token
    # dans le code ou le commit.
    load_dotenv(ROOT / ".env")
    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("HF_TOKEN absent : ajoute-le dans .env (voir .env.example).")
    if not any(PROCESSED.glob("*/*.parquet")):
        # Le dataset ne peut pas être publié s'il n'y a aucune table transformée.
        sys.exit("Aucun Parquet dans data/processed/ : lance d'abord la transformation.")
    if not CARD.exists():
        # La Dataset Card est la page de présentation du dataset sur le Hub.
        sys.exit("dataset_card.md introuvable dans scripts/publish/.")

    api = HfApi(token=token)
    # Le repos est nommé avec le nom du compte Hugging Face de l'utilisateur et le
    # nom du dataset : <username>/tmdb-movies-2000-2026.
    repo_id = f"{api.whoami()['name']}/{DATASET_NAME}"
    # Dépôt PRIVÉ pendant le développement ; pas d'erreur s'il existe déjà.
    # On garde le dataset non public tant qu'on valide le périmètre et les données.
    api.create_repo(repo_id, repo_type="dataset", private=True, exist_ok=True)

    # data/processed/<tableau>/part-NNNN.parquet -> data/<tableau>/... sur le Hub.
    # On ne téléverse que les fichiers Parquet, pas le dossier complet du projet.
    api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=str(PROCESSED),
        path_in_repo="data",
        allow_patterns="*.parquet",
        commit_message="Parquet du pipeline (transformation)",
    )

    # La Dataset Card est le README.md du dépôt sur le Hub : elle explique le dataset,
    # son périmètre, ses limites et les règles d'usage. C'est aussi le point d'entrée
    # pour les utilisateurs qui découvrent le dataset sur Hugging Face.
    api.upload_file(
        path_or_fileobj=str(CARD),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset",
        commit_message="Dataset Card",
    )
    if args.tag:
        api.create_tag(
            repo_id,
            tag=args.tag,
            tag_message=f"Version {args.tag}",
            repo_type="dataset",
            exist_ok=True,
    )
    print(f"Tag posé : {args.tag}")
    print(f"Publié (privé) : https://huggingface.co/datasets/{repo_id}")


if __name__ == "__main__":
    main()