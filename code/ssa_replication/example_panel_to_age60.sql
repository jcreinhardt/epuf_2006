-- =============================================================================
-- example_panel_to_age60.sql
-- Long earnings panel for every person whose ENTIRE earnings history through
-- age 60 is observed within the EPUF window (1951-2006), i.e. uncensored.
--
--   duckdb processed_data/ssa.duckdb < code/ssa_replication/example_panel_to_age60.sql
--   duckdb processed_data/ssa.duckdb ".read code/ssa_replication/example_panel_to_age60.sql"
--
-- "Full history until age 60 observed" means the whole age span
-- [START_AGE .. 60] falls inside 1951-2006, so neither the career start nor
-- age 60 is clipped by the sample window:
--   * reaches age 60 by 2006      ->  yob + 60        <= 2006   (yob <= 1946)
--   * career start within window  ->  yob + START_AGE >= 1951   (yob >= 1951 - START_AGE)
--
-- Careers are assumed to start at age 25 (the earnings-dynamics convention);
-- with START_AGE = 25 the eligible cohorts are yob 1926-1946 (644,793 people,
-- 36 ages each -> 23,212,548 rows). Lowering START_AGE requires observing more
-- early years and therefore SHRINKS the eligible set.
--
-- Because full history is observed, a year with no annual record is a true zero,
-- so the panel is balanced and zero-filled across ages 25-60.
--
-- NOTE: DuckDB's generate_series() needs literal bounds, so the age span 25/60
-- is written as literals in two places below -- keep them in sync.
-- =============================================================================

WITH cohort AS (                              -- people with uncensored history to age 60
    SELECT d.id, d.yob, d.sex
    FROM demographic d
    WHERE d.yob + 60 <= 2006                   -- age 60 observed   (yob <= 1946)
      AND d.yob + 25 >= 1951                   -- career start obs. (yob >= 1926)
),
ages AS (                                     -- ages 25..60 (must match the 25/60 above)
    SELECT age FROM generate_series(25, 60) AS g(age)
)
SELECT
    cohort.id,
    cohort.sex,
    cohort.yob,
    ages.age,
    cohort.yob + ages.age            AS year,
    COALESCE(a.earnings, 0)          AS earnings,   -- 0 = true zero (no covered earnings)
    a.qtrs
FROM cohort
CROSS JOIN ages
LEFT JOIN annual a
       ON a.id = cohort.id
      AND a.year = cohort.yob + ages.age
ORDER BY cohort.id, ages.age;
