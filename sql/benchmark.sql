-- 1. Performance avant création de l'index
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, person_id, job
FROM pipeline.credits
WHERE job = 'Director';

-- 2. Création d'un index sur la colonne job
CREATE INDEX IF NOT EXISTS idx_credits_job
ON pipeline.credits(job);

-- 3. Performance après création de l'index
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, person_id, job
FROM pipeline.credits
WHERE job = 'Director';