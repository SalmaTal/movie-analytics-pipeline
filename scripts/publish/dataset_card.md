---
license: other
license_name: tmdb-api-terms
license_link: https://www.themoviedb.org/api-terms-of-use
language:
- en
pretty_name: TMDB Movies 2000-2026
tags:
- movies
- tmdb
- tabular
configs:
- config_name: movies
  data_files: "data/movies/*.parquet"
  default: true
- config_name: genres
  data_files: "data/genres/*.parquet"
- config_name: movie_genres
  data_files: "data/movie_genres/*.parquet"
- config_name: people
  data_files: "data/people/*.parquet"
- config_name: credits
  data_files: "data/credits/*.parquet"
---

# TMDB Movies 2000-2026

Films sortis de 2000 à 2026 avec au moins 50 votes sur [TMDB](https://www.themoviedb.org/), nettoyés et organisés en 5 tableaux Parquet. Ils sont produits par un pipeline de données complet (collecte asynchrone, transformation, base SQL, publication) réalisé dans le cadre de la formation *Data Engineer expert en IA* (Ynov). Les textes (résumés, accroches) sont en anglais.

## Contenu

| Configuration | Une ligne = | Lignes |
|---|---|---|
| `movies` | un film | 25 389 |
| `genres` | un genre | 19 |
| `movie_genres` | un lien film-genre | 60 263 |
| `people` | une personne (acteur ou équipe technique) | 674 561 |
| `credits` | un poste d'une personne sur un film | 1 914 840 |

Les liens entre tableaux : `movie_genres.movie_id` → `movies.id`, `movie_genres.genre_id` → `genres.id`, `credits.movie_id` → `movies.id`, `credits.person_id` → `people.id`.

### Colonnes

- **`movies`** : `id`, `imdb_id`, `title`, `original_title`, `original_language`, `status`, `overview`, `tagline`, `homepage`, `release_date` (date), `runtime` (minutes), `budget` et `revenue` (dollars), `vote_average`, `vote_count`, `popularity`, `adult`, `collection_id`.
- **`genres`** : `id`, `name`.
- **`movie_genres`** : `movie_id`, `genre_id`.
- **`people`** : `id`, `name`, `gender`, `known_for_department`, `popularity`.
- **`credits`** : `credit_id` (clé), `movie_id`, `person_id`, `type` (`cast` ou `crew`), `character`, `order`, `job`, `department`. `character` et `order` ne servent que pour `cast`, `job` et `department` que pour `crew`.

Les valeurs inconnues sont vides (NULL). Les types exacts sont ceux des fichiers Parquet.

## Collecte et transformation

- **Source :** API TMDB v3, collecte terminée en novembre 2026. Pour chaque mois de 2000 à 2026, la liste des films (`/discover/movie`, au moins 50 votes, anglais, sans films pour adultes, triée par date de sortie), puis la fiche complète de chaque film avec son casting (`/movie/{id}` avec `append_to_response=credits`).
- **Ingestion :** asynchrone (`aiohttp`), concurrence limitée par un sémaphore, nouvelles tentatives avec attente exponentielle, reprise après interruption.
- **Transformation :** lecture par lots d'au plus 1 000 films, écriture en Parquet avec des types imposés. Les `0` de `runtime`, `budget`, `revenue` et `gender` (qui veulent dire « inconnu » chez TMDB) deviennent des valeurs vides. Les dates sont de vraies dates, les textes vides deviennent vides, les doublons sont supprimés. Les listes (genres, casting) sont dépliées en tableaux séparés.
- **Code :** dépôt GitHub du projet (`movie-analytics-pipeline`).

## Utilisation

```python
from datasets import load_dataset

movies = load_dataset("NdeyeAidaNdour/tmdb-movies-2000-2026", "movies", split="train")
credits = load_dataset("NdeyeAidaNdour/tmdb-movies-2000-2026", "credits", split="train")
```

## Limites

- **2026 est incomplète** : l'année n'était pas terminée à la collecte, et ses films ont encore peu de votes.
- **Biais de sélection** : seuls les films avec au moins 50 votes sont inclus, ce qui écarte les films peu connus.
- **Données manquantes** : `budget` et `revenue` sont souvent inconnus, donc vides.
- **Instantané** : `popularity`, `vote_average` et `vote_count` changent chaque jour chez TMDB ; ils reflètent le moment de la collecte.
- **Casting complet** : `credits` contient tout le casting et toute l'équipe, y compris de nombreux postes techniques et petits rôles.
- **`gender`** : 1, 2 et 3 selon la documentation de TMDB (femme, homme, non binaire) ; vide si non renseigné.
- Les données de TMDB sont alimentées par sa communauté et peuvent contenir des erreurs.

## Licence et attribution

Les données proviennent de TMDB et restent soumises à ses [conditions d'utilisation de l'API](https://www.themoviedb.org/api-terms-of-use) : usage non commercial, attribution obligatoire. Ce dataset est destiné à un usage pédagogique et non commercial. TMDB ne revendique pas la propriété des données ; les ayants droit restent ceux des œuvres concernées.

**This product uses the TMDB API but is not endorsed or certified by TMDB.**

## Version

v1.0.0 : première publication.

## Auteurs

Ndeye Aida Ndour, Yannis Staali, Salma Talib.