
import argparse
import os
import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# Rozdzielczości, dla których przygotowujemy agregację.
SUPPORTED_RESOLUTIONS = (7, 8, 9)

# Liczba warstw BDOT10k powiatu chełmskiego.
EXPECTED_LAYERS = 68

# Oczekiwana liczba heksagonów.
EXPECTED_CELLS = {
    7: 463,
    8: 2909,
    9: 19523,
}


def validate_layer_name(layer_name):
    """Sprawdza bezpieczeństwo nazwy tabeli i kolumny."""

    if not re.fullmatch(r"ot_[a-z0-9]+_[alp]", layer_name):
        raise ValueError(
            f"Nieprawidłowa nazwa warstwy: {layer_name}"
        )


def aggregate_layer(connection, resolution, layer_name, geom_type):
    """
    Agreguje jedną warstwę BDOT10k.

    Punkty: liczba pojedynczych punktów.
    Linie: długość fragmentów w heksagonie [m].
    Poligony: powierzchnia unii fragmentów [m2].

    Każdy wynik dotyczy jednego heksagonu i jednej warstwy.
    """

    validate_layer_name(layer_name)

    if resolution not in SUPPORTED_RESOLUTIONS:
        raise ValueError(
            f"Nieobsługiwana rozdzielczość H3: {resolution}"
        )

    grid_table = f"grid.h3_r{resolution}"
    result_table = f"grid.agregacja_h3_r{resolution}"

    if geom_type == "MULTIPOINT":
        column_type = "BIGINT"

        # ST_Dump rozdziela ewentualne geometrie wielopunktowe.
        # Każdy punkt przypisujemy do maksymalnie jednego heksagonu.
        # Na wspólnej granicy wybieramy najmniejszy h3_id.
        query = f"""
            SELECT
                selected.h3_id,
                COUNT(*)::bigint AS value
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

        # Liczymy tylko odcinki znajdujące się
        # wewnątrz konkretnego heksagonu.
        query = f"""
            SELECT
                h.h3_id,
                SUM(
                    ST_Length(
                        ST_Intersection(h.geom, b.geom)
                    )
                ) AS value

            FROM {grid_table} AS h

            JOIN bdot.{layer_name} AS b
                ON ST_Intersects(h.geom, b.geom)

            GROUP BY h.h3_id
        """

    elif geom_type == "MULTIPOLYGON":
        column_type = "DOUBLE PRECISION"

        # Najpierw przycinamy poligony do heksagonu.
        # Następnie łączymy fragmenty tej samej warstwy.
        # Dzięki temu nakładające się powierzchnie
        # są liczone tylko raz.
        query = f"""
            SELECT
                h.h3_id,

                ST_Area(
                    ST_UnaryUnion(
                        ST_Collect(
                            ST_Intersection(h.geom, b.geom)
                        )
                    )
                ) AS value

            FROM {grid_table} AS h

            JOIN bdot.{layer_name} AS b
                ON ST_Intersects(h.geom, b.geom)

            GROUP BY h.h3_id
        """

    else:
        raise ValueError(
            f"Nieobsługiwany typ geometrii: "
            f"{geom_type} w warstwie {layer_name}"
        )

    # Tworzymy kolumnę tylko wtedy, gdy jeszcze nie istnieje.
    connection.execute(text(f"""
        ALTER TABLE {result_table}
        ADD COLUMN IF NOT EXISTS
        {layer_name} {column_type} DEFAULT 0
    """))

    # Zerujemy stare wyniki, aby ponowne uruchomienie
    # nie powodowało sumowania wartości z poprzedniego przebiegu.
    connection.execute(text(f"""
        UPDATE {result_table}
        SET {layer_name} = 0
    """))

    # Zapisujemy nowe wartości w odpowiednich heksagonach.
    connection.execute(text(f"""
        UPDATE {result_table} AS result

        SET {layer_name} = aggregate.value

        FROM ({query}) AS aggregate

        WHERE result.h3_id = aggregate.h3_id
    """))


def check_input_data(connection, resolution):
    """Sprawdza siatkę źródłową i tabelę wynikową."""

    grid_table = f"grid.h3_r{resolution}"
    result_table = f"grid.agregacja_h3_r{resolution}"

    grid_exists = connection.execute(
        text("SELECT to_regclass(:name)"),
        {"name": grid_table},
    ).scalar_one()

    result_exists = connection.execute(
        text("SELECT to_regclass(:name)"),
        {"name": result_table},
    ).scalar_one()

    if grid_exists is None:
        raise RuntimeError(
            f"Brak siatki źródłowej: {grid_table}"
        )

    if result_exists is None:
        raise RuntimeError(
            f"Brak tabeli wynikowej: {result_table}"
        )

    grid_info = connection.execute(text(f"""
        SELECT
            COUNT(*) AS total,
            COUNT(DISTINCT h3_id) AS unique_ids,
            MIN(ST_SRID(geom)) AS min_srid,
            MAX(ST_SRID(geom)) AS max_srid
        FROM {grid_table}
    """)).one()

    result_info = connection.execute(text(f"""
        SELECT
            COUNT(*) AS total,
            COUNT(DISTINCT h3_id) AS unique_ids,
            MIN(ST_SRID(geom)) AS min_srid,
            MAX(ST_SRID(geom)) AS max_srid
        FROM {result_table}
    """)).one()

    expected = EXPECTED_CELLS[resolution]

    if grid_info.total != expected:
        raise RuntimeError(
            f"H3-{resolution}: siatka ma "
            f"{grid_info.total} zamiast {expected} heksagonów."
        )

    if (
        grid_info.unique_ids != expected
        or result_info.total != expected
        or result_info.unique_ids != expected
    ):
        raise RuntimeError(
            f"H3-{resolution}: niezgodna liczba "
            f"lub identyfikatory heksagonów."
        )

    if (
        grid_info.min_srid != 2180
        or grid_info.max_srid != 2180
    ):
        raise RuntimeError(
            f"H3-{resolution}: siatka musi mieć EPSG:2180."
        )

    if (
        result_info.min_srid != 4326
        or result_info.max_srid != 4326
    ):
        raise RuntimeError(
            f"H3-{resolution}: wynik musi mieć EPSG:4326."
        )

    # Sprawdzenie, czy obie tabele mają te same identyfikatory.
    missing = connection.execute(text(f"""
        SELECT COUNT(*)
        FROM (
            SELECT h3_id FROM {grid_table}
            EXCEPT
            SELECT h3_id FROM {result_table}
        ) AS differences
    """)).scalar_one()

    if missing != 0:
        raise RuntimeError(
            f"H3-{resolution}: niezgodne identyfikatory H3."
        )

    print(
        f"H3-{resolution}: {expected} heksagonów, "
        f"EPSG wejściowy 2180, wynikowy 4326 - OK",
        flush=True,
    )


def check_polygon_results(connection, resolution, layers):
    """
    Sprawdza, czy obliczona powierzchnia każdej warstwy
    nie przekracza powierzchni heksagonu.

    Tolerancja 0.01 m2 służy ograniczeniu wpływu
    drobnych różnic numerycznych.
    """

    result_table = f"grid.agregacja_h3_r{resolution}"
    grid_table = f"grid.h3_r{resolution}"

    for layer_name, geom_type in layers:
        if geom_type != "MULTIPOLYGON":
            continue

        validate_layer_name(layer_name)

        invalid = connection.execute(text(f"""
            SELECT COUNT(*)
            FROM {result_table} AS result
            JOIN {grid_table} AS h USING (h3_id)
            WHERE result.{layer_name} IS NULL
               OR result.{layer_name} < 0
               OR result.{layer_name} >
                  ST_Area(h.geom) + 0.01
        """)).scalar_one()

        if invalid:
            raise RuntimeError(
                f"H3-{resolution}: warstwa {layer_name} "
                f"ma {invalid} nieprawidłowych wartości powierzchni."
            )

    print(
        f"H3-{resolution}: kontrola powierzchni - OK",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Agregacja 68 warstw BDOT10k do siatek H3 "
            "w rozdzielczościach 7, 8 i 9."
        )
    )

    parser.add_argument(
        "--resolutions",
        nargs="+",
        type=int,
        choices=SUPPORTED_RESOLUTIONS,
        default=list(SUPPORTED_RESOLUTIONS),
        help="Rozdzielczości H3 do przetworzenia.",
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Uruchamia agregację. "
            "Bez tej opcji wykonywana jest tylko kontrola."
        ),
    )

    args = parser.parse_args()

    # Dane połączenia pobieramy ze zmiennych środowiskowych.
    # Nie zapisujemy hasła na stałe w skrypcie.
    required = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]

    missing = [
        name for name in required
        if not os.getenv(name)
    ]

    if missing:
        raise RuntimeError(
            "Brak zmiennych środowiskowych: "
            + ", ".join(missing)
        )

    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        database=os.environ["POSTGRES_DB"],
    )

    engine = create_engine(
        url,
        pool_pre_ping=True,
    )

    try:
        # Najpierw sprawdzamy konfigurację.
        with engine.connect() as connection:
            layers = connection.execute(text("""
                SELECT
                    f_table_name,
                    type
                FROM geometry_columns
                WHERE f_table_schema = 'bdot'
                ORDER BY f_table_name
            """)).all()

            if len(layers) != EXPECTED_LAYERS:
                raise RuntimeError(
                    f"Oczekiwano {EXPECTED_LAYERS} warstw, "
                    f"znaleziono {len(layers)}."
                )

            for layer_name, geom_type in layers:
                validate_layer_name(layer_name)

                if geom_type not in (
                    "MULTIPOINT",
                    "MULTILINESTRING",
                    "MULTIPOLYGON",
                ):
                    raise RuntimeError(
                        f"Nieobsługiwana geometria: "
                        f"{layer_name} ({geom_type})"
                    )

            print(
                f"Wykryto {len(layers)} warstw BDOT10k.",
                flush=True,
            )

            for resolution in sorted(set(args.resolutions)):
                check_input_data(connection, resolution)

        if not args.execute:
            print(
                "Kontrola konfiguracji zakończona. "
                "Nie zmieniono danych.",
                flush=True,
            )
            return

        # Właściwa agregacja.
        for resolution in sorted(set(args.resolutions)):
            print(
                f"Rozpoczynam agregację H3-{resolution}.",
                flush=True,
            )

            for index, (layer_name, geom_type) in enumerate(
                layers, start=1
            ):
                # Jedna warstwa = jedna transakcja.
                # W przypadku błędu nie zapisujemy
                # częściowo przeliczonych wartości tej warstwy.
                with engine.begin() as connection:
                    aggregate_layer(
                        connection,
                        resolution,
                        layer_name,
                        geom_type,
                    )

                print(
                    f"H3-{resolution}: "
                    f"{index}/{EXPECTED_LAYERS} - {layer_name}",
                    flush=True,
                )

            # Kontrola końcowa powierzchni.
            with engine.connect() as connection:
                check_polygon_results(
                    connection,
                    resolution,
                    layers,
                )

            print(
                f"H3-{resolution}: agregacja zakończona.",
                flush=True,
            )

        print(
            "Zakończono agregację wszystkich "
            "wybranych rozdzielczości.",
            flush=True,
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
