-- Benchmark d'index : la filmographie d'une personne dans pipeline.credits
--
-- Pourquoi cet index et pas celui sur credits(job) :
--   un index n'aide que si la requête cible PEU de lignes dans une grosse table.
--   - job = 'Director' renvoie 28 103 lignes éparpillées dans toute la table :
--     PostgreSQL lit presque toutes les pages de toute façon, et l'index ajoute
--     des allers-retours. Mesuré : plus lent avec l'index (917 ms contre 315 ms).
--   - person_id = 525 (Christopher Nolan) renvoie une centaine de lignes
--     sur 1,9 million : sans index, PostgreSQL lit toute la table ; avec l'index,
--     il va directement aux bonnes lignes.
--
-- Lancer avec psql (le \timing n'est pas nécessaire, EXPLAIN ANALYZE donne les temps) :
--   psql -h localhost -p 5433 -U postgres -d movie_analytics -f sql/benchmark.sql
--
-- Pour une mesure honnête : lancer le script deux fois et garder la 2e mesure.
-- La 1re exécution lit le disque (cache froid), les suivantes la mémoire.


-- 0. Point de départ propre : on retire les index de test s'ils existent déjà,
--    et on met à jour les statistiques que PostgreSQL utilise pour choisir son plan.
DROP INDEX IF EXISTS pipeline.idx_credits_job;
DROP INDEX IF EXISTS pipeline.idx_credits_person_id;
ANALYZE pipeline.credits;


-- 1. Avant l'index : PostgreSQL doit parcourir toute la table (Seq Scan)
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, type, character, job
FROM pipeline.credits
WHERE person_id = 525;


-- 2. Création de l'index sur person_id
--    Remarque : PostgreSQL crée un index pour chaque clé primaire,
--    mais PAS pour les clés étrangères comme person_id. Il faut le faire soi-même.
CREATE INDEX idx_credits_person_id
ON pipeline.credits (person_id);
ANALYZE pipeline.credits;


-- 3. Après l'index : PostgreSQL va directement aux lignes (Index Scan ou Bitmap Index Scan)
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, type, character, job
FROM pipeline.credits
WHERE person_id = 525;


-- 4. Même requête avec le titre des films : la jointure profite aussi de l'index
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.title, m.release_date, c.type, c.job
FROM pipeline.credits AS c
JOIN pipeline.movies AS m ON m.id = c.movie_id
WHERE c.person_id = 525
ORDER BY m.release_date;
