# Coin valuations tab: sources and the ten readings (before building)

Date: 26 November 2026. Nothing is built yet; the owner asked to see this first.

## Method as computed

- Natural log of the daily close against calendar days, straight line by least squares, over each coin's full available history up to the latest finished day.
- Fair value = the line's value today. Reading = (log price − log fair value) ÷ standard deviation of the residuals (population form, as TradingView's `ta.stdev` uses).
- Zones: within ±1 SD is "fair value"; 1 to 2 SD is "−1 / +1 SD", 2 to 3 is "−2 / +2", beyond 3 is "−3 / +3". Oversold green, fair amber, overbought red.

## Settings, and which are guesses

| Setting | Used | Source |
|---|---|---|
| Log base | Natural log | Owner's instruction. The reading in SD is the same in any base |
| X axis | Calendar days | Owner's instruction ("against time"). Identical to bar index for coins that trade every day |
| Start date | First day of available history | Owner's instruction. **The TradingView script's default start date is unknown**: tradingview.com cannot be reached from the build workspace, and the search snippets say only that the user sets a start and end date |
| Bands | ±1, ±2, ±3 SD | Search snippets describing the script. **Not verified from its code** |
| SD form | Population (divide by n) | **Guess**, based on Pine's default. Sample form changes readings by under 0.1% |
| Refit | Daily, through the latest finished day | **Guess.** The fair value therefore moves a little each day |

## Sources

| Coin | Coin Metrics community (no key) | Coinbase |
|---|---|---|
| BTC | from Jul 2010 | from Jul 2015 |
| ETH | from Aug 2015 | from May 2016 |
| SOL | from Apr 2020 | from Jun 2021 |
| SUI | from Aug 2023 | from May 2023 |
| LINK | from Sep 2017 | from Jun 2019 |
| NEAR | from Oct 2020 | from Sep 2022 |
| ZEC | from Oct 2016 | from about Dec 2020 |
| HYPE | from Dec 2024 | from Feb 2026 |
| WAL | from May 2025 | from Feb 2026 |
| DEEP | from Nov 2024 | from Feb 2026 |

Both work from the build workspace; Coin Metrics already works from a GitHub runner (point 2), and Coinbase likewise.

- **Proposed:** Coin Metrics for history (longest for nine of ten; Coinbase alone would leave HYPE, WAL and DEEP under a year and therefore with no dial). Coinbase for today's live price and as a daily cross-check.
- **Cross-check:** over the last 60 days the two agree on each day's close within 0.10% (BTC) to 0.34% (WAL, DEEP) on average.
- **Licence:** Coin Metrics community data is, to my understanding, free for non-commercial use with credit (Creative Commons BY-NC). It will be credited in the footer. To be confirmed before go-live.

## The ten readings (close of 25 Nov 2026)

| Coin | History | Price | Fair value | Reading | Zone | R² | Line's growth a year | −2 SD | −1 SD | +1 SD | +2 SD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BTC | 16.4 years | $60,268 | $575,718 | −1.72 | −1 SD oversold | 0.86 | +101% | $41,610 | $154,776 | $2.14m | $7.97m |
| ETH | 11.3 years | $1,690 | $10,855 | −1.54 | −1 SD oversold | 0.69 | +75% | $972 | $3,248 | $36,277 | $121,239 |
| SOL | 6.6 years | $70.35 | $278 | −1.24 | −1 SD oversold | 0.47 | +73% | $30.34 | $91.89 | $843 | $2,552 |
| SUI | 3.3 years | $0.665 | $1.58 | −1.30 | −1 SD oversold | **0.01** | +8% | $0.415 | $0.810 | $3.09 | $6.03 |
| LINK | 9.2 years | $9.03 | $33.98 | −1.33 | −1 SD oversold | 0.52 | +48% | $4.67 | $12.59 | $91.68 | $247 |
| NEAR | 6.1 years | $3.02 | $2.31 | +0.40 | fair value | **0.06** | −9% | $0.59 | $1.17 | $4.56 | $9.02 |
| ZEC | 10.1 years | $764 | $84.30 | **+2.23** | +2 SD overbought | **0.00** | −1% | $11.73 | $31.44 | $226 | $606 |
| HYPE | 1.9 years: short history | $61.36 | $75.08 | −0.68 | fair value (greyed) | 0.63 | +99% | $41.36 | $55.73 | $101 | $136 |
| WAL | 1.5 years: short history | $0.0213 | $0.0174 | +0.79 | fair value (greyed) | 0.94 | **−90%** | $0.0105 | $0.0135 | $0.0225 | $0.0290 |
| DEEP | 2.0 years: short history | $0.0119 | $0.0139 | −0.35 | fair value (greyed) | 0.74 | **−73%** | $0.0055 | $0.0088 | $0.0222 | $0.0353 |

## Bitcoin against Raoul Pal's figure

Secondary reports (no primary post found) quote Pal at about 1.5 SD below fair value in late June 2026, with Bitcoin near $59,500.

| Fit starting | Reading on 26 Jun 2026 | Fair value then |
|---|---|---|
| Jul 2010 (full history, as proposed) | **−1.69** | $529,141 |
| 2011 | −1.80 | $410,906 |
| 2013 | −1.84 | $223,240 |
| Jul 2015 (Coinbase's history) | −1.73 | $188,734 |
| 2017 | −1.52 | $132,461 |
| 2019 | −1.52 | $122,895 |

The proposed settings land 0.19 SD from his figure. A fit starting in 2017 or later lands on it, but choosing that start to match would be fitting the method to one number; it is shown, not adopted.

For comparison only: a log-log fit (a power law, the curve behind most "Bitcoin rainbow" charts) puts Bitcoin at fair value (+0.1 SD, fair value about $52,000). That is not what the owner specified, and it does not match Pal's figure.

## Things the owner should know before approving

1. **A straight line on a log chart assumes the same percentage growth forever.** For Bitcoin that is about 100% a year, which is why its "fair value" is $576,000 and its bands reach millions. The −1.7 reading mostly says that Bitcoin has grown more slowly in recent years than in 2010 to 2017.
2. **Three fits are meaningless: SUI, NEAR and ZEC have R² of 0.00 to 0.06.** The line is nearly flat and explains almost none of the price history, so "fair value" there is close to an average price. ZEC's "+2 SD overbought" is a reaction to its 2025–26 rally against a flat ten-year line.
3. **WAL and DEEP have falling lines** (−90% and −73% a year): their "fair value" assumes the decline continues. "Fair value" for them means "in line with its fall so far".
4. **Proposed extra honesty rule, not adopted without approval:** below an R² of 0.3, grey the dial and label it "the line does not fit this coin's history; reading not meaningful". This would grey SUI, NEAR and ZEC.

Sources: [Log-Regression Channels RV](https://www.tradingview.com/script/AWBVmz7a/) (not readable from here; description from search results), [Log Regression Channel v2](https://ar.tradingview.com/script/YDEqp4Zb-Log-Regression-Channel-v2/), [Blockonomi on Pal, June 2026](https://blockonomi.com/ex-goldman-sachs-exec-says-crypto-cycle-remains-mid-phase/), [Bitget on Pal](https://www.bitget.com/amp/news/detail/12560605479488), [Cryptonews on Pal](https://cryptonews.net/news/bitcoin/33698083/), [Pal on X, 2022](https://x.com/RaoulGMI/status/1502638171145842692).

## Owner's decisions (26 Nov 2026) and what was built

- **Full history for every coin**, start dates unchanged. Bitcoin reads −1.69 on 26 June 2026 against Pal's reported −1.5; the gap is recorded here and not tuned away.
- **R² rule adopted:** below 0.3 the dial is greyed with "the line does not fit this coin's history; reading not meaningful". On 26 Nov this greys SUI (0.01), NEAR (0.06) and ZEC (0.00).
- **Card layout:** the SD reading and zone lead; the "trend-based estimate" label follows; the fair value is in smaller text with its assumed growth ("assumes +101% a year"); then price now, the price at every band, the history used and R²; and on every card: "A constant-growth line drifts toward oversold as a coin's growth slows; read with care for older coins."
- **Licence:** Coin Metrics' terms grant use under Creative Commons Attribution-NonCommercial 4.0, and its attribution guidelines ask for the name "Coin Metrics" with a link to coinmetrics.io wherever its data is shown. This is a personal, non-commercial dashboard, so the use is covered. The credit is in the dashboard footer and the source list. **If the feed is ever used commercially (for example by a bot run as a business), this licence would no longer cover it.**
- **Data:** ten new history series from Coin Metrics, plus Coinbase live prices for the five coins not already tracked (ETH, ZEC, HYPE, WAL, DEEP). A newly added series now loads its full history automatically on its first run, marked as back-filled.
- **Context only, as specified:** the readings do not enter the buy / hold reading, the backdrop or any push. They appear in the daily digest as one line.
- **Tests:** 437 in all, 30 of them for this tab (the regression arithmetic, the seven zones and their edges, the honesty rules, live-price handling, the page, the digest line, and a check that a valuation change never causes a push).
- **Status:** built on the `claude/valuations` branch; phone screenshots sent; not published.
