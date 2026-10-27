
import argparse
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def aggregate_layer(connection, resolution, layer_name, geom_type):
    """Agreguje jedną warstwę BDOT10k do siatki H3."""

    grid_table = f"grid.h3_r{resolution}"
    result_table = f"grid.agregacja_h3_r{resolution}"

    # Nazwy pochodzą z bazy danych, ale dodatkowo je sprawdzamy.
    if not layer_name.startswith("ot_") or not layer_name.replace("_", "").isalnum():
        raise ValueError(f"Nieprawidłowa nazwa warstwy: {layer_name}")

    if geom_type == "MULTIPOINT":
        column_type = "BIGINT"
        query = f"""
            SELECT selected.h3_id, COUNT(*)::bigint AS value
            FROM bdot.{layer_name} AS b
            CROSS JOIN LATERAL ST_Dump(b.geom) AS p
            CROSS JOIN LATERAL (
                SELECT h.h3_id
                FROM {grid_table} AS h
                WHERE ST_Covers(h.geom, p.geom)
                ORDER BY h.h3_id
                LIMIT 1
            ) AS selected
            GROUP BY selected.h3_id
        """

    elif geom_type == "MULTILINESTRING":
        column_type = "DOUBLE PRECISION"
        query = f"""
            SELECT h.h3_id,
                   SUM(ST_Length(ST_Intersection(h.geom, b.geom))) AS value
            FROM {grid_table} AS h
            JOIN bdot.{layer_name} AS b
              ON ST_Intersects(h.geom, b.geom)
            GROUP BY h.h3_id
        """

    elif geom_type == "MULTIPOLYGON":
        column_type = "DOUBLE PRECISION"
        query = f"""
            SELECT h.h3_id,
                   SUM(ST_Area(ST_Intersection(h.geom, b.geom))) AS value
            FROM {grid_table} AS h
            JOIN bdot.{layer_name} AS b
              ON ST_Intersects(h.geom, b.geom)
            GROUP BY h.h3_id
        """

    else:
        raise ValueError(f"Nieobsługiwany typ geometrii: {geom_type}")

    connection.execute(text(f"""
        ALTER TABLE {result_table}
        ADD COLUMN IF NOT EXISTS {layer_name} {column_type} DEFAULT 0
    """))

    connection.execute(text(f"""
        UPDATE {result_table}
        SET {layer_name} = 0
    """))

    connection.execute(text(f"""
        UPDATE {result_table} AS result
        SET {layer_name} = aggregate.value
        FROM ({query}) AS aggregate
        WHERE result.h3_id = aggregate.h3_id
    """))


def main():
    parser = argparse.ArgumentParser(
        description="Agregacja warstw BDOT10k do siatek H3"
    )
    parser.add_argument(
        "--resolutions",
        nargs="+",
        type=int,
        choices=[7, 8, 9],
        default=[7, 8, 9],
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Wykonaj agregację. Bez tej opcji tylko sprawdzamy konfigurację.",
    )
    args = parser.parse_args()

    required = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]

    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Brak zmiennych środowiskowych: " + ", ".join(missing)
        )

    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        database=os.environ["POSTGRES_DB"],
    )

    engine = create_engine(url)

    with engine.connect() as connection:
        layers = connection.execute(text("""
            SELECT f_table_name, type
            FROM geometry_columns
            WHERE f_table_schema = 'bdot'
            ORDER BY f_table_name
        """)).all()

        if len(layers) != 68:
            raise RuntimeError(
                f"Oczekiwano 68 warstw BDOT10k, znaleziono {len(layers)}."
            )

        for resolution in sorted(set(args.resolutions)):
            grid_name = f"grid.h3_r{resolution}"
            result_name = f"grid.agregacja_h3_r{resolution}"

            count = connection.execute(
                text(f"SELECT COUNT(*) FROM {grid_name}")
            ).scalar_one()

            result_exists = connection.execute(
                text("SELECT to_regclass(:table_name)"),
                {"table_name": result_name},
            ).scalar_one()

            print(
                f"H3-{resolution}: {count} heksagonów, "
                f"68 warstw, tabela wynikowa: {result_name}, "
                f"istnieje: {result_exists is not None}",
                flush=True,
            )

            if not args.execute:
                continue

            if result_exists is None:
                raise RuntimeError(
                    f"Brak tabeli wynikowej: {result_name}"
                )

            for index, (layer_name, geom_type) in enumerate(layers, 1):
                with engine.begin() as transaction:
                    aggregate_layer(
                        transaction,
                        resolution,
                        layer_name,
                        geom_type,
                    )
                print(
                    f"H3-{resolution}: {index}/68 - {layer_name}",
                    flush=True,
                )

    print(
        "Kontrola konfiguracji zakończona."
        if not args.execute
        else "Agregacja zakończona.",
        flush=True,
    )


if __name__ == "__main__":
    main()
