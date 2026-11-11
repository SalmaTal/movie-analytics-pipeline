# Données brutes TMDB (`data/raw/`)

Ce dossier contient les réponses de l'API TMDB, **telles quelles**, au format JSON Lines (un objet JSON par ligne). On n'y modifie jamais rien : le nettoyage se fait dans `data/processed/`.

## Le fichier à utiliser pour la transformation

**`movies/year=AAAA.jsonl`**, un fichier par année de 2000 à 2026 : une ligne = la fiche complète d'un film, casting compris.

- **Contenu :** **25 389 films** au total, de 422 (2000) à 1 452 (2018) par an. 2026 est incomplète (424 films). Fichiers de 11 à 34 Mo, ~600 Mo en tout.
- **Origine :** `/movie/{id}?append_to_response=credits&language=en-US`
- **Périmètre :** films avec au moins 50 votes, textes en anglais.

L'autre dossier, `discover/`, contient les pages de la liste des films : seulement des résumés, qui servent à l'ingestion pour trouver les ids. **Tu n'en as pas besoin.**

## Le récupérer

```bash
git pull
```

## Le lire en Python

```python
import json

with open("data/raw/movies/year=2010.jsonl", encoding="utf-8") as f:
    for line in f:
        movie = json.loads(line)   # un dictionnaire = un film
        print(movie["id"], movie["title"], len(movie["credits"]["cast"]))
```

Lis les fichiers ligne par ligne comme ci-dessus, sans tout charger d'un coup : c'est ce que la fiche demande (traitement par lots).

## Ce qu'il y a dans une fiche

- **Valeurs simples :** `id` (la clé du film), `title`, `release_date` (texte `"2010-07-15"`), `runtime`, `budget`, `revenue`, `vote_average`, `vote_count`, `overview`, `imdb_id`...
- **Listes :** `genres` (`id` + `name`), `production_companies`, `production_countries`, `spoken_languages`.
- **Casting :** `credits.cast` (acteurs, triés par `order`) et `credits.crew` (équipe technique : `job`, `department`).

Le détail de chaque champ est dans [docs/note_exploration.md](../../docs/note_exploration.md).

## Les pièges à connaître

1. **`0` veut dire « inconnu »** pour `budget` (56 % des films de l'échantillon), `revenue` et `runtime`. Il faut le remplacer par une valeur vide, sinon les moyennes seront fausses.
2. **`release_date` est du texte**, à convertir en date. Il peut aussi valoir `""`.
3. **Une même personne peut avoir plusieurs postes** dans `crew` (Nolan est `Producer` et `Writer` sur Inception). La ligne unique, c'est `credit_id`, pas l'`id` de la personne.
4. **Pour trouver les réalisateurs**, filtre sur `job == "Director"`, pas sur `known_for_department`.
5. **Le casting est long** : 26 acteurs et 46 postes techniques en moyenne. On peut ne garder que les premiers acteurs (`order < 10`, par exemple).
6. **Dédoublonne sur `id`** : un film peut apparaître deux fois si l'ingestion est relancée après une coupure.

## Pour démarrer

Commence par une seule année (par exemple `movies/year=2010.jsonl`, 914 films) pour mettre au point ton script, puis lance-le sur toutes les années.
