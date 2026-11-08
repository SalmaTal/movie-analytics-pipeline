# Consignes pour l'agent

Projet d'école (Ynov, groupe de 3) : pipeline TMDB → JSON Lines → Parquet → PostgreSQL → Hugging Face Hub.

## À lire en début de session

- `docs/index.html` : la doc principale, sous forme de petit site à onglets (navbar et menus déroulants). On y trouve le récap du projet, les 4 étapes, l'API TMDB (bases, endpoints, carte des données, pièges), le cadrage, l'équipe et le lexique.
- `docs/HISTORIQUE.md` : où on en est, ce qui a été fait et décidé.
- `fiche_projet_pipeline_donnees.pdf` : la fiche de la prof, qui fait foi en cas de doute.

## Tenir l'historique

Après chaque avancement (étape franchie, décision prise, fichier créé ou modifié, résultat d'exploration), mettre à jour `docs/HISTORIQUE.md` :
- ajouter une entrée datée en bas du journal, sous le titre du jour (`### AAAA-MM-JJ`) ;
- mettre à jour la section « Où on en est » en haut (étape en cours, prochaine action, décisions en attente) ;
- être factuel : ce qui a été fait, testé ou décidé, et ce qui ne l'a pas été.

Quand une explication ou une décision a valeur de référence (rôles, étapes, périmètre, champs retenus, statut d'une étape), mettre aussi à jour `docs/index.html`. Chaque onglet est un `<article class="tab" id="..." data-group="..." data-title="...">`. Un nouvel onglet doit aussi être ajouté dans le menu déroulant correspondant de la navbar.

## Comment travailler avec Yannis

- Yannis débute en data et s'occupe de l'ingestion (rôle A).
- Une étape à la fois. Toujours expliquer le pourquoi avant le comment.
- Faire un rappel léger (une ligne) de ce qui précède et de ce qui suit.
- Ne pas écrire ni modifier de code sans un feu vert explicite : discuter d'abord.
- Méthode de travail pour le code, une étape à la fois :
  1. expliquer ce que fait l'étape et pourquoi ;
  2. écrire le code, avec des commentaires ;
  3. s'arrêter pour laisser Yannis le lire et poser ses questions ;
  4. attendre qu'il dise de passer à la suite. Ne jamais enchaîner plusieurs étapes.
- Yannis avance sans attendre la validation de l'équipe, et l'informe ensuite.
- Écrire en français.

## Règles du dépôt

- Ne jamais écrire de secret (clé TMDB, jeton HF, mot de passe) dans un fichier versionné : seulement dans `.env`, ignoré par Git.
- `data/raw/` (les JSON bruts récupérés) est versionné : décision de Yannis, pour que l'équipe récupère les données avec `git pull`. `data/raw/essais/` et `data/processed/` ne le sont pas.
- Ne pas commiter ni pousser sans demande explicite.
