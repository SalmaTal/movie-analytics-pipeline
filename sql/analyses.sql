
-- 1. Les 10 films avec les plus grosses recettes
SELECT title, release_date, revenue
FROM pipeline.movies
WHERE revenue IS NOT NULL
ORDER BY revenue DESC
LIMIT 10;


-- 2. Note moyenne et nombre de films par genre
SELECT
    g.name AS genre,
    COUNT(*) AS nombre_films,
    ROUND(AVG(m.vote_average)::numeric, 2) AS note_moyenne
FROM pipeline.movies m
JOIN pipeline.movie_genres mg ON m.id = mg.movie_id
JOIN pipeline.genres g ON mg.genre_id = g.id
WHERE m.vote_average IS NOT NULL
GROUP BY g.id, g.name
ORDER BY note_moyenne DESC;


-- 3. Classement des 5 films les mieux notés par année
WITH classement AS (
    SELECT
        title,
        EXTRACT(YEAR FROM release_date)::integer AS annee,
        vote_average,
        ROW_NUMBER() OVER (
            PARTITION BY EXTRACT(YEAR FROM release_date)
            ORDER BY vote_average DESC, vote_count DESC, id
        ) AS rang
    FROM pipeline.movies
    WHERE release_date IS NOT NULL
      AND vote_average IS NOT NULL
      AND vote_count >= 100
)
SELECT *
FROM classement
WHERE rang <= 5
ORDER BY annee DESC, rang;


-- 4. Les 10 réalisateurs ayant réalisé le plus de films
SELECT
    p.name AS realisateur,
    COUNT(DISTINCT c.movie_id) AS nombre_films
FROM pipeline.credits c
JOIN pipeline.people p ON p.id = c.person_id
WHERE c.type = 'crew'
  AND c.job = 'Director'
GROUP BY p.id, p.name
ORDER BY nombre_films DESC, realisateur
LIMIT 10;


-- 5. Évolution annuelle des recettes moyennes
WITH recettes_annuelles AS (
    SELECT
        EXTRACT(YEAR FROM release_date)::integer AS annee,
        COUNT(*) AS nombre_films,
        ROUND(AVG(revenue)::numeric, 2) AS recette_moyenne
    FROM pipeline.movies
    WHERE revenue IS NOT NULL
      AND release_date IS NOT NULL
    GROUP BY EXTRACT(YEAR FROM release_date)
)
SELECT
    annee,
    nombre_films,
    recette_moyenne,
    LAG(recette_moyenne) OVER (ORDER BY annee) AS recette_moyenne_annee_precedente,
    recette_moyenne
      - LAG(recette_moyenne) OVER (ORDER BY annee) AS difference
FROM recettes_annuelles
ORDER BY annee;
