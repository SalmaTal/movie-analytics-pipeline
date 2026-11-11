from getpass import getpass
from pathlib import Path

import psycopg
import pyarrow.parquet as pq
from psycopg import sql

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "processed"
BATCH_SIZE = 5000

# L'ordre respecte les clés étrangères : les tables parentes d'abord.
TABLES = ("genres", "movies", "people", "movie_genres", "credits")


def load_table(conn: psycopg.Connection, table_name: str) -> int:
    directory = DATA_DIR / table_name
    paths = sorted(directory.glob("*.parquet"))
    if not paths:
        raise FileNotFoundError(f"Aucun fichier Parquet dans {directory}")

    destination = sql.Identifier("pipeline", table_name)
    # La table temporaire prend les mêmes colonnes et types que la table cible,
    # mais pas ses contraintes uniques / de clés étrangères.
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("CREATE TEMP TABLE stage_load (LIKE {} EXCLUDING ALL) ON COMMIT DROP").format(destination)
        )
        cur.execute(
            """SELECT a.attname
               FROM pg_attribute AS a
               JOIN pg_class AS c ON a.attrelid = c.oid
               JOIN pg_namespace AS n ON c.relnamespace = n.oid
              WHERE n.nspname = 'pipeline' AND c.relname = %s
                AND a.attnum > 0 AND NOT a.attisdropped
              ORDER BY a.attnum""",
            (table_name,),
        )
        columns = [row[0] for row in cur.fetchall()]
        if not columns:
            raise ValueError(f"Table cible introuvable : pipeline.{table_name}")

        column_names = sql.SQL(", ").join(map(sql.Identifier, columns))
        pk_cols = {"movies": ["id"], "genres": ["id"], "people": ["id"],
                   "movie_genres": ["movie_id", "genre_id"], "credits": ["credit_id"]}[table_name]
        conflict_columns = sql.SQL(", ").join(map(sql.Identifier, pk_cols))
        other_cols = [name for name in columns if name not in pk_cols]
        if other_cols:
            assignments = sql.SQL(", ").join(
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(name), sql.Identifier(name))
                for name in other_cols
            )
            on_conflict = sql.SQL("DO UPDATE SET ") + assignments
        else:
            on_conflict = sql.SQL("DO NOTHING")

        # SELECT ... WHERE true résout l'ambiguïté SQL de ON CONFLICT après SELECT.
        merge_stmt = sql.SQL(
            "INSERT INTO {} ({}) SELECT {} FROM stage_load WHERE true "
            "ON CONFLICT ({}) {}"
        ).format(destination, column_names, column_names, conflict_columns, on_conflict)
        copy_stmt = sql.SQL("COPY stage_load ({}) FROM STDIN").format(column_names)

        processed = 0
        for file_path in paths:
            parquet = pq.ParquetFile(file_path)
            available = set(parquet.schema_arrow.names)
            missing = set(columns) - available
            if missing:
                raise ValueError(f"Colonnes manquantes dans {file_path.name}: {sorted(missing)}")

            for record_batch in parquet.iter_batches(batch_size=BATCH_SIZE, columns=columns):
                # Evite de charger tous les crédits (presque 2 millions) en mémoire.
                rows = record_batch.to_pylist()
                cur.execute("TRUNCATE stage_load")
                with cur.copy(copy_stmt) as copy:
                    for record in rows:
                        copy.write_row(tuple(record[col] for col in columns))
                cur.execute(merge_stmt)
                processed += len(rows)
            print(f"  {table_name}: {file_path.name} terminé", flush=True)

        # Une seule transaction par table, validée ici si pas d'erreur.
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(destination))
        total_in_db = cur.fetchone()[0]
        print(f"{table_name} : {processed} lignes traitées ; {total_in_db} lignes en base", flush=True)
    return processed


def main():
    print("Chargement Parquet -> PostgreSQL (schema pipeline)")
    print(f"Source : {DATA_DIR}")
    password = getpass("Mot de passe PostgreSQL : ")
    for name in TABLES:
        # Connexion / transaction séparée pour chaque table : en cas d'échec,
        # les tables déjà chargées restent validées et la relance est sûre.
        with psycopg.connect(
            host="localhost",
            port=5433,
            dbname="movie_analytics",
            user="postgres",
            password=password,
        ) as conn:
            load_table(conn, name)
    print("Chargement des cinq tables terminé.")


if __name__ == "__main__":
    main()