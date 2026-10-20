
import os
import subprocess
from pathlib import Path

from sqlalchemy import URL, create_engine, text

from h3_generator import generate_grid, read_boundary


def main():
    shapefile = Path("/data/powiat.shp")

    if not shapefile.exists():
        raise FileNotFoundError(
            f"Nie znaleziono pliku: {shapefile}"
        )

    # Parametry polaczenia z PostgreSQL
    environment = os.environ.copy()
    environment.setdefault("PGHOST", "postgis")
    environment.setdefault("PGPORT", "5432")
    environment.setdefault("PGDATABASE", "psip")
    environment.setdefault("PGUSER", "psip")

    if not environment.get("PGPASSWORD"):
        raise ValueError("Brak zmiennej PGPASSWORD")

    resolutions = sorted({
        int(value.strip())
        for value in os.getenv(
            "H3_RESOLUTIONS", "7,8,9"
        ).split(",")
        if value.strip()
    })

    if not resolutions or any(
        r < 0 or r > 15 for r in resolutions
    ):
        raise ValueError(
            "Rozdzielczosci H3 musza byc w zakresie 0-15."
        )

    # 1. Import granicy powiatu
    command = [
        "ogr2ogr",
        "-f", "PostgreSQL",
        "PG:",
        str(shapefile),
        "-nln", "public.powiat",
        "-lco", "GEOMETRY_NAME=geom",
        "-overwrite",
    ]

    subprocess.run(
        command,
        env=environment,
        check=True
    )

    print(
        "Zaladowano powiat do public.powiat.",
        flush=True
    )

    # 2. Generowanie siatek H3
    boundary = read_boundary(shapefile)
    grids = {}

    for resolution in resolutions:
        print(
            f"Generowanie H3: {resolution}",
            flush=True
        )

        grid = generate_grid(
            boundary, resolution
        )

        grid = grid.to_crs(
            epsg=2180
        ).rename_geometry("geom")

        grid["area_m2"] = grid.geometry.area

        grids[resolution] = grid

    # 3. Polaczenie z PostGIS
    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=environment["PGUSER"],
        password=environment["PGPASSWORD"],
        host=environment["PGHOST"],
        port=int(environment["PGPORT"]),
        database=environment["PGDATABASE"],
    )

    engine = create_engine(
        connection_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 15},
    )

    try:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS grid")
            )

            for resolution, grid in grids.items():
                table_name = f"h3_r{resolution}"

                grid.to_postgis(
                    name=table_name,
                    con=connection,
                    schema="grid",
                    if_exists="replace",
                    index=False,
                    chunksize=1000,
                )

                connection.execute(
                    text(
                        f'ALTER TABLE grid."{table_name}" '
                        "ADD PRIMARY KEY (h3_id)"
                    )
                )

                count = connection.execute(
                    text(
                        f'SELECT COUNT(*) '
                        f'FROM grid."{table_name}"'
                    )
                ).scalar_one()

                if count != len(grid):
                    raise RuntimeError(
                        f"Niepelny zapis {table_name}"
                    )

                print(
                    f"OK: grid.{table_name} "
                    f"- {count} heksagonow",
                    flush=True,
                )

    finally:
        engine.dispose()

    print(
        "Import siatek H3 zakonczony.",
        flush=True,
    )


if __name__ == "__main__":
    main()
