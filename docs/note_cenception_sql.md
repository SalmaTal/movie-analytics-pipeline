# Rapport technique — Partie C : PostgreSQL et analyses SQL

**Projet :** Movie Analytics Pipeline  
**Formation :** M1 Expert en IA — Ynov  
**Partie réalisée :** Modélisation PostgreSQL, chargement des données et analyses SQL

## 1. Objectif

L'objectif de cette partie était de récupérer les données Parquet produites lors de l'étape de transformation, de les charger dans une base PostgreSQL et de réaliser des analyses SQL sur les films.

Nous devions également vérifier la cohérence des données, éviter les doublons lors des chargements et analyser les performances des requêtes.

## 2. Création de la base PostgreSQL

Nous avons créé une base de données `movie_analytics` et un schéma `pipeline` contenant cinq tables :

- **movies** : informations générales sur les films.
- **genres** : liste des genres cinématographiques.
- **movie_genres** : association entre films et genres.
- **people** : informations sur les personnes.
- **credits** : acteurs et membres des équipes techniques.

Nous avons défini les clés primaires et étrangères pour assurer les relations entre les tables et garantir l'intégrité référentielle.

## 3. Chargement des données Parquet

Nous avons développé un script Python, `load_all_parquet.py`, utilisant `PyArrow` pour lire les fichiers Parquet et `psycopg` pour communiquer avec PostgreSQL.

Le chargement s'effectue par lots et respecte l'ordre des dépendances entre les tables.

Les résultats obtenus sont :

| Table | Nombre de lignes |
|---|---:|
| movies | 25 389 |
| genres | 19 |
| movie_genres | 60 263 |
| people | 674 561 |
| credits | 1 914 840 |
| **Total** | **2 675 072** |

Les cinq tables ont été chargées et leurs nombres de lignes correspondent aux volumes attendus.

Nous avons également testé l'**idempotence** en exécutant le chargement une deuxième fois. Les nombres de lignes sont restés identiques, ce qui confirme l'absence de doublons supplémentaires.

## 4. Analyses SQL réalisées

Nous avons créé un fichier `analyses.sql` contenant cinq analyses :

1. **Films avec les recettes les plus élevées :** classement des dix films générant le plus de revenus dans le jeu de données.
2. **Notes moyennes par genre :** comparaison des genres selon le nombre de films et leur note moyenne.
3. **Meilleurs films par année :** classement annuel des cinq films les mieux notés, avec `ROW_NUMBER()`.
4. **Réalisateurs les plus présents :** identification des dix réalisateurs ayant réalisé le plus de films dans le jeu de données.
5. **Évolution annuelle des recettes :** comparaison des recettes moyennes d'une année à l'autre avec `LAG()`.

Les cinq requêtes ont été exécutées avec succès.

**Quelques résultats :**

- Le genre *Documentary* présente la note moyenne la plus élevée : **7,06/10**, pour 1 420 films.
- Le genre *Animation* arrive ensuite avec **6,93/10**, pour 2 112 films.
- Le réalisateur le plus représenté est **Takashi Miike**, avec 34 films, suivi de Tyler Perry avec 31 films.

Ces résultats concernent uniquement le jeu de données utilisé et dépendent des informations disponibles dans TMDB.

## 5. Analyse des performances

Nous avons utilisé `EXPLAIN ANALYZE` pour étudier les performances d'une requête recherchant les crédits dont le poste est `Director`.

Nous avons comparé l'exécution avant et après la création d'un index sur la colonne `job`.

| Indicateur | Sans index | Avec index |
|---|---|---|
| Plan d'exécution | Parallel Seq Scan | Bitmap Index Scan + Bitmap Heap Scan |
| Lignes retournées | 28 103 | 28 103 |
| Temps d'exécution | 314,858 ms | 917,063 ms |

Dans cette mesure, la requête avec index était environ **2,9 fois plus lente**.

Ce résultat montre qu'un index n'améliore pas systématiquement les performances. Il dépend notamment du plan choisi par PostgreSQL et des accès aux données. Plusieurs exécutions seraient nécessaires pour confirmer cette différence.

## 6. Conclusion

Cette partie du projet nous a permis de construire une base PostgreSQL relationnelle à partir de fichiers Parquet et d'exploiter les données avec des requêtes SQL avancées.

Nous avons réussi à charger **2 675 072 lignes**, à vérifier les volumes des cinq tables et à confirmer l'idempotence du chargement sur deux exécutions.

Nous avons également réalisé cinq analyses SQL et un premier test d'optimisation.

Ce travail complète la partie stockage et analyse du pipeline et prépare les données pour leur exploitation et leur publication éventuelle.