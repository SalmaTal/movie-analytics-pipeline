--table film :
CREATE TABLE films (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    release_date DATE,
    runtime INTEGER,
    budget BIGINT,
    revenue BIGINT,
    vote_average NUMERIC(5,3),
    vote_count INTEGER,
    popularity DOUBLE PRECISION
);

--table genres :
CREATE TABLE genres (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

--table film_genre
CREATE TABLE film_genres (
    film_id INTEGER REFERENCES films(id),
    genre_id INTEGER REFERENCES genres(id),
    PRIMARY KEY (film_id, genre_id)
);

--table personnes
CREATE TABLE personnes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    original_name TEXT,
    gender INTEGER,
    known_for_department TEXT
);

--table casting
CREATE TABLE casting (
    credit_id TEXT PRIMARY KEY,
    film_id INTEGER NOT NULL REFERENCES films(id),
    personne_id INTEGER NOT NULL REFERENCES personnes(id),
    character_name TEXT,
    cast_order INTEGER
);

--table équipe_technique
CREATE TABLE equipe_technique (
    credit_id TEXT PRIMARY KEY,
    film_id INTEGER NOT NULL REFERENCES films(id),
    personne_id INTEGER NOT NULL REFERENCES personnes(id),
    job TEXT,
    department TEXT
);