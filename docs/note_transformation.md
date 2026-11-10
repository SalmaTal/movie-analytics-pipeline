# Note de transformation (contrat 2)

**Auteur :** Aida (rôle B, transformation) · **Date :** 2026-11-09 · **Statut :** proposition, à valider avec Salma

Cette note fixe ce que la transformation écrit dans `data/processed/` et ce que Salma peut charger dans PostgreSQL. Elle part de `data/raw/movies/` (contrat 1 : [note_exploration.md](note_exploration.md)).

**En résumé :** `scripts/transform/transform.py` lit les 25 389 films bruts par lots d'au plus 1 000 films, les nettoie et écrit 5 tableaux Parquet typés. Les types exacts sont dans `SCHEMAS`, en haut du script.

## 1. Tableaux produits

| Tableau | Une ligne = | Lignes | Clé primaire |
|---|---|---|---|
| `movies` | un film | 25 389 | `id` |
| `genres` | un genre | 19 | `id` |
| `movie_genres` | un lien film-genre | 60 263 | `(movie_id, genre_id)` |
| `people` | une personne | 674 561 | `id` |
| `credits` | un poste d'une personne sur un film (cast ou crew) | 1 914 840 | `credit_id` |

Clés étrangères : `movie_genres.movie_id` → `movies.id`, `movie_genres.genre_id` → `genres.id`, `credits.movie_id` → `movies.id`, `credits.person_id` → `people.id`.

Fichiers : `data/processed/<tableau>/part-NNNN.parquet`, un par lot de 1 000 films (un seul pour `genres`).

## 2. Colonnes et types

| Tableau | Colonnes (type) |
|---|---|
| `movies` | `id` (int), `imdb_id`, `title`, `original_title`, `original_language`, `status`, `overview`, `tagline`, `homepage` (texte), `release_date` (date), `runtime`, `budget`, `revenue` (int), `vote_average` (décimal), `vote_count` (int), `popularity` (décimal), `adult` (booléen), `collection_id` (int) |
| `genres` | `id` (int), `name` (texte) |
| `movie_genres` | `movie_id` (int), `genre_id` (int) |
| `people` | `id` (int), `name` (texte), `gender` (int), `known_for_department` (texte), `popularity` (décimal) |
| `credits` | `credit_id` (texte), `movie_id`, `person_id` (int), `type` (`cast` ou `crew`), `character` (texte), `order` (int), `job`, `department` (texte) |

Dans `credits`, `character` et `order` ne servent que pour `cast`, `job` et `department` que pour `crew` : les autres cases sont vides.

## 3. Règles de nettoyage

| Règle | Détail |
|---|---|
| Les 0 « inconnus » | `runtime`, `budget`, `revenue` et `gender` à 0 deviennent vides (NULL) |
| Dates | `release_date` devient une vraie date ; `""` devient vide |
| Textes | espaces retirés ; `""` devient vide |
| Valeurs manquantes | `imdb_id`, collection, etc. : vides, sans erreur |
| Listes dépliées | `genres`, `credits.cast`, `credits.crew` : une ligne par élément |
| Doublons | un film déjà vu (même `id`) est ignoré ; une personne n'est écrite qu'une fois (première fiche rencontrée) |
| Casting | tout le `cast` et tout le `crew` sont gardés ; une personne avec deux postes a deux lignes (deux `credit_id`) |

Le script traite 1 000 films à la fois, sans charger les fichiers en entier.

## 4. Champs non gardés

`backdrop_path`, `poster_path`, `video`, `softcore`, `origin_country`, `production_companies`, `production_countries`, `spoken_languages`, le nom de la collection, et dans le casting `original_name`, `profile_path`, `cast_id`, `adult`.

## 5. Mesures

Sur les 25 389 films : environ 33 s, environ 400 Mo de RAM au maximum, 589 Mo de JSON bruts pour XX Mo de Parquet.

## 6. À valider avec Salma

- [ ] Garde-t-on tout le `crew` (1,9 million de lignes avec le `cast`) ou seulement certains postes (par exemple `Director`) ?
- [ ] Faut-il ajouter les pays, langues ou sociétés de production, si les analyses les demandent ?

*This product uses the TMDB API but is not endorsed or certified by TMDB.*