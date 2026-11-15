# Historique du projet

## Où on en est

- **Étapes :** ① ingestion terminée (25 389 films, 2000-2026, poussée), 17 tests pytest ; ② transformation faite par Aida et reproduite par Yannis ; ③ base SQL faite par Salma ; ④ publication faite par Aida (Hub **public**, tag v1.0.0).
- **En cours :** finitions pour coller à la fiche. Yannis les fait lui-même et prévient l'équipe ensuite.
- **Prochaines actions, dans l'ordre :**
  1. **tester tout le pipeline depuis zéro sur le VPS de Yannis**, en suivant `docs/TEST_VPS.md` (mesures du benchmark comprises), puis reporter les temps de l'index dans `docs/note_cenception_sql.md` ;
  2. prévenir Aida et Salma : leur prochain `git pull` supprimera `data/raw/movies/` et `data/raw/discover/` chez elles (les copier avant) ;
- **Données en local :** `data/` est vide sur le poste de Yannis (choix assumé). Sans effet sur les tests : ils écrivent dans un dossier temporaire.
- **À signaler à Salma :** la mise en place de la base n'est documentée nulle part (voir le 2026-11-13) ; le script de chargement écrit les réglages de connexion en dur au lieu de lire `DATABASE_URL`.
- **Idée bonus (pas demandée par la fiche) :** orchestrer le pipeline avec Airflow sur le VPS de Yannis (voir le 2026-11-13).
- **Décisions en attente (équipe) :** garder ou non tout le `crew`.

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
### 2026-11-06
- **Méthode :** pour ne pas attendre l'ingestion, le nettoyage a d'abord été écrit et testé sur un faux échantillon construit d'après `docs/note_exploration.md` (0 « inconnus », date vide, `imdb_id` absent, doublon, personne avec deux postes).

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


### 2026-11-09
- **README réécrit**.
- **Transformation :** `scripts/transform/transform.py` lit `data/raw/movies/` par lots de 1 000 films et écrit 5 tableaux Parquet typés dans `data/processed/` : `movies` (25 389 lignes), `genres` (19), `movie_genres` (60 263), `people` (674 561), `credits` (1 914 840).
- **Mesures :** environ 33 s, environ 400 Mo de RAM au maximum, 589 Mo de JSON bruts pour 81 Mo de Parquet. Aucun doublon de film dans les données de Yannis (25 389 lignes, 25 389 ids).

### 2026-11-10 
- **README réécrit**.
- **Choix :** on garde tout le casting (cast et crew), contrairement à la proposition de la note d'exploration, pour décider ensuite avec Salma. La liste des genres est reconstruite à partir des fiches.
- **Tests :** 8 tests pytest dans `tests/test_transform.py` (0 « inconnus », dates, textes vides, listes dépliées, personne avec deux postes, doublons sur le script complet).
- **Contrat 2 :** `docs/note_transformation.md`, statut « proposition », à valider avec Salma.
 - **Publication sur le Hub :** `scripts/publish/publish.py` crée un dépôt de dataset **privé**, envoie les 153 fichiers Parquet (environ 81 Mo) et la Dataset Card (`scripts/publish/dataset_card.md`), puis pose un tag avec `--tag`. Tag `v1.0.0` posé. Le dataset a été relu depuis le Hub avec `load_dataset(..., revision="v1.0.0")` : les 5 tableaux ont les mêmes nombres de lignes qu'après la transformation.
- **Reste à décider en équipe :** la licence TMDB et le passage en public (les conditions de l'API sont non commerciales, non transférables et non sous-licenciables, la redistribution publique est à clarifier). Le dépôt est sous le compte personnel d'Aida (`NdeyeAidaNdour/tmdb-movies-2000-2026`), donc visible d'elle seule tant qu'il est privé. Il peut etre changé pour une organisation.

### 2026-11-10 (Aida)
- **Décision d'équipe :** le dataset est publié en **public** pour un usage pédagogique non commercial, attribution TMDB dans la Dataset Card.
- **Dépôt hub passé en public**.

### 2026-11-11

- **`git pull`** : récupération du travail d'Aida (transformation Parquet, tests, publication sur le Hub, `docs/note_transformation.md`).
- **`docs/doc_yannis.html` créé** : le pense-bête de Yannis, au style « plan de métro ». Il contient :
  - le lignage cliquable API → JSON Lines → Parquet → PostgreSQL → Hub (survol = d'où viennent les données et ce qu'elles alimentent) ;
  - les chiffres clés et le graphique des films par année ;
  - les 8 stations de l'ingestion, la transformation (normalisation, nettoyage, typage, outils, Parquet vs PostgreSQL), les pièges, le reste à faire et un lexique ;
  - une fiche détaillée (modale) pour chaque élément, et une recherche.

  Rendu vérifié dans Edge (headless). Non commité.

### 2026-11-12

- **Transformation relancée par Yannis sur son poste** (après `pip install -r requirements.txt`). Résultat identique à celui d'Aida : `movies` 25 389, `genres` 19, `movie_genres` 60 263, `people` 674 561, `credits` 1 914 840 lignes ; 38 fichiers par tableau, 80 Mo au total. 25 389 ids uniques. `budget` est vide pour 16 425 films (65 %), `runtime` pour 56.
- **`git pull` du travail de Salma** (pull request #1 `feature/sql-publication`, fusionnée le 2026-11-11) :
  - `sql/schema.sql` : schéma `pipeline`, 5 tables (`movies`, `genres`, `movie_genres`, `people`, `credits`), clés primaires et étrangères, `CHECK` sur `credits.type` ;
  - `scripts/load/load_all_parquet.py` : chargement par lots avec pyarrow + psycopg, `COPY` dans une table temporaire puis `INSERT … ON CONFLICT` (idempotent, vérifié sur deux exécutions). 2 675 072 lignes chargées ;
  - `sql/analyses.sql` : 5 requêtes (top recettes, note par genre, top 5 par année avec `ROW_NUMBER`, réalisateurs, recettes annuelles avec `LAG`) ;
  - `sql/benchmark.sql` : `EXPLAIN ANALYZE` avant/après un index sur `credits(job)`, **plus lent avec l'index** (315 ms contre 917 ms) ;
  - `docs/note_cenception_sql.md` : le rapport.

  **Point à signaler à Salma :** la fiche demande un index *justifié* par `EXPLAIN ANALYZE`. Celui-ci ralentit la requête (28 103 lignes renvoyées, trop pour qu'un index aide). Un index plus sélectif serait à tester, par exemple `credits(person_id)` pour « les films d'un acteur ». `docs/doc_yannis.html` décrit encore la partie SQL comme « à venir ».

### 2026-11-13

- **Relecture de `sql/schema.sql` et de `scripts/load/load_all_parquet.py`** avec Yannis (schéma PostgreSQL, `search_path`, `with`, table temporaire `stage_load`, lecture des colonnes dans le catalogue `pg_attribute`).
- **Trou dans la doc repéré :** rien dans le dépôt n'explique comment préparer la base avant le chargement. Le script suppose que deux étapes manuelles ont déjà été faites :
  1. créer la base `movie_analytics` (PostgreSQL local, port 5433, utilisateur `postgres`) ;
  2. exécuter `sql/schema.sql`, avec pgAdmin ou avec `psql -h localhost -p 5433 -U postgres -d movie_analytics -f sql/schema.sql`.

  Sans elles, le script s'arrête sur « Table cible introuvable ». Le README indique encore « À venir » pour l'étape ③. **À demander à Salma :** ajouter une section « ③ Base SQL » au README avec les commandes qu'elle a réellement utilisées. Les réglages de connexion sont aussi écrits en dur dans le script (`localhost`, `5433`, `postgres`), alors que `.env.example` prévoit `DATABASE_URL`.
- **Idée bonus notée : orchestration avec Airflow sur le VPS privé de Yannis.** Pas demandée par la fiche, à faire une fois l'essentiel fini.
  - Airflow est gratuit (open source, Apache 2.0). Déploiement avec le `docker-compose.yaml` officiel, sur Docker Engine (Linux, gratuit). Un DAG enchaîne les 4 commandes : ingestion, transformation, chargement, publication.
  - Pourquoi le VPS plutôt que le PC Thales : Docker Desktop est payant dans les entreprises de plus de 250 salariés, le proxy du travail bloque TMDB, et le VPS est toujours allumé.
  - À prévoir : au moins 4 Go de RAM libres ; ne pas exposer le port 8080 sur Internet (reverse proxy avec HTTPS, ou tunnel SSH) ; changer le compte par défaut `airflow` / `airflow` ; les secrets dans un `.env` sur le VPS.
  - Interface : celle d'Airflow est peu personnalisable (réglages, plugins). Idée : une page à soi qui appelle l'API REST d'Airflow (lancer le pipeline, état de chaque étape, logs), par exemple le lignage de `doc_yannis.html` coloré selon l'état réel des étapes.
- **`docs/doc_yannis.html` mis à jour** (toujours non commité) :
  - « Ma partie » remplacé par le nom de la partie (« Ingestion ») dans la navbar et les titres ;
  - nouvelle section « La base SQL » (navbar comprise), avec 8 fiches dans l'ordre d'exécution : préparer la base (étape manuelle non documentée), `schema.sql` (schéma, `search_path`), les règles, le chargement, la lecture des colonnes dans le catalogue, la table de transit + `COPY` + upsert, les analyses, l'index ;
  - stations PostgreSQL du plan : plus « à venir », vrais noms de tables et nombres de lignes, résultats des 5 analyses et mesure de l'index ;
  - chiffre ajouté (2,7 M lignes chargées), « Reste à faire » au 13 novembre (base SQL faite ; index et mise en place à signaler à Salma ; idée bonus Airflow) ;
  - lexique : schéma, `search_path`, catalogue, table de transit, `COPY`, transaction, `with`, ETL/ELT, orchestrateur.

  Rendu vérifié dans Edge (headless) : toutes les sections se remplissent, pas d'erreur JavaScript.
- **Relecture complète de `scripts/load/load_all_parquet.py`** avec Yannis, ligne par ligne : tri des colonnes (clé / reste), `ON CONFLICT … DO UPDATE SET … = EXCLUDED…` ou `DO NOTHING`, assemblage de `copy_stmt` et `merge_stmt`, boucle (`iter_batches` → `TRUNCATE` → `COPY` par `write_row` → `INSERT … ON CONFLICT`), contrôle `COUNT(*)`. Remarque de lisibilité pour Salma : `merge_stmt` est écrite avant `copy_stmt` alors qu'elle s'exécute après.
- **`docs/doc_chargement.html` créé** (non commité) : la doc visuelle du script de chargement, pour Yannis. Elle contient :
  - un lignage cliquable en deux zones, « Préparer » (le texte SQL) et « Exécuter » (les données) ;
  - les 14 variables du script avec leur contenu d'exemple ;
  - une simulation pas à pas d'un paquet de 3 films au 2e lancement (mémoire Python → `stage_load` → `pipeline.movies`) ;
  - les 17 étapes, chacune avec un exemple de données, le code et des détails dans des menus déroulants, et une fiche complète au clic ;
  - les questions posées pendant la relecture et les points à signaler à Salma.

  Rendu vérifié dans Edge (headless) : sections remplies, fiche qui s'ouvre au clic.

### 2026-11-15

- **Comparaison du dépôt avec la fiche :** il manquait les tests de l'ingestion, l'index ne se justifie pas (il ralentit la requête), et `data/raw/` est versionné alors que la fiche l'interdit (« `data/` et les secrets ne sont jamais versionnés »). Le README marque encore l'étape ③ « À venir ».
- **`git pull` du commit d'Aida `c888873`** : le dataset est passé en **public** sur le Hub (décision d'équipe : usage pédagogique non commercial, attribution TMDB). Conflit sur `HISTORIQUE.md`, résolu en gardant les deux versions.
- **`tests/test_ingest.py` écrit : 17 tests, sans appel à la vraie API.** Un faux TMDB (`FakeSession`) renvoie les réponses voulues, et `asyncio.sleep` est remplacé pour noter les attentes sans attendre. Les fichiers sont écrits dans un dossier temporaire, jamais dans `data/raw/`. Ce qui est vérifié :
  - nommage déterministe (`year=AAAA.jsonl`), les 12 mois (années bissextiles), JSON Lines (une ligne par objet, accents gardés) ;
  - `get_json` : 200 renvoie le JSON, 404 renvoie `None` sans réessayer, 401 s'arrête tout de suite, 429, timeout et coupure réseau sont réessayés, attente 1, 2, 4, 8 s puis abandon après 5 essais, `Retry-After` respecté ;
  - le sémaphore : 30 requêtes avec 3 places, jamais plus de 3 en même temps ;
  - discover : 500 pages au maximum, ids sans doublon entre les mois ;
  - checkpoint : le `.part` est renommé en `.jsonl` à la fin, un `.part` laissé par une coupure est effacé et l'année refaite, une année déjà finie est sautée.

  `python -m pytest` : **25 tests passent** (17 ingestion + 8 transformation), en 9 s. Non commité.
- **Index remplacé dans `sql/benchmark.sql` : `credits(job)` → `credits(person_id)`.**
  - **Pourquoi :** un index n'aide que si la requête cible peu de lignes. `job = 'Director'` renvoie 28 103 lignes (1,5 % de la table), éparpillées : l'index ralentissait (917 ms contre 315 ms). La filmographie de Christopher Nolan (`person_id = 525`) renvoie **57 lignes sur 1 914 840**, comptées dans les Parquet : c'est le cas où un index évite de lire toute la table. PostgreSQL n'indexe pas les clés étrangères tout seul.
  - **Le script :** supprime les index de test (`DROP INDEX IF EXISTS`), lance `ANALYZE`, mesure sans index, crée `idx_credits_person_id`, mesure avec, puis mesure la même requête jointe à `movies`. Consigne ajoutée : lancer deux fois et garder la 2e mesure (cache froid à la 1re), ce qui explique peut-être en partie l'écart de la mesure de Salma.
  - **Pas encore mesuré :** PostgreSQL ne tourne pas sur le poste de Yannis (port 5433 fermé). La note de Salma (`docs/note_cenception_sql.md`) décrit encore l'ancien index.
- **`data/` retiré du suivi Git** (la fiche : « `data/` et les secrets ne sont jamais versionnés »). Annule la décision du 2026-11-03 / 11-09 de versionner `data/raw/`.
  - `git rm -r --cached data/raw/movies data/raw/discover` : 54 fichiers retirés du suivi, **toujours présents sur le disque** (27 fichiers dans `data/raw/movies/`).
  - `.gitignore` : tout `data/raw/` et `data/processed/` est ignoré, sauf les `.gitkeep` et `data/raw/README.md`.
  - Docs alignées : `data/raw/README.md` (récupérer = relancer l'ingestion), `README.md` (arborescence, phrase sur `data/processed/`), `docs/index.html` (onglet organisation), `CLAUDE.md` (règle du dépôt).
  - **Piège pour l'équipe :** au `git pull` de ce commit, Git **supprimera** `data/raw/movies/` et `data/raw/discover/` chez Aida et Salma, puisque les fichiers disparaissent du dépôt. Elles doivent les copier ailleurs avant de tirer, puis les remettre (ou relancer l'ingestion).
  - **Pas fait :** les ~600 Mo restent dans l'**historique** Git (les anciens commits). Les effacer demanderait de réécrire l'historique et de forcer le push, ce qui casse les copies de l'équipe. Non fait, à décider en équipe.
  - Non commité.
- **Pas de soutenance** finalement (info de Yannis) : la présentation de 10 minutes prévue par la fiche n'est plus à préparer.
- **Commit `3dcabaf` poussé sur `main`** : tests de l'ingestion, nouvel index, retrait de `data/` et docs. `docs/doc_yannis.html` et `docs/doc_chargement.html` restent hors du commit (docs personnelles).
- **Test complet depuis zéro : impossible sur le poste Thales.** TMDB répond `SSLError` (proxy qui inspecte le HTTPS), et ni PostgreSQL ni Docker ne sont installés. Rien n'a été supprimé.
- **`docs/TEST_VPS.md` écrit** : la procédure pour tout relancer sur le VPS de Yannis (Debian/Ubuntu), depuis un clone neuf (sans `data/`, donc page blanche) : ingestion avec mesure durée/RAM et test de reprise, transformation, pytest, PostgreSQL en Docker (port 5433 limité à `127.0.0.1`, base `movie_analytics` créée par `POSTGRES_DB`), `schema.sql`, chargement lancé deux fois (idempotence), analyses, benchmark lancé deux fois, lecture seule du Hub (on ne relance pas `publish.py`, le dataset est public). Valeurs attendues et tableau récapitulatif à remplir. Points faibles relevés : connexion en dur et mot de passe au clavier dans le chargement (bloquant pour Airflow), `publish.py` crée le dépôt en `private=True`. Non commité.
- **README réécrit, plus court** : le dataset publié (lien), les chiffres clés, les 4 étapes en un tableau, l'installation, toutes les commandes (**étape ③ enfin documentée** : `schema.sql`, chargement, analyses, benchmark), la structure, les docs et la licence. La section « Explication ingestion », destinée à Aida, est retirée : elle renvoyait à des données qui ne sont plus dans Git. Non commité.
- **Commit `743d68f` (« finalisation et ajout docs ») poussé sur `main`** : `README.md` réécrit, `docs/TEST_VPS.md`, et l'entrée ci-dessus dans l'historique.
  - **Changement d'avis :** `docs/doc_yannis.html` et `docs/doc_chargement.html` sont finalement **versionnées** dans ce commit, alors que l'entrée du commit `3dcabaf` les laissait hors de Git comme docs personnelles.
  - Ce commit n'avait pas été noté dans l'historique au moment où il a été fait : entrée ajoutée après coup.
- **`data/` vidé sur le poste de Yannis** (changement d'avis : l'entrée du retrait de `data/` disait que les fichiers restaient sur le disque). `data/raw/movies/` n'existe plus et `data/processed/` est vide. Les données se régénèrent avec l'ingestion puis la transformation, ce que fera de toute façon le test sur le VPS. Pas d'effet sur les tests : ceux de l'ingestion comme ceux de la transformation écrivent dans un dossier temporaire (`tmp_path`). Non vérifié ici : pytest n'est pas installé sur ce poste (pas de `.venv`).
- **`docs/TEST_VPS.md` corrigé (étape 4)** : il disait que les tests de transformation lisent `data/processed/`. C'est faux : `test_main_dedoublonne` écrit dans un dossier temporaire (`tmp_path`), et les autres tests de transformation n'écrivent aucun fichier. Non commité.
