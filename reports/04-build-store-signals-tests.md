# Point 4: store, signals and tests

Date: 25 November 2026. Code is on the `claude/build` branch; nothing is scheduled yet and nothing is on `main`.

## What was built

| Part | Where | What it does |
|---|---|---|
| Series registry | `registry/series.yaml` | 67 series: id, source, units, frequency, usual publication lag, meaning. Adding a series is one entry |
| Source adapters | `hub/sources/` | 12 small files, one per data site. Only finished periods go into history; today's still-moving values are passed separately and never stored |
| History store | `hub/store.py` | One tidy table per series (`date, value, first_seen, backfill`), one file per year. Revisions are appended, never overwritten |
| Fetch step | `hub/fetch.py` | Asks each source that is due, records health, counts failures in a row |
| Config | `config/thresholds.yaml` | Every threshold, each with a comment (a test enforces this) |
| Dials | `hub/signals/dials.py` | 39 dials, each a pure function over the store. No network calls in `hub/signals/` |
| Engine | `hub/signals/engine.py` | No-flapping rule, families, turn confirmation, regime, and both buy rules (new and original) |
| Replay | `hub/replay.py` | Runs the dials day by day over the past, seeing only what was known each day |
| Workflows | `.github/workflows/` | `tests.yml` runs every test on every change; `backfill.yml` loads history |

Not built yet (later points): dashboard, feed, verdict log, ntfy pushes, the 15-minute schedule, Phase 2.

## Tests

**242 tests, all passing**, locally and on GitHub Actions (run 45584659828, commit 376c7d8). All use made-up data; none touches the network.

| File | Tests | Covers |
|---|---|---|
| `tests/test_store.py` | 8 | New values, revisions appended not overwritten, point-in-time views, publication lag on back-filled rows, once-a-day snapshots, one file per year |
| `tests/test_dials.py` | 149 | Every band edge of every dial, the 2% price buffer, the dollar's two-fixing 0.3 rule, weekly close on the Sunday candle, month-end only when the next month has data, missing data |
| `tests/test_engine.py` | 57 | Two-runs-in-a-row rule, families counted once, turn confirmation (bank reserves alone never confirm), regime order, SELL / BUY (CONFIRMED) / BUY (STAGED) / HOLD kinds, CAUTION, altcoin rule, the original buy rule, "newly red" window |
| `tests/test_sources.py` | 28 | Each adapter's parsing, failure counting, retry behaviour, FINRA manual fallback, **secrets scrubbed from errors, logs and saved state**, registry and config checks |

## History loaded

A back-fill ran on a GitHub runner and wrote the `data` branch: **62 of 67 series, about 174,500 rows, 8.8 MB**. Every source reported healthy.

The five missing series are Coinalyze's (three funding rates, two open-interest totals). They are held back until the one-off open-interest pull finishes, because both use the same 40-a-minute allowance. Until then the funding and altcoin open-interest dials read "no data".

## First full calculation on live data (25 Nov 2026, about 09:30 UTC)

- **Regime: BREAK** (Bitcoin weekly close $61,163, below $70,000).
- **Reading: Hold: fairly cheap, but the turn is not confirmed (CAUTION: weekly close below the break level).**
  - Price is 1.11x realised price, not yet in the value zone ($59,025 against a green edge of $57,430).
  - No turn signal is green.
  - Liquidity deteriorating: the margin-debt signal fired within 12 months; the dollar is above 102.5 and rising; three families red (rates and dollar, AI and private credit, crypto leverage).
- Original rule, for comparison: Hold: neither cheap nor frothy (CAUTION).

Red dials: weekly close, Bitcoin against the Nasdaq-100 (-9.6% against its 100-day average), CPI (+0.4% in October), dollar index (103.88), stablecoin supply (-5.9%), AI-debt canaries (-42 points against the S&P 500), dollar reversal, stablecoin turn, weekly reclaim.
Green dials: breakeven (2.11%), BBB spread (+21bp), both Fed stress indexes, KRE (-10.5%), discount window ($9.1bn), standing repo ($0).
Everything else amber. One near an edge: CCC minus BB is +293bp against a red edge of +300bp.

## Things found while building

1. **Turn signals behave as states, not events.** See `03-dial-bands.md`: the dollar reversal dial was green on 80% of days in the past two years and the stablecoin dial on 74%, so "turn confirmed" held on 82% of days and the TURN regime on 721 of 730. An open question is recorded there; nothing was changed without the owner's say.
2. **Three noisy turn signals were widened** as instructed (hikes priced out 20bp to 30bp; bank reserves $75bn to $150bn; buybacks 1.5x to 2.0x). The buyback change means the August 2026 step-up Coutts cites (1.6x) no longer fires.
3. **Dollar index accuracy is weaker over a long window:** within 0.3 of the published close on 76% of 2,491 days.
4. **Back-filled history has no true "first seen" time.** It is marked `backfill=1`, and for point-in-time questions counts as known from its date plus the series' usual publication lag. That is an estimate. From go-live onward every value carries its real first-seen time.
5. **Fixed dollar levels cannot be replayed over old cycles** ($58,600, $70,000 and $73,000 mean nothing in 2018). For point 6 the config has one replay-only switch that expresses the value zone as a multiple of realised price; how to treat the weekly-close levels will be set out in the point 6 report before any result is shown.

## Still open

- Coinalyze load and the 1.66x open-interest cross-check (waiting on the one-off pull).
- The owner's answer on "fresh" turn signals.
