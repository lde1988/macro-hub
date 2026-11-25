# macro-hub

A market data hub that runs entirely on GitHub: no server, nothing to install.

- **Dashboard:** https://lde1988.github.io/macro-hub/
- **Feed for bots:** https://lde1988.github.io/macro-hub/feed/latest.json (layout in [FEED.md](FEED.md))
- **Alerts:** pushes to a phone through ntfy.

It reads public market data only. It holds no holdings, account details or trading keys.
Everything it shows is a **framework reading, not financial advice**. It was built to spot buy
zones; its exit signals have a weak record (see the reports).

## What it does

About every 15 minutes it:

1. fetches public data (prices, on-chain figures, interest rates, credit spreads and so on);
2. adds anything new to its history, never overwriting a figure that was later revised;
3. works out 39 dials, each green (supports buying crypto), amber (neutral) or red (argues against);
4. applies fixed, written rules to give a Bitcoin reading (Buy, Hold or Froth warning), an
   altcoin line, a trend line and a backdrop;
5. publishes the dashboard and the feed;
6. sends a push only if something changed.

There is no machine learning and there are no hidden weights. The rules are in
`hub/signals/engine.py` and every threshold is in `config/thresholds.yaml`, each with a comment.

## What runs when

| What | When | Where to see it |
|---|---|---|
| **Hub run**: fetch, dials, dashboard, feed, pushes | Every 15 minutes (at :07, :22, :37, :52). GitHub's timer is "best effort" and is often 5 to 20 minutes late | Actions tab → Hub run |
| **Open interest (daily)**: altcoin and Bitcoin open interest from about 1,060 markets | Once a day at 00:40 UTC; takes about half an hour | Actions tab → Open interest (daily) |
| **Watchdog**: checks the dashboard is fresh and restarts the hub if not | Four times a day | Actions tab → Watchdog |
| **Tests** | On every change to the code | Actions tab → Tests |
| **Daily digest** push | First run after 08:00 Hong Kong time. It doubles as a heartbeat: no digest means something is wrong | Your phone |

Hong Kong time is UTC+8, so 00:40 UTC is 08:40 in Hong Kong.

## The pushes you can get

| Push | Priority |
|---|---|
| The Bitcoin reading changed (Buy / Hold) | 5 |
| A froth warning started or ended | 4 |
| The backdrop (regime) changed | 5 |
| The trend line turned down or up | 5 |
| A dial turned red | 4 |
| A dial turned amber from green | 3 |
| A dial improved | 2 |
| A source has failed four runs in a row, or a dial's data has gone stale | 3 |
| A run failed, the hub had gone quiet, or it is running again after a gap | 4 |
| Daily digest | 2 (silent) |

The first run after a reset records a silent baseline. A push that cannot be delivered is retried on the next run.

## How to pause it

1. Open the repository on GitHub and click the **Actions** tab.
2. In the left-hand list click **Hub run**.
3. Click the **"…"** button at the top right and choose **Disable workflow**.
4. Do the same for **Watchdog**, otherwise the watchdog will switch the hub back on within a few hours. That is its job.
5. Optionally do the same for **Open interest (daily)**.

To start again, repeat the steps and choose **Enable workflow**, then click **Run workflow** on Hub run.
After a pause the hub fills in the history it missed, and tells you it is running again.

## If it stops on its own

GitHub switches scheduled jobs off after 60 days with no activity in a repository. Three things guard against that:

- every run re-enables the three scheduled jobs, which resets GitHub's 60-day clock;
- the hub saves data most days, which counts as activity;
- the watchdog runs on its own timer and restarts the hub if the dashboard is more than 90 minutes old.

If GitHub ever disables *all* scheduled jobs at once, none of them can switch the others back on.
You would notice because the daily digest stops arriving and the dashboard's "updated" line turns amber. To switch it back on by hand:

1. Open **Actions**. If a yellow banner says workflows were disabled, click **Enable** on it.
2. Click **Hub run** in the left-hand list. If you see "This workflow was disabled", click **Enable workflow**.
3. Click **Run workflow** → **Run workflow** to start one now.
4. Do steps 2 and 3 for **Watchdog** and **Open interest (daily)**.
5. Within a few minutes you should get a push saying the hub is running again.

## Secrets

Secrets live only in GitHub (Settings → Secrets and variables → Actions). They are never written to the
repository, the logs, the feed or the data branch; tests check this.

| Secret | What it is | Where to get it |
|---|---|---|
| `FRED_API_KEY` | Free key for US economic data | fred.stlouisfed.org → My Account → API Keys |
| `COINALYZE_API_KEY` | Free key for funding rates and open interest | coinalyze.net/account/api-key |
| `NTFY_TOPIC` | The private topic name your phone subscribes to | You choose it in the ntfy app |
| `XAI_API_KEY` | Phase 2 only (weekly sweep). Not set: the sweep stays switched off | console.x.ai |

Anyone who knows the ntfy topic name can read the pushes, so treat it like a password.

## How to add a dial

1. **Add the data series** to `registry/series.yaml`: one entry with an id, the source, the code at
   that source, units, frequency and a plain sentence on what it means. If the source is already
   listed (FRED, Coinbase and so on) that is all the data work needed. A new source needs one small
   file in `hub/sources/` with a `fetch` function; copy `hub/sources/nasdaq.py` as a pattern.
2. **Add the thresholds** to `config/thresholds.yaml`, each with a comment.
3. **Add the dial** to `hub/signals/dials.py`: a function that reads the series and returns the
   number, its colour, the text and one sentence on what would move it. Copy a similar dial.
4. **Put it in a family** in `config/thresholds.yaml` (under `families`), so it is counted once with its group.
5. **Add tests** with made-up data in `tests/test_dials.py`: one for each band edge.
6. **Load its history**: Actions → Backfill → Run workflow, typing the source's name.

Tests run automatically on every change. A dial changes colour only after two runs in a row beyond a
band edge, and data older than its limit cannot change a colour (the dial greys out instead).

## How a bot should read the feed

Read [FEED.md](FEED.md) for the full layout. In short:

- Fetch `feed/latest.json` no more than once every few minutes.
- Check `version` starts with `1.`; ignore fields you do not know. Within version 1 fields are only added.
- Check `generated_at`: if it is more than an hour old, treat everything as stale.
- `reading.label` is `BUY`, `HOLD` or `FROTH WARNING`; `reading.level` is `STAGED` or `CONFIRMED` for a buy.
- `trend_exit.state` is `RISK-ON` or `RISK-OFF`. It is separate from the reading.
- Each dial has `colour`, `value`, `data_age_days` and `stale`. Do not act on a stale dial.
- For back-tests use `feed/history/<SERIES_ID>.csv`. Each row has `first_seen`, so a test can see only
  what was known at the time. Rows marked `backfill` were loaded in one go before go-live; FEED.md explains how to date them.

## Where things are

| Path | What |
|---|---|
| `registry/series.yaml` | Every data series |
| `registry/oi_universe.yaml` | The markets counted for open interest (written by a tool; see Maintenance) |
| `config/thresholds.yaml` | Every threshold, with comments |
| `hub/sources/` | One small adapter per data site |
| `hub/store.py` | The history store (append-only, with first-seen times) |
| `hub/signals/` | Dials and rules. Nothing here touches the network |
| `hub/outputs/` | Feed and dashboard |
| `hub/alerts.py`, `hub/notify.py` | What to push, and sending it |
| `hub/run.py` | One scheduled run, start to finish |
| `hub/replay.py`, `tools/replay_report.py` | Replaying the rules over history |
| `tests/` | Tests, all with made-up data |
| `manual/margin_debt.csv` | Hand-filled fallback if FINRA's file cannot be read |

Branches:

- `main`: the code that runs.
- `data`: history, dial state and logs, written by the runs. Committed only when something changed.
- `reports`: one plain-English report per stage of the build, including the history replays.

## Maintenance

- **Fixed price levels** ($58,600, $70,000, $73,000) are in `config/thresholds.yaml` under `levels`.
  The dashboard shows moving equivalents beside them so you can see when they drift apart.
- **Open-interest market list**: new coin listings are not counted until the list is rebuilt. A few
  times a year run Actions → Open interest backfill (a full census, about 2.5 hours), then
  `python tools/oi_universe.py <folder>` on its result. New share or commodity contracts must be added
  to the exclusion list in `tools/oi_universe.py`, or they would be counted as altcoins.
- **Margin debt**: if FINRA changes its spreadsheet, fill `manual/margin_debt.csv` by hand (one line a month).
- **Bitview** is at version 0.x: watch for changes to its series names.

## What it cannot do

- It does not use Coutts' own liquidity index (proprietary): the liquidity dial is a labelled proxy.
- The dollar index is computed from ECB reference rates, not the official ICE index, and is a daily fixing, not a live quote.
- The S&P 500 comes from FRED a day late; an unofficial same-day estimate is shown beside it.
- Credit spreads on FRED go back only three years, so they were missing from most of the history replay.
- The history replay covers five cycle lows and four highs. That is a sanity check, not proof.

## Room for later

Company financials from SEC EDGAR would be a new source file plus registry entries; equity data is
another entry for the existing `nasdaq` source; more bots only need the feed. None of these is built.
