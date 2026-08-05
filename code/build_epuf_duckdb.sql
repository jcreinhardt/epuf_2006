-- =============================================================================
-- build_epuf_duckdb.sql
-- Load the 2006 SSA Earnings Public-Use File (EPUF) into a DuckDB database.
--
-- Creates two linkable tables from the raw CSVs:
--   demographic  -- one row per sampled person   (4,384,254 rows)
--   annual       -- one row per person-year       (60,326,474 rows)
--
-- Run from the project root (epuf_2006/), which builds/refreshes the DB file:
--   duckdb processed_data/ssa.duckdb < code/build_epuf_duckdb.sql
--
-- Paths below are relative to that working directory.
-- Idempotent: CREATE OR REPLACE rebuilds the tables from scratch each run.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Demographic sub-file (person level). Join key: id (unique).
--   sex == 3 ("Unspecified gender code") -> NULL, per project convention.
-- Column renames from the raw CSV header (see epuf_dictionary.pdf):
--   TOT_COV_EARN3750 -> agg_earn_3750  (dictionary field AE3750)
--   QC3750           -> qc_3750        (dictionary field TC3750)
--   QC5152           -> qc_5152        (dictionary field TC5152)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE demographic AS
SELECT
    ID                                    AS id,             -- random person id (join key)
    CAST(YOB AS SMALLINT)                 AS yob,            -- year of birth, 1870-2006
    CASE WHEN SEX = 3 THEN NULL
         ELSE CAST(SEX AS TINYINT) END    AS sex,            -- 1=Male, 2=Female, 3->NULL
    CAST(TOT_COV_EARN3750 AS INTEGER)     AS agg_earn_3750,  -- aggregate taxable earnings 1937-50 (top-coded 41,500)
    CAST(QC3750 AS SMALLINT)              AS qc_3750,        -- credits/quarters of coverage 1937-50 (0-56)
    CAST(QC5152 AS SMALLINT)              AS qc_5152         -- credits 1951-52 (0-8)
FROM read_csv('raw_data/EPUF2006_DEMOGRAPHIC.csv',
              header = true,
              types  = {'ID': 'INTEGER', 'YOB': 'INTEGER', 'SEX': 'INTEGER',
                        'TOT_COV_EARN3750': 'INTEGER', 'QC3750': 'INTEGER',
                        'QC5152': 'INTEGER'});

-- id is unique; a unique index enforces that and speeds person-level lookups.
CREATE UNIQUE INDEX IF NOT EXISTS idx_demographic_id ON demographic (id);

-- -----------------------------------------------------------------------------
-- Annual earnings sub-file (person-year level). Long/tidy; only positive-earning
-- years appear, so an absent (id, year) means zero covered earnings that year.
--   ANNUAL_QTRS is read as text because 1951-52 rows carry the code '.'.
--   TRY_CAST turns '.' into NULL, leaving 0-4 elsewhere.
--   ANNUAL_EARNINGS is capped (top-coded) at the year's taxable maximum.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE annual AS
SELECT
    ID                                AS id,        -- person id (join key; repeats across years)
    CAST(YEAR_EARN AS SMALLINT)       AS year,      -- earnings year, 1951-2006
    CAST(ANNUAL_EARNINGS AS INTEGER)  AS earnings,  -- capped SS taxable earnings (~45 - 94,200)
    TRY_CAST(ANNUAL_QTRS AS TINYINT)  AS qtrs       -- quarters of coverage 0-4; NULL for 1951-52
FROM read_csv('raw_data/EPUF2006_ANNUAL.csv',
              header = true,
              types  = {'ID': 'INTEGER', 'YEAR_EARN': 'INTEGER',
                        'ANNUAL_EARNINGS': 'INTEGER', 'ANNUAL_QTRS': 'VARCHAR'});

-- (id, year) is unique; also the natural key for joining onto the demographic
-- table and slicing person-year panels.
CREATE UNIQUE INDEX IF NOT EXISTS idx_annual_id_year ON annual (id, year);

-- -----------------------------------------------------------------------------
-- Sanity report (printed when run through the CLI).
-- -----------------------------------------------------------------------------
SELECT 'demographic' AS tbl, COUNT(*) AS n_rows,
       COUNT(*) FILTER (WHERE sex IS NULL) AS sex_null
FROM demographic
UNION ALL
SELECT 'annual', COUNT(*),
       COUNT(*) FILTER (WHERE qtrs IS NULL)
FROM annual;
