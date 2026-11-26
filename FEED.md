# macro-hub feed

Everything the dashboard shows is also published as plain files for bots.
Base address: `https://lde1988.github.io/macro-hub/feed/`

| File | What it is |
|---|---|
| `latest.json` | The current picture: reading, regime, trend exit, every dial |
| `history/<SERIES_ID>.csv` | Full history of one data series, including revisions |
| `series.json` | The series registry: id, source, units, frequency, meaning |
| `verdicts.csv` | The verdict log: every change of reading, regime or trend exit, plus one row a day |
| `dial_changes.csv` | Every dial colour change |

Public market data only. Framework reading, not financial advice.

## Stability promise

`latest.json` has a `version`, currently **1.0**.

- Within version 1.x, fields are only **added**. Nothing is renamed, removed or given a new meaning.
- A breaking change raises the first number (2.0) and is announced in this file.
- A bot should check that `version` starts with `1.` and ignore fields it does not know.

## latest.json

| Field | Type | Meaning |
|---|---|---|
| `version` | text | Feed layout version |
| `generated_at` | text | When this run finished, UTC, `YYYY-MM-DDTHH:MM:SSZ` |
| `generated_at_hkt` | text | The same in Hong Kong time, for people |
| `disclaimer`, `exit_note` | text | Shown under the reading |
| `reading` | object | The Bitcoin buy / hold reading (below) |
| `altcoins` | object | `label`, `headline`, `why`. Stricter rule than Bitcoin's |
| `trend_exit` | object | Separate weekly-close filter (below) |
| `regime` | object | Context only (below) |
| `turn` | object | `confirmed` (true/false), `dollar_reversal`, `families` {rates, fed_treasury, crypto_liquidity}, `fresh_signals` (list) |
| `bitcoin` | object | `price`, `realised_price`, `ratio_to_realised`, `value_zone` (fixed level), `dynamic_value_zone`, `lth_cost`, `sth_cost` |
| `sections` | list | One entry per family: `id`, `name`, `kind` (valuation / stress / turn), `colour`, `word`, `sentence`, `dials` (ids) |
| `dials` | list | Every dial (below) |
| `sources` | object | Per source: `credit`, `last_ok` (UTC), `fails_in_a_row`, `check_only`, `problem` |
| `valuations` | list | Coin log-regression channels, one per coin (below). Context only: never part of the reading |
| `plain` | object | The plain-English wording shown on the dashboard (headline, backdrop, trend, tally, group sentences). For people; bots should use the coded fields |
| `watching` | object | Weekly sweep panel; `enabled` is false until Phase 2 is switched on |
| `stale_minutes` | number | The dashboard marks itself late when older than this |

### reading

| Field | Meaning |
|---|---|
| `label` | `BUY`, `HOLD` or `FROTH WARNING` |
| `level` | For `BUY` only: `STAGED` or `CONFIRMED` |
| `headline` | The reading in words, for example "Hold: cheap, but the turn is not confirmed" |
| `reasons` | Up to four plain sentences |
| `change` | What would change the reading |
| `caution` | true when the weekly close is below the break line and price is not in the value zone |
| `record` | For `FROTH WARNING` only: its past record |
| `rule` | Which rule set produced it (`new`) |
| `since`, `days_in_force` | When this reading began |

The rules are fixed and written in `reports/03-dial-bands.md` and `hub/signals/engine.py`. There is no machine learning and there are no hidden weights.

### trend_exit

`state` is `RISK-ON`, `RISK-OFF` or `NO DATA`. `RISK-OFF` follows a Bitcoin weekly close below `break_level`; `RISK-ON` returns on a weekly close above `reclaim_level`. Also `weekly_close`, `text`, `since`, `days_in_force`. It is its own line and does not enter the buy / hold reading.

### regime

`name` is one of `TURN`, `BREAK`, `STRESS BUILDING`, `FRAGILE`, `CALM`. `TURN` appears only when the turn is confirmed. `detail` explains why; `early_line` and `early_signals` list turn dials that are freshly green but not enough to confirm; `since`, `days_in_force`.

### each dial

| Field | Meaning |
|---|---|
| `id`, `title` | Stable id and display name |
| `group` | `A` is it cheap, `B` stress, `C` credit-event risk, `D` turn |
| `family` | Family id (`valuation`, `turn`, or one of the seven stress families) |
| `value` | The main number the needle shows (may be null) |
| `text` | The reading as displayed |
| `colour` | `green` supports buying, `amber` neutral, `red` argues against, or null (no data yet) |
| `word` | `Supports`, `Neutral`, `Against` or `No data` |
| `since` | When the dial took its current colour |
| `data_date`, `data_age_days` | Date of the newest data used, and its age |
| `stale`, `stale_reason` | true when the source is failing or the data is older than allowed; the colour shown is then the last known one |
| `fresh_turn_signal` | Group D only: true while a green is within 13 weeks of switching on |
| `moves` | One sentence on what would move the dial |
| `gauge` | `min`, `max`, `bands` ([from, to, colour]) for drawing |
| `extra` | Dial-specific numbers; treat as informative and optional |

A colour changes only after two runs in a row beyond a band edge, so `colour` is deliberately a little slower than `value`.

## history/<SERIES_ID>.csv

Columns: `date, value, first_seen, backfill`.

- `date`: the day the value is for.
- `first_seen`: when the hub first saw this value (UTC).
- A revised figure appears as a **new row** with the same `date` and a later `first_seen`. Rows are never changed or deleted.
- `backfill` = 1 marks history loaded in one go before go-live. The hub did not see those values at the time.

### Seeing only what was known at a time T (for back-tests)

1. Keep rows where `backfill` = 0 and `first_seen` ≤ T.
2. For rows where `backfill` = 1, treat a value as known from `date` + `lag_days` (from `series.json`). This is an estimate: back-filled history is today's version of the past, not the first print.
3. For each `date`, take the row with the latest `first_seen` among those kept.

`hub/store.py` (`Store.series(id, asof=T, lag_days=...)`) does exactly this.

Daily series hold finished days only; today's still-moving value is in `latest.json`, not in history.

## verdicts.csv

Columns: `time_utc, why_logged, reading, level, headline, altcoins, trend_exit, regime, turn_confirmed, btc_price, price_to_realised, reasons, what_would_change_it`. `why_logged` is `first run`, `change` or `daily`. Appended forever.

## Reading the feed politely

The feed is rebuilt about every 15 minutes (GitHub's timer can run late). Fetch `latest.json` no more than once every few minutes and check `generated_at`: if it is more than an hour old, treat the readings as stale.

## valuations

One entry per coin, in the dashboard's order (BTC, ETH, SOL, SUI, LINK, NEAR, ZEC, HYPE, WAL, DEEP).
A straight line is fitted to the natural log of the daily close against calendar days, over the coin's whole
history (Coin Metrics community data, CC BY-NC 4.0: credit Coin Metrics if you republish it).

| Field | Meaning |
|---|---|
| `sym`, `name` | Coin |
| `status` | `ok`; `greyed` (under 3 years of history, or the line fits poorly: R² below 0.3); `too_little` (under 1 year: no reading); `none` (no data) |
| `z` | Standard deviations from the line: (log price − log fair value) ÷ SD of the residuals |
| `zone`, `colour` | One of eight zones: `-3 SD oversold`, `-2 SD oversold`, `-1 SD oversold`, `below fair value` (−1 to 0), `above fair value` (0 to +1), `+1 SD overbought`, `+2 SD overbought`, `+3 SD overbought`; oversold green, the two fair-value zones amber, overbought red |
| `price`, `price_is_live`, `last_close_date` | Price used (live Coinbase price when available) |
| `fair_value`, `growth_per_year` | The line's value today, and the growth it assumes (0.5 = +50% a year) |
| `bands` | Price at each band, keys `"-3"` … `"+3"` |
| `r2`, `years`, `months`, `history_from` | How well the line fits and how much history was used |
| `warnings` | Plain reasons a card is greyed |
| `stretch` | Recent trend: `status`, `z`, `zone`, `colour`, `ratio` (price ÷ 200-day average), `ma`, `typical_ratio`, `days` |
| `revenue` | Price against revenue (SUI, ETH, LINK, SOL, NEAR; HYPE and WAL once they have enough history; otherwise null): `status` (`ok`, `waiting` with `available_in` days, or `none`), `z`, `zone`, `colour`, `multiple` (fully diluted value ÷ last 365 days of DefiLlama fees), `typical_multiple`, `fdv`, `fees_365`, `unlock` (share of supply still to unlock), `approximate` (true where past supply is estimated: SOL, NEAR), `note` |

A constant-growth line drifts toward "oversold" as a coin's growth slows. Treat these as context.
