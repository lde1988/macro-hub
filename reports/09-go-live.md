# Point 9: schedule, backstop, README; open-interest calibration

Date: 25 November 2026.

## Schedule

Switched on at 11:32 UTC (19:32 Hong Kong time) by publishing to `main`.

| Job | Timer | Purpose |
|---|---|---|
| Hub run | every 15 minutes, at :03, :18, :33, :48 | Fetch, dials, dashboard, feed, pushes |
| Open interest (daily) | 00:40 UTC | Altcoin and Bitcoin open interest from about 1,060 markets; about half an hour |
| Watchdog | 01:27, 07:27, 13:27, 19:27 UTC | Backstop (below) |
| Tests | on every change | 314 tests, all passing |

**First scheduled run:** see "First real run" at the end of this file.

## Keeping it alive, and the backstop

GitHub switches scheduled jobs off after 60 days without repository activity. Guards, in order:

1. **Every hub run and every open-interest run re-enables all three scheduled jobs.** Re-enabling resets GitHub's 60-day clock, and brings back any one job that was switched off.
2. **The hub saves data on most days**, which is itself repository activity.
3. **Watchdog** (the backstop the owner asked for): a separate job on its own timer. Four times a day it reads the published feed. If the feed is more than 90 minutes old it re-enables the hub, starts a run, and sends a priority-4 push saying what it found.
4. **"Running again" push:** when the hub runs after a silence of three hours or more, it says so and for how long.
5. **Run-failure pushes** (from point 8) and the **daily digest as heartbeat**.

**The limit of this, stated plainly:** if GitHub disables every scheduled job in the repository at once, the watchdog is disabled too, and nothing inside GitHub can restart it. The signs would be: no daily digest, and the dashboard's "updated" line amber. The manual steps are in the README under "If it stops on its own". A watcher outside GitHub would close this gap; it is offered to the owner as an option and is not built.

## README

`README.md` on `main`, in plain English: what runs when, the pushes, how to pause it, what to do if it stops, secrets, how to add a dial, how a bot should read the feed, where things are, maintenance, and what it cannot do.

## Altcoin open-interest calibration (owner's instruction)

The first table (1.91x at the 67th percentile) was wrong for three reasons, all now corrected:

1. It counted contracts on shares, indices, commodities and metals as altcoins. On 27 September these were 11% of the "altcoin" total.
2. It included 701 days on which Bitcoin open interest was zero or missing (before October 2022), which gave infinite ratios and wrecked the percentile.
3. The percentile therefore ran over a window that was mostly empty.

**Excluded as not crypto** (41 tickers): AAPL, AMD, ANT, AVGO, BZ, CL, CRCL, CRWV, DELL, DRAM, EWY, GOOGL, INTC, KORU, META, MRVL, MSFT, MSTR, MU, NBIS, NVDA, ORCL, QQQ, SAMSUNG, SKHY, SKHYNIX, SNDK, SNXX, SOXL, SOXS, SPCX, SPY, TQQQ, TSLA, UNITREE, XAG, XAU; tokenised gold PAXG, XAUT; stablecoins USDC, USDT. Two whole venues (tradeXYZ, Polymarket) were already left out. A few small tickers I could not identify (for example BTW, LAB, H, BILL) were left in as crypto; together they are well under 1% of the total.

**About "from 1 January 2022":** Coinalyze's history for every major exchange starts on 13–16 October 2022. There is no data for January to October 2022, so "since Jan 2022" and "since Oct 2022" are the same window here. Both columns are shown; they are identical for that reason.

### Table: 27 September 2026 (Coutts: 1.66x, 98th percentile "since 2022")

1,505 days kept (13 Oct 2022 to 25 Nov 2026), all exchanges, days without Bitcoin open interest dropped.

| Definition of "altcoins" | Ratio 27 Sep | Percentile since Jan 2022 | Percentile since Oct 2022 | Latest day | Its percentile |
|---|---|---|---|---|---|
| All contracts, including shares and metals (first run, days fixed) | 1.91x | 100 | 100 | 1.52x | 84 |
| **Crypto only, with ETH** (all crypto contracts) | **1.70x** | **98** | **98** | 1.24x | 44 |
| Crypto only, with ETH (the 400 largest coins only) | 1.64x | 98 | 98 | 1.17x | 33 |
| Crypto only, without ETH | 1.02x | 98 | 98 | 0.69x | 55 |
| Crypto only, without ETH and SOL | 0.88x | 98 | 98 | 0.60x | 50 |
| ETH alone | 0.68x | 91 | 91 | 0.55x | 46 |
| Ten largest crypto altcoins, with ETH | 1.20x | 98 | 99 | 0.88x | 66 |

**Closest to Coutts: crypto only, with ETH.** It gives 1.64x to 1.70x at the 98th percentile on 27 September, against his 1.66x at the 98th. On 28 September it reads exactly 1.66x. Without ETH the percentile also matches (98th) but the level does not (1.02x), so his figure includes ETH.

### What is live: the check on the loaded series

The live dial uses "crypto only, with ETH", restricted to the markets holding 97% of crypto altcoin open interest (1,043 altcoin markets and all 18 Bitcoin markets), because all 5,500 cannot be read daily at Coinalyze's limit of 40 a minute. Its history was loaded on exactly that list (1,501 days, 16 Oct 2022 to 24 Nov 2026, no day without Bitcoin open interest).

| Date | Loaded series | Percentile to that date | Coutts |
|---|---|---|---|
| 26 Sep 2026 | 1.62x | 99 | |
| **27 Sep 2026** | **1.65x** | **99** | **1.66x, 98th** |
| 28 Sep 2026 | 1.61x | 98 | |
| 24 Nov 2026 (latest) | 1.20x | 51 | |

**Result: matched.** 1.65x against his 1.66x; 99th percentile against his 98th. By the owner's test ("near 1.66x and the 98th percentile") the proxy label comes off, and the dial takes part in the froth warning and the altcoin buy line again. The switch is one line in `config/thresholds.yaml` (`alt_oi.matched_to_coutts`, now `true`); setting it to `false` restores the proxy label and both exclusions.

Two honest caveats:

- **Older history is under-counted.** The market list is chosen by today's open interest, so coins that were large in 2022 and 2023 and have since faded are missing from those years. The loaded series peaks at 1.32x in late 2022, where the full count showed 2.26x. That makes recent readings rank slightly higher than they should (99th here against 98th on the full count).
- **The list ages.** New listings are not counted until it is rebuilt, and new share or commodity contracts must be added to the exclusion list (README, Maintenance).

## Queued work started

- **Plain-language redesign:** built on the `claude/redesign` branch, with screenshots sent to the owner. Not published; waiting for approval.
- **Coin valuations tab:** not started.
- **Point 10 (Phase 2 plumbing):** not started.
