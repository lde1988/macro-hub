# Coin valuations: new method (1-year z-score and 4-year trend channel)

Date: 26 November 2026. Status: built on `claude/valuations4`, replayed, not published.

## What changed (owner's instruction)

- **Removed:** the from-inception log-regression dial (Pal's method) and the stretch-from-200-day dial.
- **Short term, every coin:** natural log of the daily close; mean and sample standard deviation over the last 365 closes;
  reading = (log price today − mean) ÷ standard deviation. Fair value = exp(mean). Needs 365 days. Band prices −3 to +3 SD in dollars.
- **Long term, coins with 4 years of prices:** straight line through the log price against time over the last 1,461 days only,
  refitted daily; standard deviation of the residuals over the same window (population form, as before). Fair value with its
  implied growth ("trend +44% a year"). Greyed when R² is below 0.3.
- **Kept:** price against revenue (always last), its labels, the split fair-value band, the big number, context only.
- **Card line:** "Short term: compared with the last year. Long term: trend over the last 4 years."
- **Feed:** the `valuations` entries changed shape, so the feed version goes from 1.0 to 2.0, as FEED.md promises for any breaking
  change. Nothing outside `valuations` changed. No bot reads the feed yet.

## Replay at past lows and highs (point in time: each reading uses only prices known on that day)

Episode dates are each coin's own lowest or highest close in the window. Nothing was tuned.

| Coin | Episode | Date | Price | Short term (last year) | Long term (4-year channel) |
|---|---|---|---|---|---|
| BTC | 2018 low | 15 Dec 2018 | $3,185 | −2.66 (−2 SD oversold) | −2.86 (−2 SD oversold), trend +208%/yr, R² 0.89 |
| BTC | 2020 low | 12 Mar 2020 | $4,959 | −1.83 (−1 SD oversold) | −1.95 (−1 SD oversold), trend +118%/yr, R² 0.69 |
| BTC | 2021 first high | 13 Apr 2021 | $63,446 | +1.92 (+1 SD overbought) | +2.35 (+2 SD overbought), trend +54%/yr, R² 0.49 |
| BTC | 2021 second high | 8 Nov 2021 | $67,542 | +1.44 (+1 SD overbought) | +1.36 (+1 SD overbought), trend +66%/yr, R² 0.54 |
| BTC | 2022 June low | 18 Jun 2022 | $19,014 | −3.50 (−3 SD oversold) | −2.73 (−2 SD oversold), trend +100%/yr, R² 0.79 |
| BTC | 2022 November low | 9 Nov 2022 | $15,758 | −1.81 (−1 SD oversold) | −2.52 (−2 SD oversold), trend +84%/yr, R² 0.67 |
| BTC | 2025 high | 6 Oct 2025 | $124,824 | +1.56 (+1 SD overbought) | +0.67 (above fair value), trend +45%/yr, R² 0.54 |
| BTC | June 2026 low | 30 Jun 2026 | $58,525 | −1.89 (−1 SD oversold) | −2.90 (−2 SD oversold), trend +61%/yr, R² 0.79 |
| ETH | 2018 low | 15 Dec 2018 | $82.83 | −2.45 (−2 SD oversold) | not shown: under 4 years |
| ETH | 2020 low | 12 Mar 2020 | $110 | −2.30 (−2 SD oversold) | −1.43 (−1 SD oversold), trend +123%/yr, R² 0.40 |
| ETH | 2021 first high | 11 May 2021 | $4,156 | +2.22 (+2 SD overbought) | +3.00 (+2 SD overbought, on the edge), greyed: R² 0.05 |
| ETH | 2021 second high | 8 Nov 2021 | $4,811 | +1.49 (+1 SD overbought) | +1.64 (+1 SD overbought), greyed: R² 0.26 |
| ETH | 2022 June low | 18 Jun 2022 | $993 | −3.72 (−3 SD oversold) | −1.91 (−1 SD oversold), trend +153%/yr, R² 0.73 |
| ETH | 2022 November low | 9 Nov 2022 | $1,093 | −1.62 (−1 SD oversold) | −2.26 (−2 SD oversold), trend +161%/yr, R² 0.77 |
| ETH | 2025 high | 22 Aug 2025 | $4,831 | +2.33 (+2 SD overbought) | +1.76 (+1 SD overbought), greyed: R² 0.02 |
| ETH | June 2026 low | 6 Jun 2026 | $1,565 | −2.17 (−2 SD oversold) | −2.89 (−2 SD oversold), trend +22%/yr, R² 0.43 |
| SOL | 2018, 2020 lows | | | no data (prices begin April 2020) | |
| SOL | 2021 first high | 18 May 2021 | $56.07 | +2.21 (+2 SD overbought) | not shown: under 4 years |
| SOL | 2021 second high | 6 Nov 2021 | $258 | +1.67 (+1 SD overbought) | not shown: under 4 years |
| SOL | 2022 June low | 13 Jun 2022 | $27.60 | −1.88 (−1 SD oversold) | not shown: under 4 years |
| SOL | 2022 low (late) | 29 Dec 2022 | $9.54 | −2.18 (−2 SD oversold) | not shown: under 4 years |
| SOL | 2025 high | 18 Jan 2025 | $261 | +2.23 (+2 SD overbought) | +1.01 (+1 SD overbought), greyed: R² 0.15 |
| SOL | June 2026 low | 6 Jun 2026 | $62.07 | −2.10 (−2 SD oversold) | −2.23 (−2 SD oversold), trend +80%/yr, R² 0.56 |

## Read plainly

- **Short term was on the right side at every episode it could read**: oversold (green) at all 13 lows, overbought (red) at all 8 highs.
- **Long term agreed at the lows**: oversold at all 9 lows it could read. At highs it was weaker: BTC's 2025 high read only "above fair
  value"; ETH's and SOL's highs read overbought but greyed, because their 4-year lines fitted poorly.
- **But the short-term dial is red very often.** A coin that is rising sits above its own 1-year average most of the time. Since 2016,
  BTC's short-term reading was +1 SD or higher on **48% of days** (+2 or higher on 14%); ETH 37% (10%); SOL 31% (10%). It was −1 SD or
  lower on 17%, 19% and 27% of days. So "oversold" is the rarer and more telling signal; "overbought" mostly says the coin has been rising.
- **Sample:** 8 episodes for BTC, 8 for ETH, 6 for SOL, all hand-picked as the extremes; this shows the dials were on the right side at
  turning points, not that they found them in advance.

## Readings today (26 Nov, preview)

| Coin | Short term | Long term (4-year channel) |
|---|---|---|
| BTC | −1.60, −1 SD oversold (fair $74,534) | −2.13, −2 SD oversold (fair $121,572, trend +44%/yr, R² 0.62) |
| ETH | −1.52, −1 SD oversold | −1.84, greyed (R² 0.12) |
| SOL | −1.29, −1 SD oversold | −1.58, −1 SD oversold (trend +57%/yr, R² 0.38) |
| SUI | −1.31, −1 SD oversold | not shown: 3.3 years |
| LINK | −0.53, below fair value | −1.22, greyed (R² 0.10) |
| NEAR | +1.04, +1 SD overbought | +0.26, greyed (R² 0.00) |
| ZEC | +0.68, above fair value | +0.75, above fair value (trend +141%/yr, R² 0.65) |
| HYPE | +0.53, above fair value | not shown: 1.9 years |
| WAL | −1.43, −1 SD oversold | not shown: 1.5 years |
| DEEP | −1.77, −1 SD oversold | not shown: 2.0 years |

WAL now has a short-term reading: it has more than 365 days of prices.
