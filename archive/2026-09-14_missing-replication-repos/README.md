# Archived: worktree `missing-replication-repos-37e75a`, 2026-09-14 to 09-16

Exploratory checks that were never committed, rescued when the worktree was removed
on 2026-10-07. Paths below `output/` mirror where each file was written.

**No script in the repo regenerates any of these.** They were produced by code that
was run inline and not saved. Treat them as a record of what was looked at, not as
reproducible artifacts. Nothing in `code/` reads them.

- `output/cross_sections/` — skewness of log earnings, 1951–2006; taxable share of
  total earnings, 1951–2006; cross-section shape for 1960 / 1990 / 2020.
- `output/dynamics/` — aggregate mean and cap-share check; EPUF-vs-model histograms
  for 1960 and 1994 (all ages, and ages 25–55); 1990 cross-section overlay and survival.

The worktree's one real commit (benefits award simulation re-run on the
SMOOTH_FRAC = 3e-4 surface, `4e2b01e`) was merged into main separately.
