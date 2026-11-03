# Historique du projet

## Où on en est

- **Étape en cours :** ① Récupérer (ingestion), phase d'exploration de l'API TMDB à la main avec Thunder Client.
- **Prochaine action :** partager `docs/note_exploration.md` avec l'équipe pour validation.
- **Décisions en attente :**
  - validation de la note d'exploration (périmètre, langue, fichiers) par Aida et Salma ;
  - garder ou supprimer le script d'ingestion écrit trop tôt (voir le 2026-11-03) ;
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
- **Premier incident Postman :** trois réponses identiques, car l'onglet renvoyait la même requête. Solution : un nouvel onglet par requête, et vérifier l'onglet Params avant d'envoyer.
- **Réseau :** depuis le poste Thales, l'agent ne peut pas appeler l'API TMDB (bloquée par la politique de sécurité). Les requêtes se font dans Thunder Client par Yannis.
