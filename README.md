# SSA Earnings Data — EPUF 2006 + Annual Statistical Supplement

## Data sources

This repository collects **two complementary SSA earnings data sources**, both ultimately
from the Master Earnings File but not interchangeable:

1. **EPUF 2006** — the 1% individual **microdata** (person and person-year records); detailed below.
2. **Annual Statistical Supplement (ASS)** — SSA's published **aggregate** tables (currently
   Table 4.B1, 2008 edition), used as an external benchmark when replicating Compson (2012).

| | EPUF 2006 | Annual Statistical Supplement |
|---|---|---|
| Grain | individual microdata (1% sample) | published annual aggregates |
| Sampling frame | 1% of all SSNs | CWHS frame |
| Earnings cap | capped at the taxable max **per person** | taxable capped **per job** (can exceed the max); also reports uncapped total |
| Adjustments | disclosure-protected: bottom/top-coded, random-rounded; ages ≤14/≥86 zeroed | OCACT adjustments for late/erroneous reporting |
| In this repo | `EPUF2006_*.csv` | `supplement_2008_table_4B1.csv` |

Because of the per-person vs per-job cap and the OCACT adjustments, EPUF aggregates *should*
fall **below** the Supplement's taxable-earnings totals — this is the expectation behind RS
Note 2012-01, and something we have **not yet tested** against our own EPUF extract.

The **2006 Earnings Public-Use File (EPUF)** is a public microdata file released by the
U.S. Social Security Administration (SSA). It is a **systematic 1% random sample of all
Social Security numbers (SSNs) issued before January 2007**, and it reports **annual
Social Security taxable earnings from 1951 to 2006** for the sampled individuals (plus a
1937–1950 aggregate).

**Where the earnings come from — the Master Earnings File (MEF).** The values are drawn
from the *summary segment* of SSA's MEF, the administrative system of record used to
determine benefit eligibility and compute benefit amounts. The MEF summary segment holds,
for each person-year, a running total of Social Security *covered* earnings (wages subject
to the payroll tax, plus taxable self-employment income).

**"Capped" earnings — the key measurement caveat.** The MEF itself records taxable
earnings that can exceed the annual taxable maximum when a person has multiple employers.
EPUF instead reports **capped** taxable earnings: each person-year is **top-coded at that
year's taxable maximum**. So EPUF measures covered earnings *up to the cap*, not total
labor income — the gap widens in years/for workers where earnings exceed the cap.

**Which records are in the sample.** The sample is defined on SSNs, not on a work-history
frame. From an underlying 1% draw, SSA removed some individuals during data cleaning (e.g.,
overlap with the New Beneficiary Data System) and, for disclosure protection, **zeroed out
earnings at ages ≤ 14 or ≥ 86**. All monetary values are additionally **bottom-coded and
random-rounded** (rounding base grows with the amount), so individual dollar figures are
approximate by design.

**Relation to the CWHS.** EPUF is *not* the Continuous Work History Sample (CWHS). The CWHS
is a **separate sampling frame** that SSA's Office of Research, Evaluation, and Statistics
uses to produce the published aggregates in the *Annual Statistical Supplement*. Because
EPUF (a 1%-of-SSNs draw from the MEF) and the CWHS are distinct frames — and because the
Supplement uses uncapped taxable earnings and applies Office of the Chief Actuary
adjustments for delinquent/fraudulent/late reporting that EPUF does **not** — estimates
from the two sources differ, though the differences are modest once the capping and
adjustments are accounted for.

**Further documentation**
- Compson, Michael (2012). *Comparing Earnings Estimates from the 2006 Earnings Public-Use
  File and the Annual Statistical Supplement.* SSA Research and Statistics Note No. 2012-01.
  <https://www.ssa.gov/policy/docs/rsnotes/rsn2012-01.html>
- Compson, Michael (2011). *The 2006 Earnings Public-Use Micro Data File: An Introduction.*
  Social Security Bulletin 71(4).
- `raw_data/epuf_dictionary.pdf` — field-level data dictionary shipped with the file.
- `raw_data/READ ME FIRST.doc` — SSA's original release notes.

### Annual Statistical Supplement — Table 4.B1 (2008 edition)

*"Number of workers with taxable earnings, amount of earnings, and Social Security numbers
issued, selected years 1937–2007."* Saved page: `raw_data/supplement_2008_table_4B1.source.html`
(from `.../supplement/2008/4b.html`; SSA's edge blocks non-browser fetches, so it was captured
from the browser). `code/data_import/extract_table_4B1.py` parses it to
`output/data_import/supplement_2008_table_4B1.csv` **and** loads it as table `supplement_4b1`
into the shared `processed_data/ssa.duckdb` (see [Database structure](#database-structure)).

Used to replicate Compson (2012), whose Table 1 compares the EPUF 1% sample against the
taxable-earnings series here. Columns that map to that comparison: **`reported_taxable_musd`**
(per-job-capped taxable — the headline series), **`workers_total_thousands`** (worker count),
and **`total_covered_earnings_musd`** (fully uncapped total — the other end of the capping wedge).

| Column | Meaning |
|---|---|
| `year` | Earnings year (selected years 1937–2007) |
| `prelim_flag` | SSA preliminary-data flag e/f/g (blank = final) |
| `workers_total_thousands` | Workers with taxable earnings (thousands); 1937–50 wage & salary only, 1951+ incl. self-employment |
| `workers_with_max_thousands` | Workers with earnings at the taxable maximum (thousands) |
| `new_entrants_thousands` | Workers with first taxable earnings under the program that year (thousands) |
| `total_covered_earnings_musd` | Total wages incl. estimated amounts above the taxable limit ($M); **uncapped** |
| `reported_taxable_musd` | Reported taxable earnings ($M); **per-job capped** |
| `reported_taxable_pct` | Reported taxable as % of total covered earnings |
| `avg_total_earnings_usd` | Average total earnings per worker ($) |
| `avg_reported_taxable_usd` | Average reported taxable earnings per worker ($) |
| `ssn_issued_thousands` | Social Security numbers issued (thousands; excludes railroad numbers) |

Empty `workers_with_max`/`new_entrants` for 2007 = "not available" (`--` in source).
Preliminary footnotes: **e** preliminary; **f** taxable = preliminary SSA, employment =
preliminary BLS; **g** preliminary BLS/BEA. SSA source line: *Master Earnings File, 1 percent
sample; BEA; BLS.*

Related Supplement tables for the note's other comparisons (not yet collected): **4.B4**
(% below max by sex), **4.B6** (median earnings by sex and age), **4.B3** (median by type and sex).

## Repository layout

```
epuf_2006/
├── README.md                     # this file
├── raw_data/                     # source data, as distributed (large; do not edit)
│   ├── EPUF2006_DEMOGRAPHIC.csv               #  151 MB — EPUF, one row per person
│   ├── EPUF2006_ANNUAL.csv                    # 1.75 GB — EPUF, one row per person-year
│   ├── epuf_dictionary.pdf                    # EPUF field dictionary
│   ├── READ ME FIRST.doc                      # EPUF release notes
│   └── supplement_2008_table_4B1.source.html  # ASS Table 4.B1, saved source page
├── code/
│   ├── data_import/
│   │   ├── build_epuf_duckdb.sql          # load EPUF CSVs → ssa.duckdb (demographic, annual)
│   │   └── extract_table_4B1.py           # parse saved 4.B1 HTML → CSV + ssa.duckdb (supplement_4b1)
│   ├── ssa_replication/
│   │   ├── example_panel_to_age60.sql     # sample analysis query (see below)
│   │   ├── replicate_note_table2.sql      # replicate Table 2 of RS Note 2012-01
│   │   └── plot_chart4_replication.py     # replicate Chart 4 → output/ssa_replication/chart4_replication.pdf
│   └── cross_sections/
│       ├── fit_dpln_male_1990.py          # double Pareto-lognormal fit, 1990 men
│       ├── fit_lognorm_mix_women_1990.py  # two-component lognormal-mixture fit, 1990 women
│       └── plot_women_mixture_1990.py     # histogram + fitted density → output/cross_sections/
├── processed_data/
│   └── ssa.duckdb                     # shared DB: demographic + annual + supplement_4b1 (~1.6 GB)
└── output/                            # generated artifacts (regenerable; not version-controlled)
    ├── data_import/
    │   └── supplement_2008_table_4B1.csv  # ASS Table 4.B1, extracted (1937–2007)
    ├── ssa_replication/
    │   └── chart4_replication.pdf
    └── cross_sections/
        └── women_mixture_1990.{pdf,png}
```

`raw_data/` and `processed_data/` are large and are not version-controlled; regenerate the
database from the raw CSVs with the build script.

## Database structure

All SSA data live in one shared [DuckDB](https://duckdb.org) database,
`processed_data/ssa.duckdb`, with three tables:

| Table | Source | Grain | Rows |
|---|---|---|---|
| `demographic` | EPUF demographic sub-file | one row per person | 4,384,254 |
| `annual` | EPUF annual sub-file | one row per person-year | 60,326,474 |
| `supplement_4b1` | ASS Table 4.B1 (2008) | one row per year (1937–2007) | 61 |

Build it from the project root (`epuf_2006/`) in two steps — the EPUF tables via SQL,
then the Supplement table via the Python extractor (which also writes the CSV):

```bash
duckdb processed_data/ssa.duckdb < code/data_import/build_epuf_duckdb.sql   # ~7 s → demographic, annual
python code/data_import/extract_table_4B1.py                                # → supplement_4b1
```

Both steps use `CREATE OR REPLACE`, so they are idempotent and order-independent.
The `demographic`/`annual` schemas are detailed below; `supplement_4b1` mirrors the
CSV columns documented under
[Annual Statistical Supplement — Table 4.B1](#annual-statistical-supplement--table-4b1-2008-edition).

### Table `demographic` — one row per person (4,384,254 rows)

Every sampled individual appears exactly once; `id` is unique.

| Column          | Type     | Range / codes   | Meaning |
|-----------------|----------|-----------------|---------|
| `id`            | INTEGER  | 1 – 4,384,254   | Random person identifier (join key, unique) |
| `yob`           | SMALLINT | 1870 – 2006     | Year of birth |
| `sex`           | TINYINT  | 1, 2, **NULL**  | 1 = Male, 2 = Female. **The raw code 3 ("unspecified", 3,054 people) is stored as `NULL`.** |
| `agg_earn_3750` | INTEGER  | 0 – 41,500      | Aggregate taxable earnings 1937–1950 (raw `TOT_COV_EARN3750` / dict. `AE3750`); top-coded at 41,500; ~80% are 0 |
| `qc_3750`       | SMALLINT | 0 – 56          | Credits (quarters of coverage) earned 1937–1950 (raw `QC3750` / dict. `TC3750`) |
| `qc_5152`       | SMALLINT | 0 – 8           | Credits earned 1951–1952 (raw `QC5152` / dict. `TC5152`); provided here because annual 1951–52 credits are unavailable |

### Table `annual` — one row per person-year (60,326,474 rows)

Long/tidy: only the 3.13M people with ≥1 positive-earning year appear, and only their
**positive-earning years**. **An absent `(id, year)` means zero covered earnings that
year** — this is a sparse panel, not a balanced one.

| Column     | Type     | Range / codes | Meaning |
|------------|----------|---------------|---------|
| `id`       | INTEGER  | → demographic | Person identifier (join key; repeats across years) |
| `year`     | SMALLINT | 1951 – 2006   | Earnings year (raw `YEAR_EARN`) |
| `earnings` | INTEGER  | ~45 – 94,200  | **Capped** SS taxable earnings; top-coded at the year's taxable maximum, bottom-coded, random-rounded |
| `qtrs`     | TINYINT  | 0 – 4, **NULL** | Quarters of coverage (SS credits) earned that year. **The raw missing code `.` (all 1951–52 rows) is stored as `NULL`.** |

Column-name changes from the raw CSVs are applied in the build script; both the raw header
name and the dictionary label are noted above because the CSV header and the
`epuf_dictionary.pdf` labels differ.

## Example query — earnings panel of fully-observed histories to age 60

`code/ssa_replication/example_panel_to_age60.sql` returns a **balanced, zero-filled long panel** of annual
earnings for every person whose **entire earnings history through age 60 is observed**
within the 1951–2006 window (i.e., uncensored at both ends).

Assuming careers start at **age 25** (the earnings-dynamics convention used in this
project), a history is fully observed when the whole age span 25–60 lies inside 1951–2006:

- reaches age 60 by 2006 → `yob + 60 <= 2006` (born ≤ 1946), and
- career start is observed → `yob + 25 >= 1951` (born ≥ 1926).

So the eligible cohorts are **birth years 1926–1946**: 644,793 people × 36 ages =
**23,212,548 person-year rows**. Missing years are filled with `earnings = 0` (a true zero,
since the full history is observed).

```sql
WITH cohort AS (                       -- uncensored history through age 60
    SELECT d.id, d.yob, d.sex
    FROM demographic d
    WHERE d.yob + 60 <= 2006           -- age 60 observed   (yob <= 1946)
      AND d.yob + 25 >= 1951           -- career start obs. (yob >= 1926)
),
ages AS (SELECT age FROM generate_series(25, 60) AS g(age))
SELECT
    cohort.id, cohort.sex, cohort.yob,
    ages.age,
    cohort.yob + ages.age    AS year,
    COALESCE(a.earnings, 0)  AS earnings,   -- 0 = no covered earnings that year
    a.qtrs
FROM cohort
CROSS JOIN ages
LEFT JOIN annual a
       ON a.id = cohort.id
      AND a.year = cohort.yob + ages.age
ORDER BY cohort.id, ages.age;
```

Run it with:

```bash
duckdb processed_data/ssa.duckdb ".read code/ssa_replication/example_panel_to_age60.sql"
```

Lowering the assumed start age tightens the window (it requires observing more early years,
so the lower birth-year bound rises and fewer cohorts qualify).

## Analysis caveats

- **Top-coding.** `earnings` is capped at the annual taxable maximum, so it understates true
  earnings — severely in early years (the cap binds near the ~56th percentile in 1965), much
  less after ~1980. Restrict to `year >= 1980` for top-of-distribution work.
- **Random rounding / bottom-coding.** Values are rounded to bases of $25/$100/$1,000
  (rising with earnings); values under $100 are replaced by the sub-$100 mean. Individual
  amounts are approximate.
- **Sparse panel.** Absence of a person-year = zero covered earnings, not missing data.
  Disclosure rules also zero out ages ≤ 14 and ≥ 86.
- **`qtrs` is not "time worked".** It is an earnings-threshold credit count (max 4); since
  1978 it is a coarse function of annual earnings, not calendar quarters employed, and it
  saturates at 4 for most full-year workers.
