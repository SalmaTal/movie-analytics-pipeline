# Note d'exploration de l'API TMDB (contrat 1)

**Auteur :** Yannis (rôle A, ingestion) · **Date :** 2026-11-03 · **Statut :** proposition, à valider en équipe

Cette note fixe ce que l'ingestion demande à TMDB et ce qu'elle écrit dans `data/raw/`. Elle permet à B (transformation) et à C (SQL) de commencer sans attendre le script final.

**En résumé :** films sortis de 2000 à 2026, avec au moins 50 votes, en anglais. Il y aura environ 22 000 à 25 000 films, chacun écrit tel que TMDB le renvoie, casting compris, dans un fichier JSON Lines par année.

---

## 1. Périmètre

| Réglage | Valeur | Pourquoi |
|---|---|---|
| Années de sortie | 2000 à 2026 | 27 ans, de quoi analyser des évolutions dans le temps |
| Seuil de votes | au moins 50 (`vote_count.gte=50`) | Écarte les fiches presque vides et les notes non fiables |
| Langue | anglais (`language=en-US`) | Résumés plus complets qu'en français ; la langue n'affecte pas les analyses |
| Films pour adultes | exclus (`include_adult=false`) | Hors sujet |

**Volumes mesurés** avec `/discover/movie` le 2026-11-03 :

| Requête | Films | Pages |
|---|---|---|
| 2010, sans seuil | 18 183 | 910 |
| 2010, au moins 50 votes | 916 | 46 |
| 2025, au moins 50 votes | 783 | 40 |

On attend donc 800 à 900 films par an. Une recherche par année reste sous la limite de TMDB (500 pages, soit 10 000 films par recherche). 2026 sera incomplète : l'année n'est pas finie et ses films ont encore peu de votes.

---

## 2. Ce qu'on demande à TMDB

Tous les appels sont des `GET` sur `https://api.themoviedb.org/3`, avec la clé lue dans `.env` (`TMDB_TOKEN`).

### a. La liste des films d'une année : `/discover/movie`

```
GET /discover/movie
    ?primary_release_year=2010
    &vote_count.gte=50
    &include_adult=false
    &sort_by=popularity.desc
    &language=en-US
    &page=1
```

- On demande la page 1, on lit `total_pages`, puis on demande les pages suivantes.
- On n'en garde que les `id` des films, qui servent à l'appel suivant.
- Environ 1 200 appels en tout (27 ans × une quarantaine de pages).

### b. La fiche complète de chaque film : `/movie/{id}`

```
GET /movie/27205
    ?append_to_response=credits
    &language=en-US
```

- `append_to_response=credits` ajoute le casting et l'équipe technique dans la même réponse : un appel par film au lieu de deux.
- Environ 22 000 à 25 000 appels.

### c. La liste des genres : `/genre/movie/list`

```
GET /genre/movie/list?language=en-US
```

- Un seul appel : les 19 genres avec leur `id` et leur `name`. Utile pour la table `genres` de C.

---

## 3. Ce qu'on écrit dans `data/raw/`

Chaque réponse est écrite **telle quelle**, sans rien retirer, renommer ni ajouter : une réponse JSON par ligne (format JSON Lines).

| Fichier | Une ligne = | Utilisé par |
|---|---|---|
| `data/raw/movies/year=YYYY.jsonl` | la réponse complète de `/movie/{id}?append_to_response=credits` pour un film | **B : c'est le fichier principal** |
| `data/raw/genres/genres.jsonl` | la réponse de `/genre/movie/list` (une seule ligne) | B, puis C |
| `data/raw/discover/year=YYYY.jsonl` | une page de `/discover/movie` | Personne : trace de la collecte |
| `data/raw/checkpoints/movies_YYYY.txt` | l'`id` d'un film déjà traité | Usage interne de l'ingestion |

- **`YYYY`** est l'année demandée à discover (`primary_release_year`), donc l'année de sortie du film.
- **Doublons possibles.** Si l'ingestion est interrompue puis relancée, un film peut apparaître deux fois. B doit dédoublonner sur `id`.
- **Échantillon.** Avant le script complet, A fournit un échantillon d'environ 200 films (une année partielle) pour que B et C démarrent.

---

## 4. Contenu d'une ligne de `movies/year=YYYY.jsonl`

Les valeurs d'exemple sont celles d'Inception (`id` 27205).

### Valeurs simples

| Champ | Type JSON | Exemple | Remarques |
|---|---|---|---|
| `id` | nombre | `27205` | Identifiant unique TMDB, la clé du film |
| `imdb_id` | texte ou `null` | `"tt1375666"` | Peut manquer |
| `title` | texte | `"Inception"` | Titre en anglais |
| `original_title` | texte | `"Inception"` | Titre dans la langue d'origine |
| `original_language` | texte | `"en"` | Code de langue sur 2 lettres |
| `overview` | texte | `"Cobb, a skilled thief…"` | Peut être vide (`""`) |
| `tagline` | texte | `"Your mind is the scene of the crime."` | Souvent vide |
| `status` | texte | `"Released"` | |
| `release_date` | texte (date) | `"2010-07-15"` | Date écrite comme du texte ; peut être `""` |
| `runtime` | nombre | `148` | En minutes ; **0 = inconnu** |
| `budget` | nombre | `160000000` | En dollars ; **0 = inconnu** |
| `revenue` | nombre | `839030630` | En dollars ; **0 = inconnu** |
| `vote_average` | nombre | `8.373` | Note sur 10 |
| `vote_count` | nombre | `40628` | Au moins 50 dans notre périmètre |
| `popularity` | nombre | `47.2752` | Indice TMDB, change chaque jour |
| `homepage` | texte | `"https://www.warnerbros.com/…"` | Souvent vide |
| `poster_path`, `backdrop_path` | texte ou `null` | `"/xlaY2zyz….jpg"` | Chemins d'images |
| `adult`, `video`, `softcore` | vrai/faux | `false` | |

### Listes et sous-objets

| Champ | Contenu d'un élément | Exemple |
|---|---|---|
| `genres` | `id`, `name` | `{"id": 28, "name": "Action"}` |
| `production_companies` | `id`, `name`, `origin_country`, `logo_path` | `{"id": 174, "name": "Warner Bros. Pictures", "origin_country": "US"}` |
| `production_countries` | `iso_3166_1`, `name` | `{"iso_3166_1": "GB", "name": "United Kingdom"}` |
| `spoken_languages` | `iso_639_1`, `english_name`, `name` | `{"iso_639_1": "fr", "english_name": "French", "name": "Français"}` |
| `origin_country` | une liste de codes pays | `["US", "GB"]` |
| `belongs_to_collection` | `id`, `name`, `poster_path`, `backdrop_path`, ou `null` | `null` pour Inception |
| `credits.cast` | `id`, `name`, `original_name`, `character`, `order`, `cast_id`, `credit_id`, `gender`, `known_for_department`, `popularity`, `profile_path`, `adult` | `{"id": 6193, "name": "Leonardo DiCaprio", "character": "Dom Cobb", "order": 0}` |
| `credits.crew` | `id`, `name`, `original_name`, `job`, `department`, `credit_id`, `gender`, `known_for_department`, `popularity`, `profile_path`, `adult` | `{"id": 525, "name": "Christopher Nolan", "department": "Writing", "job": "Writer"}` |

**Vérifié sur une vraie réponse** (`/movie/27205?append_to_response=credits&language=en-US`) : les valeurs simples, les listes du film, `credits.cast` et `credits.crew`.
- Inception compte 52 acteurs, triés par `order` (0 = premier au générique), jusqu'aux petits rôles.
- `crew` contient beaucoup de postes techniques : cascadeurs, doublures, etc.
- Une même personne peut avoir plusieurs postes. Nolan (`id` 525) apparaît comme `Producer` et comme `Writer`, avec deux `credit_id` différents.
- `known_for_department` est la spécialité habituelle de la personne, pas son poste sur ce film. Exemple : Daniel Girondeaud, `known_for_department = "Acting"`, mais `job = "Stunts"` sur Inception.
- `gender` vaut 0 (inconnu), 1, 2 ou 3.
- `profile_path` peut être `null`.
- `original_name` peut être dans un autre alphabet (`"渡辺謙"`).
- La réponse d'Inception pèse 38 Ko et a mis 495 ms à arriver.

**Encore à vérifier :** `/discover/movie` (sauf `total_pages` et `total_results`, déjà mesurés) et `/genre/movie/list`. Leur structure vient de la documentation TMDB. Le poste `job = "Director"` n'apparaît pas dans l'extrait observé, qui est tronqué.

---

## 5. Points d'attention pour la transformation (B)

1. **Des 0 qui veulent dire « inconnu ».** `runtime`, `budget` et `revenue` à `0` doivent devenir des valeurs vides, sinon les moyennes seront fausses.
2. **Des dates en texte.** `release_date` est à convertir en vraie date. Un `""` devient une valeur vide.
3. **Des textes vides.** `overview`, `tagline` et `homepage` peuvent valoir `""`, qu'on peut traiter comme vides.
4. **Des listes à déplier.** `genres`, `credits.cast` et `credits.crew` contiennent plusieurs éléments par film. Ils deviennent des tableaux séparés, reliés au film par son `id`.
5. **Des personnes en double dans `crew`.** Une même personne peut occuper plusieurs postes : Nolan est `Producer` et `Writer` sur Inception. Le couple film + personne n'est donc pas unique. Il faut utiliser `credit_id`, ou le trio film + personne + `job` (à signaler à C pour la clé primaire). Pour trouver les réalisateurs, il faut filtrer sur `job`, **pas** sur `known_for_department`, qui est la spécialité habituelle de la personne.
6. **Des crédits volumineux.** Inception compte plus de 40 acteurs, jusqu'aux figurants crédités, et `crew` compte parfois des centaines de lignes. Proposition : garder les premiers acteurs (par exemple `order < 10`) et seulement certains postes de `crew` (par exemple `job = "Director"`).
7. **Des noms dans d'autres alphabets.** `original_name` peut contenir du japonais, du coréen, etc. Il faut lire et écrire en UTF-8.
8. **Des doublons de films.** Il faut dédoublonner sur `id`.

---

## 6. Ce qui reste à valider en équipe

- [ ] Le périmètre : 2000-2026, au moins 50 votes, en anglais.
- [ ] Les champs que B garde dans les Parquet (contrat 2). Par exemple, garde-t-on `crew` en entier ou seulement les réalisateurs ?
- [ ] Faut-il ajouter la date de collecte ? Elle n'est pas dans les réponses de TMDB. On peut la noter dans la Dataset Card, ou l'ajouter à côté des fichiers bruts sans toucher aux réponses.

*This product uses the TMDB API but is not endorsed or certified by TMDB.*
