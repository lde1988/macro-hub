# Point 19: Coin scanner built and tested (not published)

Date: 27 November 2026. Code on the `claude/scanner-plan` branch (commit c65ade7). **Not on `main`. No daily job runs.
Nothing on the live dashboard has changed.**

## Tests

**595, all passing**, 41 of them new for the scanner. All use made-up data. They cover:
- every trend test and band edge, the 5-close settling and Dual Bull;
- each quality part, including the relative revenue rank and "no data";
- the universe exclusions, including a quiet real coin that must not be taken for a pegged one;
- the price cleaning;
- the once-a-day alert, only while the regime is ON;
- the snapshot format and the regime read from the hub;
- the whole daily job with a fake internet: it writes only inside `scanner/`;
- the tab's escaping, filters and regime banner;
- the backtest's regime replay;
- a check that the reading and every dial are unchanged with scanner data present.

## The owner's change to D (revenue)

Revenue growth (last 90 days against the 90 before) now carries two marks:
- **the fixed mark** (±20%);
- **a rank against every scanned coin with revenue data**: top third good, bottom third bad.

Both are shown in each coin's detail, for example "+33% on the 90 before (fixed mark: good); rank 11 of 24 (neutral)". **The relative mark is the one that counts toward passing**, so in a bear market the best relative performers still stand out. In this trial the median was +23%, from 24 coins with enough revenue data.

## Trial on real data (free; run 45955012278, written to a side branch, the data branch untouched)

- **Universe:** 101 coins rated (100 plus your WAL and DEEP), and 56 left out, each with its reason.
- **Loading:** the first load made 188 CoinGecko calls, 102 Coin Metrics calls and 116 DefiLlama calls, and took about 45 minutes. Later days need only a few calls per coin.
- **Price history:** Coin Metrics was used where it matched CoinGecko within 3%, back to 2015 for older coins. CoinGecko's free year was used for the rest.
- **Regime:** OFF (the hub's weekly trend exit, RISK-OFF since 16 November). The regime line (short-term holder cost) is $72,141.
- **Own trend:** 78 Strong Bear, 8 Bear, 9 Neutral, 2 Bull, 1 Strong Bull.
- **Against Bitcoin:** 15 Strong Bull, 6 Bull, 26 Neutral, 38 Bear, 12 Strong Bear.
- **Dual Bull:** JST, PIEVERSE and NIGHT. No buy candidates, because the regime is OFF.
- **Quality:** 51 of 101 coins pass.

### Your 10 today

| Coin | Sector | Own trend | vs BTC | Quality |
|---|---|---|---|---|
| BTC | L1 | Strong Bear | – (Bitcoin itself) | pass (2 of 3 scored) |
| ETH | L1 | Strong Bear | Strong Bear | pass (3 of 3 scored) |
| SOL | L1 | Strong Bear | Bear | pass (3 of 3 scored) |
| HYPE | L1 | Strong Bear | Neutral | fail (3 of 3 scored) |
| ZEC | Privacy | Strong Bear | Bear | pass (2 of 3 scored) |
| LINK | Infrastructure | Strong Bear | Neutral | pass (3 of 3 scored) |
| NEAR | L1 | Strong Bear | Bear | pass (3 of 3 scored) |
| SUI | L1 | Strong Bear | Bear | fail (3 of 3 scored) |
| WAL | Infrastructure | Strong Bear | Bear | fail (1 of 3 scored) |
| DEEP | Infrastructure | Strong Bear | Bear | fail (3 of 3 scored) |
**Problems the trial found, all fixed:**
1. **Impossible price jumps in the free data:** Aptos ×1,045 on its listing day (Coin Metrics), and SUN ×112 at a redenomination. Any one-day move beyond 10× is now treated as a data error, and the history before it is dropped. This applies in the ratings and the backtest. A real ×3 day (DOGE, January 2021) is kept.
2. **Figure HELOC**, a $29 billion tokenized home-equity loan fund, slipped past CoinGecko's categories. It is now on the exclusion list.
3. **The "price hardly moves" cut-off was too high.** At 1% a day it would also have excluded real coins in quiet months: Bitcoin averaged under 1% a day in mid-2023. It is now 0.3%; pegged tokens move 0.01–0.1%. This was found by a test.
4. **Sectors were badly ordered:** LINK came out as DeFi, and NEAR and WAL as AI. The most specific categories now win:
   - LINK and WAL → Infrastructure;
   - NEAR and HYPE → L1;
   - ZEC → Privacy.
5. **On a phone, an opened coin's detail was cut off** at the right edge. It now stays on screen.
6. **The backtest included funds the scanner leaves out** (EUTBL, USYC). It now tests only the coins the scanner keeps.

The screenshots come from this trial's real ratings with fixes 2 and 4 applied. Fixes 1 and 3 do not change today's ratings: the bad jumps were in 2021 and 2022, outside the window the ratings use.

## Backtest, 1 January 2020 to 26 November 2026 (Coin Metrics and CoinGecko daily closes, cleaned)

**Read this first.** Several things make this backtest look better than real life would:
- **Survivorship bias.** It tests only today's coins: 96, of which 26 have prices from the start of 2020. Coins that died or dropped out (LUNA, FTT and many more) are missing.
- **No trading costs** are included.
- **The trend settings were chosen on this same history.**
- **Quality is not in it**, because supply history is free for one year only.

The regime is the hub's weekly trend exit, replayed with its moving stand-ins (as in report 06b). It was ON on 62% of days.

| Rule | Growth | Per year | Worst fall | Days invested |
|---|---|---|---|---|
| Dual Bull coins, equal weight, only while the regime is ON (cash otherwise) | 66.15x | +83% | −71% | 60% |
| the same, memecoins left out | 18.91x | +53% | −75% | 59% |
| the same, without its 5 biggest winners (DOGE, SHIB, FET, ADA, SOL) | 12.04x | +43% | −77% | 60% |
| Hold Bitcoin | 8.44x | +36% | −77% | 100% |
| Bitcoin only while the regime is ON | 7.37x | +34% | −50% | 62% |
| Dual Bull rule, from 2022 only | 1.92x | +14% | −58% | 55% |
| Hold Bitcoin, from 2022 only | 1.31x | +6% | −67% | 100% |

| Each new Dual Bull while the regime was ON | Signals | Beat Bitcoin | Median coin | Median Bitcoin |
|---|---|---|---|---|
| after 30 days | 565 | 41% | −5.4% | −1.7% |
| after 90 days | 508 | 35% | −11.7% | +1.7% |
| after 90 days, memecoins left out | 480 | 35% | −11.9% | +1.0% |

**What it says, plainly:**
- **Most signals lose against Bitcoin.** About two in three Dual Bull signals did worse than Bitcoin over the next 90 days.
- **The big total comes from a few huge winners.** DOGE and SHIB in 2021 account for most of the 66×. Without the five biggest winners it is 12× against Bitcoin's 8.4×. Without memecoins it is 19×.
- **This is classic trend-following**, and exactly the shape survivorship bias exaggerates. The coins that rose 100× are the ones still in today's top 100 to be tested.
- **From 2022 onwards the rule made 1.9× against Bitcoin's 1.3×**, with a smaller worst fall (−58% against −67%), and was in the market just over half the time. Treat this as a sanity check, not proof.
- **The honest test is the daily snapshots from now on.**

## The tab (screenshots in this folder)

- `19-scanner-phone-top.png`: the regime banner, "No buy candidates: Bitcoin regime OFF since 16 Nov". The relative-strength watchlist follows. It covers only 10 days so far, and says so ("still noisy").
- `19-scanner-phone-detail.png`: the table filtered to your coins, with SOL opened. It shows the three trend tests with their numbers, revenue with both marks and the rank, dilution, the share to holders, and "unlock schedules: no free data".
- `19-scanner-phone-swiped.png`: the same table swiped sideways, showing vs BTC, days since and quality. The coin column stays pinned.
- `19-scanner-desktop.png`: the desktop view.

**The table:**
- The columns you asked for: asset with sector, price, since signal, 7 days, own trend, vs BTC, days since, quality.
- Every column sorts.
- Filters: All, Dual Bull, the five states, and Yours ★.
- "Hide memecoins" and "Hide exchange tokens" switches, remembered on your phone.

**Further down the tab:**
- a "How the ratings work" fold-out;
- the 56 coins left out, each with its reason;
- the honesty note.

## Still to do on publishing (free; waiting for your go-ahead)

1. Merge to `main`. The tab then appears with the next hub run.
2. Run the scanner once by hand. It loads the price history into the data branch, in about 45 minutes.
3. Leave the daily job on its timer (00:50 UTC, 08:50 Hong Kong), with the hub's backstop from 02:30 UTC.
4. Pushes: at most one a day, only once the regime is ON. With the regime OFF today, none will come.
