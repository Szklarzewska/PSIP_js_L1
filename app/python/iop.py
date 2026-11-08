
import argparse
import os
import re
from decimal import Decimal

from sqlalchemy import URL, create_engine, text

from iop_weights import WAGI_IVRF, sprawdz_wagi


# ============================================================
# KONFIGURACJA PROJEKTU
# ============================================================

RESOLUTIONS = {
    7: 463,
    8: 2909,
    9: 19523,
}

EXPECTED_LAYERS = 68

RESULT_COLUMN = "wsp_iop_norm"
COUNT_COLUMN = "liczba_klas_iop"


# ============================================================
# NAZWY TABEL
# ============================================================

def get_tables(resolution):

    grid = f"grid.h3_r{resolution}"
    aggregation = f"grid.agregacja_h3_r{resolution}"
    normalization = f"grid.iop_h3_r{resolution}"

    return grid, aggregation, normalization


# ============================================================
# POLACZENIE Z POSTGIS
# ============================================================

def create_database_engine():

    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )

    return create_engine(url, pool_pre_ping=True)


# ============================================================
# KONTROLA WAG IVRF
# ============================================================

def validate_weights():

    sprawdz_wagi()

    if len(WAGI_IVRF) != EXPECTED_LAYERS:
        raise RuntimeError("Nieprawidlowa liczba wag IVRF")

    names = []

    for name, weight, _, _ in WAGI_IVRF:

        if not re.fullmatch(r"ot_[a-z0-9_]+", name):
            raise ValueError(
                f"Nieprawidlowa nazwa warstwy: {name}"
            )

        value = Decimal(str(weight))

        if not Decimal("-1") <= value <= Decimal("1"):
            raise ValueError(
                f"Waga poza zakresem: {name}"
            )

        names.append(name)

    if len(set(names)) != EXPECTED_LAYERS:
        raise RuntimeError(
            "Wykryto powtarzajace sie warstwy"
        )

    return names


# ============================================================
# ODCZYT KOLUMN TABELI
# ============================================================

def get_columns(connection, table):

    schema, table_name = table.split(".")

    columns = connection.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table_name
        """),
        {
            "schema": schema,
            "table_name": table_name,
        },
    ).scalars().all()

    return set(columns)


# ============================================================
# KONTROLA TABELI I IDENTYFIKATOROW
# ============================================================

def check_table(connection, table, expected):

    exists = connection.execute(
        text("SELECT to_regclass(:table_name)"),
        {"table_name": table},
    ).scalar_one()

    if exists is None:
        raise RuntimeError(
            f"Nie znaleziono tabeli: {table}"
        )

    stats = connection.execute(
        text(f"""
            SELECT
                COUNT(*) AS total,
                COUNT(DISTINCT h3_id) AS unique_ids,
                COUNT(*) FILTER (
                    WHERE h3_id IS NULL
                ) AS null_ids
            FROM {table}
        """)
    ).one()

    if stats.total != expected:
        raise RuntimeError(
            f"{table}: {stats.total} rekordow, "
            f"oczekiwano {expected}"
        )

    if stats.unique_ids != expected or stats.null_ids:
        raise RuntimeError(
            f"{table}: zduplikowane lub puste h3_id"
        )


def check_identifiers(connection, left, right):

    differences = connection.execute(
        text(f"""
            SELECT COUNT(*)
            FROM (
                (
                    SELECT h3_id FROM {left}
                    EXCEPT
                    SELECT h3_id FROM {right}
                )

                UNION ALL

                (
                    SELECT h3_id FROM {right}
                    EXCEPT
                    SELECT h3_id FROM {left}
                )
            ) AS differences
        """)
    ).scalar_one()

    if differences != 0:
        raise RuntimeError(
            f"Niezgodne identyfikatory: {left}, {right}"
        )


# ============================================================
# KONTROLA NORMALIZACJI
# ============================================================

def check_normalization(connection, resolution, names):

    _, _, norm = get_tables(resolution)

    columns = get_columns(connection, norm)

    expected_columns = {
        f"n_{name}" for name in names
    }

    missing = expected_columns - columns

    if missing:
        raise RuntimeError(
            f"{norm}: brak kolumn {sorted(missing)}"
        )

    conditions = []

    for name in names:

        conditions.append(
            f'("n_{name}" IS NULL '
            f'OR "n_{name}" < 0 '
            f'OR "n_{name}" > 1)'
        )

    condition_sql = " OR ".join(conditions)

    invalid = connection.execute(
        text(f"""
            SELECT COUNT(*)
            FROM {norm}
            WHERE {condition_sql}
        """)
    ).scalar_one()

    if invalid:
        raise RuntimeError(
            f"{norm}: {invalid} blednych rekordow"
        )

    incorrect_resolution = connection.execute(
        text(f"""
            SELECT COUNT(*)
            FROM {norm}
            WHERE resolution IS DISTINCT FROM :resolution
        """),
        {"resolution": resolution},
    ).scalar_one()

    if incorrect_resolution:
        raise RuntimeError(
            f"{norm}: {incorrect_resolution} rekordow "
            "ma nieprawidlowa rozdzielczosc"
        )


# ============================================================
# KONTROLA DANYCH DLA WYBRANEJ ROZDZIELCZOSCI
# ============================================================

def check_resolution(
    connection,
    resolution,
    names,
    require_normalization=True,
):

    expected = RESOLUTIONS[resolution]

    grid, aggregation, normalization = get_tables(
        resolution
    )

    check_table(connection, grid, expected)
    check_table(connection, aggregation, expected)

    check_identifiers(
        connection, grid, aggregation
    )

    agg_columns = get_columns(
        connection, aggregation
    )

    missing = set(names) - agg_columns

    if missing:
        raise RuntimeError(
            f"Brak kolumn agregacji: {sorted(missing)}"
        )

    if require_normalization:

        check_table(
            connection, normalization, expected
        )

        check_identifiers(
            connection, grid, normalization
        )

        check_normalization(
            connection, resolution, names
        )

    print(
        f"H3-{resolution}: {expected} heksagonow "
        "- kontrola OK",
        flush=True,
    )


# ============================================================
# NORMALIZACJA 68 WARSTW BDOT10K
# ============================================================

def normalize(connection, resolution, names):

    grid, aggregation, normalization = get_tables(
        resolution
    )

    check_resolution(
        connection,
        resolution,
        names,
        require_normalization=False,
    )

    exists = connection.execute(
        text("SELECT to_regclass(:table_name)"),
        {"table_name": normalization},
    ).scalar_one()

    if exists is not None:
        raise RuntimeError(
            f"{normalization} juz istnieje. "
            "Nie nadpisano danych."
        )

    # Maksimum kazdej warstwy w danej rozdzielczosci.

    maxima = []

    for name in names:
        maxima.append(
            f'MAX(a."{name}") AS "{name}"'
        )

    maxima_sql = ",\n".join(maxima)

    # Normalizacja:
    # K_i = wartosc / maksimum
    # Wynik zapisujemy do 2 miejsc po przecinku.

    normalized = []

    for name in names:

        normalized.append(
            f'ROUND('
            f'COALESCE('
            f'a."{name}"::numeric / '
            f'NULLIF(m."{name}"::numeric, 0), '
            f'0.0), 2'
            f')::numeric(3,2) AS "n_{name}"'
        )

    normalized_sql = ",\n".join(normalized)

    sql = f"""
        CREATE TABLE {normalization} AS

        WITH maxima AS (
            SELECT
                {maxima_sql}
            FROM {aggregation} AS a
        )

        SELECT
            h.h3_id,
            {resolution}::integer AS resolution,
            h.geom,
            {normalized_sql}

        FROM {grid} AS h

        JOIN {aggregation} AS a
            ON h.h3_id = a.h3_id

        CROSS JOIN maxima AS m
    """

    connection.execute(text(sql))

    check_table(
        connection,
        normalization,
        RESOLUTIONS[resolution],
    )

    check_normalization(
        connection, resolution, names
    )

    connection.execute(
        text(
            f"ALTER TABLE {normalization} "
            "ADD PRIMARY KEY (h3_id)"
        )
    )

    connection.execute(
        text(
            f"CREATE INDEX iop_h3_r{resolution}_geom_idx "
            f"ON {normalization} USING GIST (geom)"
        )
    )

    print(
        f"H3-{resolution}: normalizacja zakonczona",
        flush=True,
    )


# ============================================================
# OBLICZENIE WSKAZNIKA PRZEJEZDNOSCI IOP
# ============================================================

def calculate_iop(connection, resolution, names):

    grid, aggregation, normalization = get_tables(
        resolution
    )

    expected = RESOLUTIONS[resolution]

    check_resolution(
        connection,
        resolution,
        names,
        require_normalization=True,
    )

    # --------------------------------------------------------
    # 1. LICZBA KLAS OBIEKTOW W HEKSAGONIE
    # --------------------------------------------------------

    # Warstwa wystepuje, gdy agregacja > 0.
    # Klasy neutralne sa obecnie rowniez liczone.
    # Korzystamy z oryginalnej agregacji, nie z
    # zaokraglonych wartosci normalizacji.

    count_parts = []

    for name in names:

        count_parts.append(
            f'CASE WHEN a."{name}" > 0 '
            f'THEN 1 ELSE 0 END'
        )

    count_sql = " +\n".join(count_parts)

    # --------------------------------------------------------
    # 2. SUMA WAZONA
    # --------------------------------------------------------

    weighted_parts = []

    for name, weight, _, _ in WAGI_IVRF:

        value = Decimal(str(weight))

        weighted_parts.append(
            f'(n."n_{name}" * {value:.2f})'
        )

    weighted_sql = " +\n".join(weighted_parts)

    # --------------------------------------------------------
    # 3. KOLUMNY W TABELI HEKSAGONOW
    # --------------------------------------------------------

    connection.execute(
        text(
            f"ALTER TABLE {grid} "
            f"ADD COLUMN IF NOT EXISTS "
            f"{COUNT_COLUMN} integer"
        )
    )

    connection.execute(
        text(
            f"ALTER TABLE {grid} "
            f"ADD COLUMN IF NOT EXISTS "
            f"{RESULT_COLUMN} numeric(3,2)"
        )
    )

    # --------------------------------------------------------
    # 4. OBLICZENIA DLA KAZDEGO HEKSAGONU
    # --------------------------------------------------------

    # IOP_h = SUM(w_i * K_i) / liczba_klas_iop
    #
    # Dla heksagonow bez klas przyjmujemy 0.00.
    # Jest to dotychczasowe zalozenie projektu,
    # ktore wymaga pozniejszej oceny metodycznej.

    sql = f"""
        WITH obliczenia AS (

            SELECT
                h.h3_id,

                ({count_sql}) AS liczba_klas,

                ({weighted_sql}) AS suma_wazona

            FROM {grid} AS h

            JOIN {aggregation} AS a
                ON h.h3_id = a.h3_id

            JOIN {normalization} AS n
                ON h.h3_id = n.h3_id
        )

        UPDATE {grid} AS h

        SET
            {COUNT_COLUMN} = o.liczba_klas,

            {RESULT_COLUMN} = ROUND(
                CASE
                    WHEN o.liczba_klas > 0
                    THEN o.suma_wazona / o.liczba_klas
                    ELSE 0.00
                END,
                2
            )

        FROM obliczenia AS o

        WHERE h.h3_id = o.h3_id
    """

    result = connection.execute(text(sql))

    if result.rowcount != expected:
        raise RuntimeError(
            f"H3-{resolution}: nie przeliczono "
            "wszystkich heksagonow"
        )

    # --------------------------------------------------------
    # 5. KONTROLA WYNIKOW
    # --------------------------------------------------------

    stats = connection.execute(
        text(f"""
            SELECT
                COUNT(*) AS total,

                MIN({COUNT_COLUMN}) AS min_classes,
                MAX({COUNT_COLUMN}) AS max_classes,

                MIN({RESULT_COLUMN}) AS min_iop,
                MAX({RESULT_COLUMN}) AS max_iop,

                COUNT(*) FILTER (
                    WHERE {COUNT_COLUMN} IS NULL
                       OR {COUNT_COLUMN} < 0
                       OR {COUNT_COLUMN} > 68
                       OR {RESULT_COLUMN} IS NULL
                       OR {RESULT_COLUMN} < -1
                       OR {RESULT_COLUMN} > 1
                ) AS invalid

            FROM {grid}
        """)
    ).one()

    if stats.total != expected or stats.invalid != 0:
        raise RuntimeError(
            f"H3-{resolution}: nieprawidlowe wyniki"
        )

    print(
        f"\nOBLICZENIE IOP H3-{resolution} ZAKONCZONE"
    )

    print(
        f"Liczba heksagonow: {stats.total}"
    )

    print(
        f"Liczba klas: "
        f"{stats.min_classes} - {stats.max_classes}"
    )

    print(
        f"Zakres IOP: {stats.min_iop} do {stats.max_iop}"
    )

    print(
        f"Zaktualizowano: {grid}",
        flush=True,
    )


# ============================================================
# URUCHOMIENIE PROGRAMU
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Normalizacja i obliczanie wskaznika "
            "przejezdnosci dla H3-7, H3-8 i H3-9"
        )
    )

    parser.add_argument(
        "--resolutions",
        nargs="+",
        type=int,
        choices=tuple(RESOLUTIONS),
        default=list(RESOLUTIONS),
        help="Wybrane rozdzielczosci H3",
    )

    parser.add_argument(
        "--action",
        choices=("check", "normalize", "calculate"),
        default="check",
        help="Rodzaj operacji",
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Zezwala na zapis zmian w PostGIS",
    )

    args = parser.parse_args()

    if args.action != "check" and not args.execute:
        parser.error(
            "Operacje zapisu wymagaja --execute"
        )

    names = validate_weights()

    engine = create_database_engine()

    try:

        for resolution in sorted(set(args.resolutions)):

            if args.action == "check":

                with engine.connect() as connection:

                    check_resolution(
                        connection,
                        resolution,
                        names,
                        require_normalization=True,
                    )

            elif args.action == "normalize":

                with engine.begin() as connection:

                    normalize(
                        connection,
                        resolution,
                        names,
                    )

            elif args.action == "calculate":

                with engine.begin() as connection:

                    calculate_iop(
                        connection,
                        resolution,
                        names,
                    )

        print(
            "\nZAKONCZONO POMYSLNIE",
            flush=True,
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
