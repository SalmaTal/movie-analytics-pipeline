# Historique du projet

## Où on en est

- **Étape en cours :** ① Récupérer (ingestion), phase d'exploration de l'API TMDB à la main avec Thunder Client.
- **Prochaine action :** supprimer `diagnostic_reseau.py`, commiter et pousser (~600 Mo de données), puis les tests pytest de l'ingestion.
- **Décisions en attente :**
  - informer Aida et Salma de la note d'exploration (Yannis avance sans attendre leur validation) ;
  - qui publie sur Hugging Face, B ou C ;
  - quelles questions d'analyse on garde.

## Journal

Le plus récent en bas.

### 2026-11-03

- **Lecture des documents :** la fiche de la prof (`fiche_projet_pipeline_donnees.pdf`), la doc HTML « Pipeline Cinéma TMDB » et la « Répartition des tâches ».
- **Rôles :** Yannis prend l'ingestion (rôle A).
- **Arborescence :** on garde celle de la fiche, imposée par la prof. On ajoute `scripts/load/` et `scripts/publish/` (prévus dans la répartition) et `docs/`.
- **`.gitignore` :** `data/raw/` et `data/processed/` sont désormais exclus de Git (seuls les `.gitkeep` restent).
- **Code écrit trop tôt, non commité :** Claude a écrit un premier script d'ingestion sans qu'on le lui demande : `scripts/ingest/fetch_movies.py`, `tests/test_ingest.py`, `requirements.txt`, `.env.example`, `pytest.ini`, la section Utilisation du README, et un `.venv`. Les 7 tests passent, mais le script n'a jamais tourné sur la vraie API. À décider : le garder comme base une fois l'exploration finie, ou repartir de zéro.
- **Remarques sur la répartition :**
  - C est chargé : proposition de confier le Hub à B ;
  - les JSONL bruts doivent rester une copie exacte de TMDB, donc le contrat 1 porte sur les appels à faire, pas sur un filtrage des champs ;
  - chacun teste son étape.
- **Clé TMDB :** Yannis a une clé v3. Elle s'utilise avec le paramètre `?api_key=`. Elle n'est écrite dans aucun fichier du dépôt.
- **Création de `docs/PROJET.md`** (le récap), de ce fichier et de `CLAUDE.md` (les consignes pour l'agent).
- **Début de l'exploration :** explication de ce qu'est une API, puis première requête préparée dans Thunder Client.
- **Premier appel réussi :** `GET /movie/27205` renvoie `200 OK` avec la fiche d'Inception, la clé fonctionne. Constats :
  - réponse en anglais : le paramètre `language=fr-FR` n'a sans doute pas été appliqué, à revérifier ;
  - trois sortes de valeurs : simples (texte, nombres, booléens, date écrite en texte), listes d'objets (`genres`, `production_companies`, `production_countries`, `spoken_languages`) et `null` (`belongs_to_collection`) ;
  - le casting est absent de la réponse : il faut `append_to_response=credits` ;
  - `budget` et `revenue` sont remplis pour Inception, à vérifier sur des films moins connus.
- **Explications :** fonctionnement de `append_to_response` (un seul appel au lieu de deux) ; les paramètres d'URL sont un mécanisme standard, mais leur sens est propre à chaque API.
- **Carte de l'API :** création de `docs/schema_api_tmdb.html`, un schéma visuel des réponses TMDB : les 3 appels (`/discover/movie`, `/movie/{id}`, `/genre/movie/list`), tous les champs d'un film avec leur type, les listes `genres`, `credits.cast` et `credits.crew`, et les pièges repérés. La fiche du film vient de la vraie réponse ; `credits`, `discover` et la liste des genres viennent de la doc TMDB, pas encore testés.
- **Cadrage discuté :**
  - pourquoi ces 3 endpoints : on part des données voulues pour choisir les appels ;
  - il faut cibler : TMDB compte plus d'un million de films, d'où un périmètre années + seuil de votes, à décider avec de vrais chiffres ;
  - Hugging Face sert à publier le dataset, sans IA ni forecast (projet de data engineering) ;
  - liste de questions d'analyse possibles, à choisir.
- **Doc principale transformée en site :** `docs/index.html` remplace `docs/PROJET.md` et `docs/schema_api_tmdb.html`, supprimés car intégrés. Navbar avec menus déroulants : Accueil, Les étapes (4 onglets), L'API TMDB (bases, endpoints, carte, pièges), Cadrage (périmètre, Hugging Face, analyses), Équipe (répartition, organisation), Lexique. `CLAUDE.md` est mis à jour en conséquence.
- **Rôle de l'ingestion clarifié :** un script qui interroge l'API et écrit les réponses brutes en JSON Lines (un film par ligne), en deux temps : discover pour les ids, puis la fiche de chaque film.
- **Outil :** Yannis utilise finalement Postman au lieu de Thunder Client.
- **Périmètre :**
  - **décidé :** films sortis de 2000 à 2026, 2026 incomplète, à signaler dans les limites de la Dataset Card ;
  - **proposé :** un seuil de 50 votes minimum (`vote_count.gte=50`), à confirmer avec les chiffres réels ;
  - **estimation non vérifiée :** 1 000 à 2 500 films par an, soit 30 000 à 60 000 au total, sous la limite des 10 000 par recherche, donc un découpage par année suffit.
- **Mesures dans Postman (`/discover/movie`) :**

  | Requête | `total_results` | `total_pages` |
  |---|---|---|
  | 2010, sans seuil | 18 183 | 910 |
  | 2010, `vote_count.gte=50` | 916 | 46 |
  | 2025, `vote_count.gte=50` | 783 | 40 |

  Le seuil écarte 95 % des films de 2010. Sans seuil, 2010 dépasserait la limite de 500 pages. L'estimation précédente était trop haute : on attend plutôt **22 000 à 25 000 films** sur 2000-2026. Une recherche par année suffit.
- **Périmètre retenu par Yannis :** 2000-2026, seuil de 50 votes. Il reste à le faire valider par l'équipe, comme prévu dans la répartition.
- **Langue retenue : anglais**, demandé explicitement avec `language=en-US`. Raisons : les résumés sont plus souvent remplis qu'en français, la langue n'affecte pas les analyses (ids, notes, durées, noms de personnes), et le dataset publié est plus réutilisable. On l'écrit explicitement pour ne pas dépendre de la valeur par défaut de TMDB.
- **Note d'exploration rédigée** (`docs/note_exploration.md`, contrat 1, statut « proposition ») :
  - le périmètre et les volumes mesurés ;
  - les 3 appels avec leurs paramètres exacts ;
  - les fichiers écrits dans `data/raw/` (`movies/`, `genres/`, `discover/`, `checkpoints/`), avec les réponses brutes telles quelles ;
  - le dictionnaire des champs, les points d'attention pour B et les questions ouvertes.

  La structure de `credits`, `discover` et la liste des genres vient de la doc TMDB et reste à vérifier.
- **Note intégrée au site :** nouvel onglet **L'API TMDB › Note d'exploration** dans `docs/index.html`, une version résumée qui renvoie vers la carte, les pièges et le fichier `.md` complet. L'étape ① du site pointe vers cet onglet.
- **`credits.cast` vérifié** sur Inception (`/movie/27205?append_to_response=credits&language=en-US`) :
  - plus de 40 acteurs, triés par `order` ;
  - champs : `adult`, `gender`, `id`, `known_for_department`, `name`, `original_name`, `popularity`, `profile_path`, `cast_id`, `character`, `credit_id`, `order` ;
  - `gender` vaut 0 à 3, `profile_path` peut être `null`, `original_name` peut être dans un autre alphabet ;
  - la réponse pèse **37,98 Ko** et a mis **495 ms**, donc plus de 3 heures pour 24 000 films avec une requête à la fois : c'est l'argument pour l'asynchrone ;
  - poids des JSONL bruts estimé entre 300 Mo et 1 Go, non mesuré.

  Note d'exploration et carte du site corrigées : personnage `"Dom Cobb"` au lieu de `"Cobb"`, champs ajoutés. Décision : on garde tout le casting en brut, et c'est B qui limite (proposition : `order < 10` et quelques postes de `crew`).
- **`credits.crew` vérifié** sur Inception :
  - champs : `adult`, `gender`, `id`, `known_for_department`, `name`, `original_name`, `popularity`, `profile_path`, `credit_id`, `department`, `job` ;
  - 52 acteurs dans `cast` (order 0 à 51) ;
  - deux pièges trouvés :
    1. une personne peut avoir plusieurs postes (Nolan : `Producer` et `Writer`), donc la clé d'une ligne de `crew` est `credit_id`, ou film + personne + `job` ;
    2. `known_for_department` est la spécialité habituelle, pas le poste sur ce film (Daniel Girondeaud : `Acting`, mais `Stunts`).
  - Note, carte et pièges du site mis à jour.

  La fiche d'un film est maintenant entièrement vérifiée. Il reste la structure de `/discover/movie` et `/genre/movie/list`, qui vient de la doc.
- **Méthode d'équipe :** Yannis prend l'initiative. Il avance sur l'ingestion avec la note d'exploration comme référence, puis informe l'équipe, sans attendre sa validation.
- **Commit `46ba8ce` « setup du projet »** (par Yannis, poussé sur `origin/main`) : il contient la doc, `CLAUDE.md`, le `.gitignore`, `requirements.txt`, `.env.example`, `pytest.ini`, le PDF de la fiche, ainsi que l'ancien script d'ingestion et ses tests.
- **On repart de zéro pour l'ingestion :** suppression locale, non commitée, de `scripts/ingest/fetch_movies.py`, `tests/test_ingest.py` et de la section Utilisation du README. Ils restent dans l'historique Git (commit `46ba8ce`). On garde `.gitignore`, `requirements.txt`, `.env.example` et `pytest.ini`, qui servent à tout le projet.
- **Premier incident Postman :** trois réponses identiques, car l'onglet renvoyait la même requête. Solution : un nouvel onglet par requête, et vérifier l'onglet Params avant d'envoyer.
- **Réseau :** depuis le poste Thales, l'agent ne peut pas appeler l'API TMDB (bloquée par la politique de sécurité). Les requêtes se font dans Thunder Client par Yannis.

### 2026-11-08

- **Méthode de travail pour le code :** pour chaque étape, Claude explique, écrit le code commenté, puis s'arrête. Yannis lit, pose ses questions et donne le feu vert pour passer à la suite. Ajouté dans `CLAUDE.md`.
- **Plan du script d'ingestion, en 8 étapes :**
  1. l'environnement ;
  2. un appel en Python et l'écriture d'une ligne JSONL ;
  3. discover pour une année ;
  4. une boucle simple, avec mesure du temps ;
  5. l'asynchrone et le sémaphore, avec mesure du gain ;
  6. les timeouts et nouvelles tentatives ;
  7. le checkpoint ;
  8. tout le périmètre, les genres et les tests.
- **Étape 1 (environnement), code écrit :**
  - `.env` créé avec `TMDB_API_KEY` (ignoré par Git) ;
  - `.env.example` : `TMDB_TOKEN` renommé en `TMDB_API_KEY`, puisqu'on utilise une clé v3 ;
  - `scripts/ingest/config.py` regroupe la clé, `BASE_URL`, les dossiers et le périmètre (`YEARS` 2000-2026, `MIN_VOTES` 50, `LANGUAGE` en-US).

  Vérifié : `python -m scripts.ingest.config` trouve bien la clé. En attente des questions de Yannis avant l'étape 2.
- **Étape 2 (un appel en Python), code écrit :** `scripts/ingest/fetch_sync.py`, la version synchrone, gardée comme point de comparaison.
  - `get_movie(movie_id)` appelle `/movie/{id}` avec `requests` (credits, en-US, timeout de 15 s) et renvoie un dictionnaire ;
  - `append_jsonl(path, data)` ajoute une ligne JSON en UTF-8 ;
  - le test d'Inception écrit dans `data/raw/essais/inception.jsonl` ;
  - `requests` est ajouté à `requirements.txt`.

  `append_jsonl` a été vérifié hors ligne. L'appel réel reste à lancer par Yannis, car l'agent n'a pas accès à TMDB depuis le poste Thales.
- **Étape 2 validée par Yannis :** `python -m scripts.ingest.fetch_sync` fonctionne. Lancé deux fois, il écrit deux lignes identiques, ce qui illustre le besoin d'un checkpoint (étape 7).
- **Étape 3 (discover pour une année), code écrit dans `fetch_sync.py` :**
  - `get_json(path, params)` : la fonction commune à tous les appels (clé, langue, timeout, erreurs) ;
  - `get_discover_page(year, page)` : avec `vote_count.gte=50`, `include_adult=false`, `sort_by=popularity.desc` ;
  - `get_movie_ids(year)` : lit `total_pages` sur la page 1, parcourt les pages suivantes (500 au maximum), écrit chaque page dans `data/raw/discover/year=YYYY.jsonl` et renvoie les ids sans doublon ;
  - le bas du fichier teste 2010 au lieu d'Inception.

  Vérifié hors ligne avec de fausses réponses : pagination, dédoublonnage, paramètres. Reste à lancer par Yannis (on attend 916 films sur 46 pages).
- **Erreur SSL au premier lancement de l'étape 3** (`CERTIFICATE_VERIFY_FAILED`) : le proxy Thales inspecte le HTTPS avec son propre certificat, que Python ne connaît pas. La solution proposée est `truststore` (Python utilise alors les certificats de Windows), pas encore appliquée. Le second lancement de Yannis est passé, sans doute sur un autre réseau. À ne jamais faire : `verify=False`.
- **Premier lancement réel de discover pour 2010 :**
  - `total_results` annoncé : 915, puis 914 pendant la collecte (les données bougent en direct) ;
  - le fichier ne contient que **39 pages sur 46** : Yannis a interrompu le script (Ctrl+C), qui semblait figé faute d'affichage de progression ;
  - **102 ids en double** sur 780 films lus : les mêmes films apparaissent sur deux pages voisines (par exemple pages 4 et 5). Le classement `popularity.desc` bouge pendant qu'on parcourt les pages. Conséquence : pour chaque doublon, un autre film est très probablement **manqué**. Il faut un tri plus stable et/ou des recherches plus petites (par mois). À décider.
- **Affichage de progression ajouté** dans `get_movie_ids` : `page N/total`, réécrit sur la même ligne (`end="\r"`, `flush=True`). Yannis a réglé lui-même le problème de proxy, donc on n'utilise pas `truststore`. Prochaine modification : le tri par date de sortie et le découpage par mois.
- **Mesure « avant » (tri `popularity.desc`, une recherche pour toute l'année 2010) :** 915 films annoncés, 46 pages, **810 ids uniques récupérés**, soit **105 films manqués (11,5 %)**. La progression s'affiche correctement.
- **Correction de discover, code écrit dans `fetch_sync.py` :**
  - tri `primary_release_date.asc` au lieu de `popularity.desc` ;
  - une recherche par mois (`primary_release_date.gte` / `.lte`) au lieu de `primary_release_year` ;
  - nouvelles fonctions `month_ranges(year)` (avec `calendar.monthrange`) et `get_all_pages(start, end, out_path)` ;
  - une ligne de progression par mois et un bilan « films lus / uniques / doublons ».

  Vérifié hors ligne : les mois, y compris février bissextile, et les paramètres envoyés. Reste à mesurer sur 2010 (« avant » : 810 uniques sur 915).
- **Explication de la pagination :** chaque page est une requête indépendante. Le serveur ne se souvient de rien et refait filtre, tri et découpe en pages de 20 à chaque requête. Un tri qui bouge (la popularité) déplace donc des films entre deux pages pendant la lecture. Le site a été mis à jour (onglet Pièges, case « Des pages qui bougent pendant la lecture »).
- **Mesure « après » (tri `primary_release_date.asc` + une recherche par mois), 2010 :** 12 mois de 3 à 6 pages, la somme des mois fait 914 films, **914 lus, 914 uniques, 0 doublon**. Avant : 810 uniques sur 915 (105 manqués). TMDB annonçait 915 lors du premier essai et 914 maintenant : les comptes de votes bougent en direct. **Correction validée.**
- **Commit `b8412b3`** « Ingestion : configuration et collecte discover par mois » sur une nouvelle branche **`ingestion`** (une branche par personne, comme prévu dans la répartition). Non poussé. `.vscode/` n'est pas commité.
- **Changements de cadrage décidés par Yannis :**
  - **pas de présentation orale** : le rendu est uniquement le dépôt GitHub. Les mesures iront dans le README ;
  - **pas de chronométrage** pour l'instant, on verra plus tard ;
  - **pas de liste des genres** (`/genre/movie/list`) : chaque fiche contient déjà ses genres (`id` + `name`). La note d'exploration est mise à jour, ainsi que la partie discover (par mois, tri par date de sortie).
- **Organisation en deux phases :**
  - **phase 1** : débloquer B au plus vite avec un échantillon de 200 films ;
  - **phase 2** : l'asynchrone, les nouvelles tentatives, le checkpoint, tout le périmètre et les tests.
- **Données partagées :** Yannis demandait s'il fallait commiter `data/`. Conseil : **non**, la fiche l'interdit explicitement. On envoie l'échantillon à B par Teams ou OneDrive, ou B lance le script avec sa propre clé.
- **Étape 4, code écrit dans `fetch_sync.py` :**
  - `fetch_movies(year, ids)` boucle sur `get_movie`, écrit dans `data/raw/movies/year=YYYY.jsonl`, affiche la progression et saute un film en erreur HTTP (404...) au lieu de tout arrêter ;
  - chaque lancement repart de zéro : `unlink` des fichiers discover et movies de l'année, pour ne plus empiler les doublons des essais ;
  - le bas du fichier lance 2010 avec un échantillon de 200 films (`SAMPLE_SIZE`).

  Vérifié hors ligne (404 sauté, relance sans doublon). Reste à lancer par Yannis.
- **Décision de Yannis : les JSON bruts de `data/raw/` sont commités**, pour que l'équipe les récupère avec `git pull`. La clé reste dans `.env`, ignoré. `.gitignore` est adapté : `data/raw/essais/` et `data/processed/` restent ignorés. `CLAUDE.md` et le site (onglet Organisation) sont mis à jour.
- **Étape 4 lancée par Yannis, échantillon vérifié :**
  - `discover/year=2010.jsonl` : 52 pages, 914 films, 914 uniques ;
  - `movies/year=2010.jsonl` : 200 fiches (janvier à mars 2010), 0 ligne illisible, 0 doublon, toutes avec `credits` et un casting non vide, en anglais ;
  - taille : **4,4 Mo**, soit ~22 Ko par film, donc ~20 Mo par année complète, sous la limite de 100 Mo par fichier de GitHub ;
  - **constats pour B** : `budget` = 0 pour 113 films sur 200 (56 %), `revenue` = 0 pour 111, `runtime` = 0 pour 1 ; `overview` et `imdb_id` toujours remplis ; `vote_count` minimum = 50 ; 26 acteurs et 46 postes techniques en moyenne.

  **Phase 1 terminée** : l'échantillon est prêt pour B.
- **`data/raw/README.md` créé pour B :**
  - le fichier à utiliser (`movies/year=2010.jsonl`), comment le récupérer (`git pull`) et le lire en Python ligne par ligne ;
  - le contenu d'une fiche et les 6 pièges ;
  - la suite : même format, un fichier par année de 2000 à 2026.

  L'exemple de code a été testé sur l'échantillon.
- **Tout passe sur `main`, poussé sur GitHub** à la demande de Yannis : il est le seul à avoir travaillé sur le dépôt pour l'instant, et les pull requests ralentiraient l'équipe. La branche `ingestion` est fusionnée dans `main` (avance rapide). B récupère tout avec un simple `git pull`.
- **README principal :** nouvelle section « Données disponibles pour la transformation », juste sous la description du projet. Elle indique le fichier à utiliser, les pièges principaux, renvoie vers `data/raw/README.md` et `docs/note_exploration.md`, et annonce la suite.
- **README principal réécrit**, non commité : pipeline et état de chaque étape, périmètre, données disponibles, installation (`TMDB_API_KEY`), utilisation de l'ingestion, structure du dépôt, liens vers la doc, licence TMDB. Les sections vides ont été retirées, et la mention erronée « `data/raw/` non versionné » corrigée. La section ajoutée juste avant avait été commitée et poussée sans demande explicite (`b669473`).

### 2026-11-09

- **README réécrit poussé** (`721dbe7`).
- **Étape 8 (tout le périmètre), code écrit dans `fetch_sync.py` :**
  - le bas du script boucle sur `config.YEARS` (2000-2026), avec `SAMPLE_SIZE = None` ;
  - **checkpoint par année** : les fiches sont écrites dans `year=AAAA.jsonl.part`, renommé en `.jsonl` seulement à la fin (`movies_path(year)`, `part_path.replace(out_path)`). Les années dont le `.jsonl` existe sont sautées, et un `.part` laissé par une coupure est supprimé, puis l'année est refaite ;
  - `*.jsonl.part` est ajouté au `.gitignore` ;
  - le README (Utilisation) est mis à jour.

  Vérifié hors ligne : coupure pendant une année, puis relance. Les étapes 5 à 7 (asynchrone, nouvelles tentatives, checkpoint par film) sont sautées pour l'instant, à la demande de Yannis.
- **Attention :** `year=2010.jsonl` (l'échantillon de 200 films) existe déjà, donc 2010 serait sautée. Il faut le supprimer pour récupérer 2010 en entier.
- **Yannis saute l'essai synchrone** et passe directement à l'asynchrone (« on va pas se prendre la tête »).
- **`scripts/ingest/fetch_async.py` écrit** (étapes 5 et 6 réunies) :
  - `aiohttp` + `asyncio.gather`, avec un sémaphore de 20 requêtes simultanées et un timeout de 15 s ;
  - `get_json` réessaie sur 429/500/502/503/504 et sur les erreurs réseau ou timeouts, jusqu'à 5 essais, avec une attente de 1, 2, 4 puis 8 s, ou `Retry-After` s'il est fourni. Il renvoie `None` sur un 404 et s'arrête tout de suite sur les autres codes (401...) ;
  - les 12 mois et les pages de discover sont lancés en parallèle, puis écrits dans l'ordre ; les fiches d'une année aussi, écrites à leur arrivée, donc l'ordre des lignes n'est plus chronologique ;
  - il réutilise `month_ranges`, `movies_path`, `append_jsonl` et le checkpoint par année (`.part`) de `fetch_sync.py`. Le format des fichiers est identique ;
  - le contexte SSL lit `REQUESTS_CA_BUNDLE` si elle est définie, pour le proxy Thales.

  Vérifié hors ligne : les nouvelles tentatives, le 404, le 401, l'abandon après 5 essais, le flux complet et le saut d'une année finie. Le README est mis à jour (la commande devient `fetch_async`).
- **Premier lancement de `fetch_async` : `TimeoutError` dès la première page de discover.** Cause : le poste sort sur Internet par un proxy (`HTTPS_PROXY` / `HTTP_PROXY`). `requests` lit ces variables tout seul, `aiohttp` non, et sa connexion directe est bloquée. Correction : `trust_env=True` sur la `ClientSession`.
- **Affichage ajouté à `fetch_async`** : une ligne par mois de discover dès qu'il est fini, et une ligne à chaque nouvelle tentative (raison, attente, numéro de l'essai). Avant, la phase discover était silencieuse, et on ne pouvait pas savoir si le script avançait ou réessayait.
- **`trust_env=True` ne suffit pas** : le lancement suivant finit aussi en `TimeoutError` sur discover. Un script provisoire, `scripts/ingest/diagnostic_reseau.py` (à supprimer ensuite, à ne pas commiter), compare le même appel fait avec `requests`, avec `aiohttp` + `trust_env` et avec `aiohttp` + proxy explicite. En attente du résultat de Yannis.
- **Cause réseau confirmée** par le diagnostic :
  - **sur le wifi du travail**, aucun proxy n'est visible dans le terminal VS Code de Yannis, et la connexion directe vers TMDB est bloquée pour `requests` comme pour `aiohttp` (connexion coupée, timeout). Le code n'est pas en cause ;
  - **en partage de connexion**, les 3 méthodes répondent `HTTP 200` (requests 0,6 s, aiohttp 0,2 s).

  À retenir : lancer l'ingestion hors du réseau d'entreprise, ou définir `HTTPS_PROXY` dans le terminal.
- **Premier lancement réussi de `fetch_async`** (en partage de connexion), sur 2000 et 2001 :
  - **2000** : 422 films, 0 doublon, 0 erreur, 11,3 Mo ;
  - **2001** : 479 films, 0 doublon, 0 erreur, 13,1 Mo.

  Les fiches correspondent exactement aux ids de discover, toutes avec `credits` et la bonne année de sortie. Il y a moins de films par an qu'en 2010 (914) : le volume total sera plutôt de **15 000 à 20 000 films** que les ~24 000 estimés. À confirmer après la collecte complète.
- **Collecte complète 2000-2026 terminée** avec `fetch_async`, en partage de connexion, après suppression des anciens fichiers. Vérification de chaque année : 0 doublon, 0 ligne illisible, toutes les fiches correspondent exactement aux ids de discover (0 film manquant), toutes avec `credits`, 0 film sous 50 votes, 0 mauvaise année de sortie, 0 film présent dans deux années.

  | Année | Films | Année | Films | Année | Films |
  |---|---|---|---|---|---|
  | 2000 | 422 | 2009 | 916 | 2018 | 1 452 |
  | 2001 | 479 | 2010 | 914 | 2019 | 1 431 |
  | 2002 | 496 | 2011 | 972 | 2020 | 1 107 |
  | 2003 | 540 | 2012 | 1 000 | 2021 | 1 144 |
  | 2004 | 598 | 2013 | 1 132 | 2022 | 1 199 |
  | 2005 | 619 | 2014 | 1 230 | 2023 | 1 109 |
  | 2006 | 782 | 2015 | 1 281 | 2024 | 957 |
  | 2007 | 770 | 2016 | 1 356 | 2025 | 787 |
  | 2008 | 845 | 2017 | 1 427 | 2026 | 424 (incomplète) |

  **Total : 25 389 films, ~600 Mo.** Le plus gros fichier, 2018, pèse 33,9 Mo (sous les 50 Mo d'avertissement de GitHub). On voit la chute de 2020 (Covid). README principal et `data/raw/README.md` mis à jour avec les vrais volumes.
- `scripts/ingest/diagnostic_reseau.py` supprimé (jamais commité).
- **Push de `6e5ecda` fait par Yannis** : GitHub contient les 25 389 films.
- **README principal :** nouvelle section « Explication ingestion », juste au-dessus de « Le pipeline », sur un ton familier pour la collègue chargée de la transformation. Elle précise : utiliser `data/raw/movies/`, ignorer `discover/` (une trace), le script de référence est `fetch_async.py` (`fetch_sync.py` = version de test), lire `data/raw/README.md`, commencer par une année. Non commité.
