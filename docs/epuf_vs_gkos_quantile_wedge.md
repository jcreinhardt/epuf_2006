# Why EPUF earnings quantiles sit below the GKOS cohort × age files

*2026-09-05. Measurement: `code/cross_sections/plots/plot_guv_gap_signature.py` →
`output/cross_sections/plots/guv_gap_signature.pdf`, `output/cross_sections/guv_gap_cells.csv`.*

**Answer.** The gap is a sample-composition and earnings-concept wedge, not a mistake in the
screen, the deflator, or sampling. It cannot be removed on the EPUF side.

## What was checked

| Candidate | Verdict | Evidence |
|---|---|---|
| Sample screen | Identical | Both sides keep nominal earnings ≥ 0.5 × 520 h × GKSW's own minimum-wage matrix (the same-year deflator cancels). Now one definition, `guv_targets.sel0_threshold`, asserted by `check_guv_conventions()`. DuckDB `quantile_disc` reproduces Stata's `r[ceil(q·N)]` exactly. |
| Deflator | Identical | GKSW's own PCE matrix (BEA 2009 = 100 vintage; their `base_price = 67` picks the 2013 entry, 107.572). A price-index error is one scalar per year; the observed gap varies by quantile and age within a year, so no deflator can produce it. |
| Sampling error | Irrelevant | Both are 1% samples of SSNs; a cell quantile with 4–17k observations has < 1% sampling error. The gap is 5–30%. |
| Sample selection / earnings concept | **The cause** | See below. |

## The signature of the gap (1957–2006, log(EPUF/GKSW), same screen and deflator)

- **Bottom-heavy.** Men: p10 −0.15 to −0.19, p25 −0.10, p50 −0.06, p75 −0.04. Women: p10 −0.05, p50 and p75 ≈ 0 to +0.02.
- **Age-increasing.** Men's p10 gap is ≈ 0 at ages 25–30 and −0.25 to −0.30 at 50–55.
- **Not trending with the price indices** (men's p75 gap flat at −0.04 from 1973 to 2006).

That is extra low earners in EPUF, concentrated among older men. EPUF `earnings` is all
covered earnings including taxable self-employment; GKSW's files are Kopczuk–Saez–Song's
"commerce and industry" W-2 wages: no self-employment, no agriculture, private households,
hospitals, education, social services, religious organisations or public administration
(≈ 70% of private employment kept). Supplement Table 4.B2: the self-employed are 7–11% of
covered workers with mean taxable earnings 45–80% of the wage mean, share rising with age.
EPUF has no industry or self-employment flag, so this selection cannot be reproduced.

## Two breaks in the GKSW files confirm the direction (EPUF flat at both)

- **2005.** The paper uses the KSS sample for 1957–2004 and extends 2004–2013 "using the
  underlying data from the MEF". GKSW's p10 falls in one year by 12% (men) and 19% (women),
  at every age, and stays there; the package's own `YEARX_PARTIALLC` file shows the same
  drop (and men's p90 rising 8%). EPUF's p10 then sits *above* GKSW's (+0.03 men, +0.18
  women). Whether the extension keeps the sector restriction is not documented; the break
  is the evidence.
- **1978.** Quarterly reports → W-2 Box 1: GKSW's p10 rises 10% against EPUF's 5%.

Anything fitted to the GKSW targets across 2004/2005 (e.g. the `mle-gmm` mode's 2005–13
cells) inherits a stitched sample.

## Sources

- Compson (2011), *SSB* 71(4): "EPUF data reflect capped Social Security taxable
  earnings … (including any taxable self-employment income) up to the taxable maximum";
  "The file excludes data for workers whose only earnings are from noncovered employment."
- Olsen & Hudson (2009), *SSB* 69(3): the Summary Segment (EPUF's source) "contains annual
  OASDI-taxable wages and tips and self-employment earnings"; the Detail Segment holds
  W-2-level data since 1978, and Box 1 "includes wages above the OASDI taxable maximum,
  noncovered wages, and deferred-compensation distributions."
- Guvenen, Kaplan, Song & Weidner (2022), Section I.A and fn. 10–11: W-2 Box 1 from 1978,
  self-employment excluded, KSS sample 1957–2004 extended from the MEF for 2004–2013.
- Kopczuk, Saez & Song (2010), Section II.B: the commerce-and-industry SIC definition;
  W-2 "full compensation" from 1978.
