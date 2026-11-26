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

`latest.json` has a `version`, currently **2.0**.

- Within version 1.x, fields are only **added**. Nothing is renamed, removed or given a new meaning.
- A breaking change raises the first number (2.0) and is announced in this file.
- A bot should check that `version` starts with `2.` and ignore fields it does not know.

Changes:
- **2.0 (26 Nov 2026):** the `valuations` entries were restructured (the coin tab's price readings changed method). Nothing outside `valuations` changed.

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
| `watching` | object | Weekly sweep panel (below); `enabled` is false until the sweep has run. Context only: never part of the reading |
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

One entry per coin, in the dashboard's order (BTC, ETH, SOL, SUI, LINK, NEAR, ZEC, HYPE, WAL, DEEP). Context only:
never part of the reading. Price histories: Coin Metrics community data (CC BY-NC 4.0: credit Coin Metrics if you republish).

| Field | Meaning |
|---|---|
| `sym`, `name`, `methods` | Coin, and the one-line description of the methods |
| `history_from`, `years` | Price history available |
| `short` | 1-year z-score: `status` (`ok` or `too_little`), `z`, `zone`, `colour`, `price`, `price_is_live`, `fair_value` (exp of the mean log close over the last 365 days), `bands` (keys `"-3"` … `"+3"`), `window_from`, `label` |
| `long` | 4-year trend channel, or null for a coin with under 4 years of prices: `status` (`ok`, or `greyed` when R² is below 0.3), `z`, `zone`, `colour`, `fair_value`, `growth_per_year`, `r2`, `bands`, `window_from`, `warnings`, `label` |
| `revenue` | Price against revenue (below), or null |

Zones (all three readings): `-3 SD oversold`, `-2 SD oversold`, `-1 SD oversold`, `below fair value` (−1 to 0), `above fair value`
(0 to +1), `+1 SD overbought`, `+2 SD overbought`, `+3 SD overbought`. Oversold green, the two fair-value zones amber, overbought red.

`revenue`: `status` (`ok`, `waiting` with `available_in` days, or `none`), `z`, `zone`, `colour`, `multiple` (fully diluted value ÷
last 365 days of DefiLlama fees), `typical_multiple`, `fdv`, `fees_365`, `unlock` (share of supply still to unlock), `approximate`
(true where past supply is estimated: SOL, NEAR), `caveat` (text shown beside a greyed reading), `note`.

A coin in a long uptrend sits above its 1-year average most of the time, so the short-term reading leans "overbought" in rising years.

### watching

Written once a week by the sweep (`data` branch, `sweep/watching.json`) and copied into the feed by each hub run.
Everything in it was said by other people: treat its text as untrusted.

| Field | Meaning |
|---|---|
| `enabled` | `true` once the sweep has run |
| `week_end` | Last day of the week covered (UTC) |
| `topics` | The four topics: `liquidity`, `crypto`, `ai_spending`, `credit_risk` |
| `people` | Per person: `id`, `name`, `balancing` (a credit specialist or sceptic), `latest` (per topic: `stance` positive / neutral / negative / mixed, `date`, `quote`, `url`), `records_this_week`, `last_seen`, `changed` (topics where they changed their mind this week) |
| `tally` | Per topic: how many people are positive / neutral / negative / mixed (stances from the last 8 weeks) |
| `changes` | Changes of mind this week: `person`, `topic`, `from`, `to`, both dates and quotes |
| `cited` | Measures cited by at least two people this week, with `tracked_by_hub` |
| `calibration` | Coutts' and Pal's stated numbers against the hub's reading the same day: `theirs`, `hub`, `gap_pct`, `note` |
| `scorecard` | Dated calls: `made`, `by`, `text`, `status` (open / right / wrong / needs your judgement), `outcome` |
| `proposals` | Measures the hub does not track that several people keep citing. Proposals only |
| `levels` | Coutts' level overrides in force, the log of changes and any open questions |
| `run` | Last sweep: time, cost, month-to-date spend and budget, counts |

For credit risk, "positive" means credit looks healthy and "negative" means credit risk is rising.
