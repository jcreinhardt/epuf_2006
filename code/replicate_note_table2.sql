-- Replicate Table 2 of Compson (2012), RS Note 2012-01:
-- Supplement taxable earnings vs EPUF weighted (×100) capped taxable earnings, 1951–2006.
--   duckdb processed_data/ssa.duckdb < code/replicate_note_table2.sql
SELECT
    s.year,
    s.reported_taxable_musd                                                  AS supp_taxable_musd,
    round(SUM(a.earnings) * 100 / 1e6)                                       AS epuf_capped_taxable_musd,
    round(SUM(a.earnings) * 100 / 1e6 / s.reported_taxable_musd * 100, 2)    AS epuf_pct_of_supp
FROM annual a
JOIN supplement_4b1 s USING (year)
WHERE s.year BETWEEN 1951 AND 2006
GROUP BY s.year, s.reported_taxable_musd
ORDER BY s.year;
