# Coin tab additions: stretch from trend, price against revenue, Bitcoin moving averages

Date: 26 November 2026. Status: items 1 and 3 built on the `claude/valuations2` branch with phone screenshots sent, not published. Item 2 not built: the fees findings are below for the owner first.

## 1. Stretch from trend (built)

The natural log of (price ÷ 200-day moving average), as a z-score against the coin's own history of that measure, same seven zones. At least 365 days of the measure is needed (so at least 565 days of prices); below that it is greyed "too little history". Labelled "Compared with its own recent trend, not a fair value". Shown under the log-regression dial, or first where that dial is greyed.

| Coin | Log-regression | Stretch from trend | Price ÷ 200-day average (usual) | Days scored |
|---|---|---|---|---|
| BTC | −1.71 | −0.71, fair value | 0.84 | 5,776 |
| ETH | −1.54 | −0.68, fair value | 0.80 | 3,929 |
| SOL | −1.23 | −0.51, fair value | 0.81 | 2,222 |
| SUI | greyed (fit) | −0.32, fair value: **leads the card** | 0.80 | 998 |
| LINK | −1.32 | −0.34, fair value | 0.91 | 3,146 |
| NEAR | greyed (fit) | +0.35, fair value: **leads** | 1.10 | 2,034 |
| ZEC | greyed (fit) | −0.14, fair value: **leads** | 0.94 | 3,481 |
| HYPE | greyed (short) | −1.05, −1 SD oversold: **leads** | 0.85 | 514 |
| WAL | greyed (short) | too little history (362 of 365 days) | | 362 |
| DEEP | greyed (short) | −0.00, fair value: **leads** | 0.64 | 549 |

WAL will get a stretch reading in three days, when it reaches 365 days of the measure.

## 2. Price against revenue (not built: findings for the owner)

Fully diluted value (price × total or maximum supply) ÷ the last 365 days of fees on DefiLlama. A z-score needs 365 days of the multiple, so at least 730 days of fees.

| Coin | DefiLlama series | Fees history | Fees, last 365 days | FDV now | Multiple now | Days of multiple | Reading now | Still to unlock | How FDV history is built |
|---|---|---|---|---|---|---|---|---|---|
| HYPE | Hyperliquid (perps, spot, L1) | 703 days, from Dec 2024 | $897.5m | $61.4bn | 68x | 339 | too little history (26 days short) | 75% | price × 1bn max supply |
| SUI | Sui (chain gas fees) | 878 days, from Jul 2024 | $2.3m | $6.7bn | 2,935x | 514 | +1.81 SD | 59% | price × 10bn max supply |
| WAL | Walrus Protocol | 611 days, from Mar 2025 | $0.11m | $0.11bn | 970x | 247 | too little history | 47% | price × 5bn max supply |
| DEEP | DeepBook | 191 days, from May 2026 | $0.36m (6 months only) | $0.12bn | none | 0 | no reading: under a year of fees | 75% | price × 10bn max supply |
| SOL | Solana (chain fees) | 2,139 days, from Jan 2021 | $228.7m | $44.9bn | 196x | 1,775 | −0.67 SD | 7% | price × **today's** supply (approximation) |
| ETH | Ethereum (chain fees) | 4,129 days, from Aug 2015 | $170.3m | $206.6bn | 1,213x | 3,765 | +0.90 SD | 0% | price × supply history (Coin Metrics) |
| LINK | Chainlink | 1,208 days, from Aug 2023 | $62.1m | $9.0bn | 145x | 843 | −1.27 SD | 23% | price × 1bn max supply |
| NEAR | Near (chain fees) | 2,234 days, from Oct 2020 | $1.1m | $4.0bn | 3,611x | 1,870 | +0.73 SD | 0% | price × **today's** supply (approximation) |

Usable for a z-score today: **SUI, SOL, ETH, LINK, NEAR**. HYPE becomes usable in about four weeks; WAL in about four months; DEEP in about a year and a half.

Things the owner should know:

- **"Fees" means different things.** For HYPE it is trading fees (mostly used to buy back HYPE). For SOL, ETH, SUI and NEAR it is the gas users pay to the chain, much of which is burned. For LINK it is payments to the Chainlink network. The multiples are not comparable across coins; only each coin against its own history is meaningful, which is what the z-score does.
- **ETH's fee history mixes regimes:** the 2021 peak and the post-2024 collapse of fees after cheaper rollups. A "+0.90 SD" partly reflects that structural fall.
- **SOL and NEAR have no free supply history.** Their past FDV would be built from today's supply, overstating the past multiple by the supply growth since (roughly 5% a year for both). That biases their readings toward "cheap now".
- **Unlock share** comes from CoinGecko (current only), as 1 − circulating ÷ total supply.
- **DefiLlama's fee data is free and needs no key.** Its terms ask for attribution; it would be credited in the footer as DefiLlama already is.

## 3. Bitcoin moving averages (built, context only)

A dial in "Is it cheap?": price ÷ 200-day average, green at 0.8 or lower, red at 2.4 or higher, amber between. The 200-week average is shown as a marker in words ("price is above / below the 200-week average"). It is listed in the group but **not counted** in the group's colour, the tally, the reading or any push, until it has been replayed and approved.

Now: 0.84x its 200-day average ($72,027), amber; price below the 200-week average ($68,168).

### How both lined up with past lows and highs (Coin Metrics prices from 2010)

| Episode | Date | Price | Price ÷ 200-day average | Dial | 200-week average | Price vs 200-week |
|---|---|---|---|---|---|---|
| 2013 April high | 9 Apr 2013 | $231 | 8.26 | red | n/a (under 200 weeks of history) | |
| 2013 December high | 4 Dec 2013 | $1,135 | 5.71 | red | n/a | |
| 2015 low | 14 Jan 2015 | $176 | 0.40 | green | $191 | 0.92x, below |
| 2017 high | 16 Dec 2017 | $19,641 | 3.78 | red | $1,160 | 16.9x, above |
| 2018 low | 15 Dec 2018 | $3,185 | 0.51 | green | $3,171 | 1.00x, on it |
| 2020 low | 12 Mar 2020 | $4,959 | 0.57 | green | $5,488 | 0.90x, below |
| 2021 first high | 13 Apr 2021 | $63,446 | 1.97 | amber | $11,165 | 5.7x, above |
| 2021 second high | 8 Nov 2021 | $67,542 | 1.48 | amber | $17,106 | 4.0x, above |
| 2022 June low | 18 Jun 2022 | $19,014 | 0.48 | green | $22,295 | 0.85x, below |
| 2022 November low | 9 Nov 2022 | $15,758 | 0.67 | green | $23,889 | 0.66x, below |
| 2024 March high | 13 Mar 2024 | $73,082 | 1.85 | amber | $31,937 | 2.3x, above |
| 2025 high | 6 Oct 2025 | $124,824 | 1.18 | amber | $53,471 | 2.3x, above |
| 2026 first-half low | 30 Jun 2026 | $58,525 | 0.78 | green | $62,433 | 0.94x, below |

Read plainly:

- **Lows:** the 200-day dial was green at all six lows since 2015. Price was at or below the 200-week average at all six.
- **Highs:** red at the 2013 and 2017 highs, but **not since**: the 2021, 2024 and 2025 highs peaked at 1.2 to 2.0 times the 200-day average, short of the 2.4 red line. Each cycle's peak has been less stretched than the one before.
- **False greens:** green also fired on days that were not lows. Since 2015 it was green on 16% of days, including spells in mid-2021, early 2022 and November to December 2025 (around $85,000 to $90,000, seven months before the 2026 low). Green says "cheap against the recent trend", not "the low is in".
- These figures use today's bands with hindsight; no band was tuned to them.
