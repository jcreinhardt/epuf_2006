#!/usr/bin/env python3
"""Extract SSA Annual Statistical Supplement Table 4.B1 (2008 edition) to CSV.

Source doc: raw_data/supplement_2008_table_4B1.source.html — the served HTML of
https://www.ssa.gov/policy/docs/statcomps/supplement/2008/4b.html (saved from the
browser because SSA's Akamai edge blocks non-browser fetches).

The page has 14 tables; we pick the one whose <caption> names Table 4.B1, then
read its data rows. Each data row starts with a 4-digit year, optionally carrying
an SSA preliminary-data footnote letter (e/f/g) that we split into its own column.
Thousands separators are stripped and "--" (not available) becomes empty.

The rows are written to CSV and loaded as a table into the shared SSA DuckDB
database (processed_data/ssa.duckdb) that also holds the EPUF `demographic` and
`annual` tables, so all SSA data live in one place. The load shells out to the
`duckdb` CLI (already this project's build tool) — no extra Python dependency.

Usage:
    python code/extract_table_4B1.py            # uses the default paths below
    python code/extract_table_4B1.py --html <in.html> --out <out.csv>
    python code/extract_table_4B1.py --no-duckdb   # write the CSV only
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup

CAPTION_MATCH = "Number of workers with taxable earnings"
PRELIM_FLAGS = {"e", "f", "g"}
NA_TOKENS = {"--", "–", "—", ""}

# Output columns, in order. The 9 value columns follow `year`/`prelim_flag` and
# map positionally onto the 9 data cells that follow the year cell in each row.
COLUMNS = [
    "year",
    "prelim_flag",
    "workers_total_thousands",        # Number: Total
    "workers_with_max_thousands",     # Number: With maximum earnings
    "new_entrants_thousands",         # Number: New entrants into covered employment
    "total_covered_earnings_musd",    # Earnings: Total in covered employment (UNCAPPED, $M)
    "reported_taxable_musd",          # Earnings: Reported taxable — Amount ($M)
    "reported_taxable_pct",           # Earnings: Reported taxable — Percentage of total
    "avg_total_earnings_usd",         # Average per worker: Total earnings ($)
    "avg_reported_taxable_usd",       # Average per worker: Reported taxable ($)
    "ssn_issued_thousands",           # Social Security numbers issued (thousands)
]
N_VALUE_CELLS = len(COLUMNS) - 2  # 9

DEFAULT_HTML = Path("raw_data/supplement_2008_table_4B1.source.html")
DEFAULT_OUT = Path("raw_data/supplement_2008_table_4B1.csv")
DEFAULT_DUCKDB = Path("processed_data/ssa.duckdb")  # shared DB (also holds EPUF tables)
DEFAULT_TABLE = "supplement_4b1"


def _clean(cell: str) -> str:
    """Normalize a data cell: drop NBSP/commas, map 'not available' to ''."""
    text = cell.replace("\xa0", " ").replace(",", "").strip()
    return "" if text in NA_TOKENS else text


def _split_year(cell: str) -> tuple[str, str] | None:
    """Return (year, prelim_flag) if the cell begins with a 4-digit year, else None."""
    text = cell.replace("\xa0", " ").strip()
    # No \b after the year: a footnote letter can render glued to it ("2004e"),
    # and there is no word boundary between a digit and a following letter.
    m = re.match(r"^(\d{4})(\D.*)?$", text)
    if not m:
        return None
    year = m.group(1)
    letters = [c.lower() for c in (m.group(2) or "") if c.isalpha()]
    flag = next((c for c in letters if c in PRELIM_FLAGS), "")
    return year, flag


def _find_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        caption = table.find("caption")
        text = caption.get_text() if caption else table.get_text()
        if CAPTION_MATCH in text:
            return table
    raise ValueError(f"No table found whose caption matches {CAPTION_MATCH!r}")


def extract_table_4B1(html_path: str | Path) -> list[dict[str, str]]:
    """Parse Table 4.B1 from the saved SSA HTML and return a list of row dicts.

    Each dict has exactly the keys in COLUMNS. Rows are yielded in document order
    (1937 → 2007). Raises ValueError if the table or no data rows are found.
    """
    soup = BeautifulSoup(Path(html_path).read_text(encoding="utf-8"), "lxml")
    table = _find_table(soup)

    rows: list[dict[str, str]] = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
        if not cells:
            continue
        parsed = _split_year(cells[0])
        if parsed is None:  # header / source / note rows
            continue
        year, flag = parsed

        values = [_clean(c) for c in cells[1:]]
        if len(values) < N_VALUE_CELLS:
            values += [""] * (N_VALUE_CELLS - len(values))
        elif len(values) > N_VALUE_CELLS:
            raise ValueError(f"Year {year}: expected {N_VALUE_CELLS} value cells, got {len(values)}")

        row = {"year": year, "prelim_flag": flag}
        row.update(dict(zip(COLUMNS[2:], values)))
        rows.append(row)

    if not rows:
        raise ValueError("Table found but no data rows parsed")
    return rows


def write_csv(rows: list[dict[str, str]], out_path: str | Path) -> None:
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_into_duckdb(csv_path: str | Path, db_path: str | Path, table: str) -> None:
    """(Re)create `table` in the shared DuckDB database from the extracted CSV.

    Uses the `duckdb` CLI so the script needs no Python duckdb package. The DB file
    is created if absent; CREATE OR REPLACE makes re-runs idempotent and leaves any
    other tables (EPUF `demographic`/`annual`) untouched.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    sql = (
        f"CREATE OR REPLACE TABLE {table} AS "
        f"SELECT * FROM read_csv('{csv_path}', header = true);"
    )
    subprocess.run(["duckdb", str(db_path), "-c", sql], check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract SSA Supplement Table 4.B1 to CSV + DuckDB.")
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML, help="input source HTML")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output CSV path")
    ap.add_argument("--duckdb", type=Path, default=DEFAULT_DUCKDB, help="shared DuckDB database")
    ap.add_argument("--table", default=DEFAULT_TABLE, help="table name to (re)create")
    ap.add_argument("--no-duckdb", action="store_true", help="write the CSV only; skip the DB load")
    args = ap.parse_args()

    rows = extract_table_4B1(args.html)
    write_csv(rows, args.out)
    print(f"Extracted {len(rows)} rows ({rows[0]['year']}–{rows[-1]['year']}) -> {args.out}")

    if not args.no_duckdb:
        load_into_duckdb(args.out, args.duckdb, args.table)
        print(f"Loaded table '{args.table}' -> {args.duckdb}")


if __name__ == "__main__":
    main()
