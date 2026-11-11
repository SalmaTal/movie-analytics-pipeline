CREATE SCHEMA IF NOT EXISTS pipeline;
SET search_path TO pipeline, public;


--table film :
CREATE TABLE movies (
    id BIGINT PRIMARY KEY,
    imdb_id TEXT,
    title TEXT NOT NULL,
    original_title TEXT,
    original_language TEXT,
    status TEXT,
    overview TEXT,
    tagline TEXT,
    homepage TEXT,
    release_date DATE,
    runtime BIGINT,
    budget BIGINT,
    revenue BIGINT,
    vote_average DOUBLE PRECISION,
    vote_count BIGINT,
    popularity DOUBLE PRECISION,
    adult BOOLEAN,
    collection_id BIGINT
);

--table genres :
CREATE TABLE genres (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL
);

--table film_genre
CREATE TABLE movie_genres (
    movie_id BIGINT NOT NULL REFERENCES movies(id),
    genre_id BIGINT NOT NULL REFERENCES genres(id),
    PRIMARY KEY (movie_id, genre_id)
);

--table personnes
CREATE TABLE people (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    gender BIGINT,
    known_for_department TEXT,
    popularity DOUBLE PRECISION
);


--table credits
CREATE TABLE credits (
    credit_id TEXT PRIMARY KEY,
    movie_id BIGINT NOT NULL REFERENCES movies(id),
    person_id BIGINT NOT NULL REFERENCES people(id),
    type TEXT NOT NULL CHECK (type IN ('cast', 'crew')),
    character TEXT,
    "order" BIGINT,
    job TEXT,
    department TEXT
);