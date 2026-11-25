# Point 3: dial bands (approved)

Approved by the owner on 25 November 2026, including the six differences from the brief, with four
changes (below) and the answer to question 1: **the regime keeps the margin-debt signal "fired" for
12 months.** "Now" is the reading on 25 November 2026 from the hub's own first full calculation.

One colour rule for every dial: **green = supports buying crypto, amber = neutral, red = argues against.**

## Rules that apply to every dial

- A dial changes colour only after **two runs in a row** beyond a band edge.
- Price levels carry a **2% buffer**: the price dial turns green at $57,430, not $58,600, and back to amber at $59,770.
- The dollar index changes a dial only after **two ECB fixings in a row** at least **0.3** beyond a level.
- If a source fails, the dial keeps its last colour, greyed out.
- Every number below lives in `config/thresholds.yaml`, each with a comment.

## A. Is it cheap?

| # | Dial | Green | Amber | Red | Why | Now |
|---|---|---|---|---|---|---|
| 1 | Bitcoin price (shows price ÷ realised price, live from Bitview) | At or below $58,600 | Above $58,600, up to 2.4x realised price | Above 2.4x realised price (about $127,400 today) | Owner's levels. **Differs from the brief:** it said "amber up to $73,000" and left $73,000 to 2.4x undefined; I treat that whole stretch as amber. Markers on the dial: realised price $53,100, long-term holder cost $48,300, short-term holder cost $72,400, all live | $59,200, 1.12x: amber |
| 2 | Bitcoin weekly close | Weekly close above $73,000 | $70,000 to $73,000 with no break in force | A weekly close below $70,000, until a weekly close above $73,000 | Coutts' regime filter. A break stays in force until reclaimed | $61,163: red |
| 3 | Size of latest weekly move (standard deviations, against the past 52 weeks) | -2 or lower | Between -2 and +2 | +2 or higher | A fall this large is washout-sized; a rise this large is blow-off-sized | -1.0 (a -6.4% week): amber |
| 3a | LTH-SOPR, 30-day (7-day shown beside it as early warning) | At or below 0.7 | Above 0.7, up to 3.0 | Above 3.0 | Owner's green edge. Checked against history: the 30-day reading bottomed at 0.49 (2015), 0.47 (Jan 2019), 0.47 (Dec 2022), but only 0.75 in Apr 2020. Red edge is mine: above 3.0 long-term holders are selling at large profits, as in 2017, 2021 and mid-2024 | 0.88 (7-day 0.72): amber |
| 3a | Net realised losses, 30-day, as a share of realised cap: percentile against all history | 95th percentile or above | Below the 95th | none | Owner's change 4. At the 2015, 2018, 2020 and June 2022 lows this stood at the 99th to 100th percentile (5.2% to 6.7% of realised cap); December 2022 was the 98th; February 2026 only the 93rd (2.75%). The February 2026 figure is kept as a marker only | 1.82% of realised cap, 86th percentile: amber (65% of the February peak) |
| 3b | Bitcoin ÷ Nasdaq-100, against its own 100-day average | 2% or more above | Within 2% | 2% or more below | Trend of Bitcoin against tech stocks | -9.6%: red |
| 3c | Altcoin value (stablecoins removed) ÷ Bitcoin value, 30-day change | Up 5% or more | Between | Down 5% or more | No free history exists, so the dial is amber and greyed until it has collected 30 days of its own | 0.49x: no colour yet |
| 3c | Watchlist (SUI, SOL, NEAR, LINK, TAO) priced in Bitcoin, equal-weight 30-day change | Up 10% or more | Between | Down 10% or more | Shows whether altcoins are gaining or losing against Bitcoin. Each coin's own number is listed under the dial | -5.3%: amber |

Short-term holder cost basis is shown as a marker on dial 1, not as its own dial: whether price below it is "good" or "bad" is ambiguous, so I would not colour it.

## B. Is stress still building?

| # | Dial | Green | Amber | Red | Why | Now |
|---|---|---|---|---|---|---|
| 4 | Margin debt, 3-month change annualised | No reading above +100% in the past 12 months | Was above +100% in the past 12 months, now back at or above 0 ("fading") | Was above +100% in the past 12 months and now below 0 (signal fired) | Owner's rule. See question 1 below on the FRAGILE regime | +9.1% after +129% in June: amber; regime keeps the signal "fired" for 12 months (owner's answer) |
| 5 | SOFR minus IORB, 5-day median | 0bp or less | Above 0 to 5bp | Above 5bp | Owner's bands; agreed | about +2bp: amber |
| 6 | 2-year yield, 20-day change | Down 15bp or more | Between | Up 25bp or more | Owner's bands; agreed | -6bp: amber |
| 6 | 10-year yield, 20-day change (curve T10Y2Y shown as a number) | Down 15bp or more | Between | Up 25bp or more | Owner's bands; agreed. The curve gets no colour of its own: steepening can be good or bad | -8bp: amber |
| 6a | Rate-hike pricing: 2-year minus Fed funds, 20-day change (Fed target shown as a number) | Down 20bp or more | Between | Up 10bp or more | **Differs from the brief**, which said "red if rising": any rise at all would flip the dial on 1bp of noise | -6bp (level +75bp): amber |
| 6b | CPI, latest month-on-month | 0.2% or less | 0.3% | 0.4% or more | 0.2% a month is roughly the Fed's 2% target; 0.4% is about 5% a year | +0.4% in October: red |
| 6b | 5-year breakeven inflation | 2.4% or less | Above 2.4% to 2.7% | Above 2.7% | Normal range is about 2.2 to 2.5%; it peaked at 3.6% in 2022 | 2.11%: green |
| 6c | Global liquidity proxy (Fed + ECB + Bank of Japan assets in dollars, plus US M2), year-on-year | Up 5% or more | 0 to 5% | Falling | Labelled "proxy". Not Coutts' index | +0.8%: amber |
| 7 | Dollar index (computed from ECB fixings; published close shown beside it as a check) | Below 100, or back below 102.5 after being above | Everything else | Above 102.5 and higher than 20 fixings ago | Owner's bands; agreed, with the 0.3 two-fixing rule | 103.88 and rising: red |
| 8 | S&P 500 | Everything else | Below the 10-month average mid-month, or 10% below the 1-year high | A finished month-end close below the 10-month average, or 20% below the 1-year high | Owner's bands; agreed | 7,237, 7.4% below high, under its 10-month average (7,304) mid-month: amber |
| 9 | Bitcoin funding rate, 30-day average annualised (days negative shown) | Negative | 0 to 30% | 30% or more | Owner's bands; agreed. Average of the Binance, Bybit and OKX dollar-stablecoin contracts | pending the Coinalyze load (about +6.7%, amber, at the source check) |
| 10 | Altcoin ÷ Bitcoin open interest, percentile | Below the 50th | 50th to 90th | 90th or above | Owner's bands; agreed. Percentile runs from October 2022, the start of Coinalyze's history | pending the history pull |
| 11 | Stablecoin supply, 30-day change | Positive | 0 to -3% | Below -3% | Owner's bands; agreed | -5.9%: red |

## C. Credit-event risk

| # | Dial | Green | Amber | Red | Why | Now |
|---|---|---|---|---|---|---|
| 12 | High-yield spread, 3-month change | Below +75bp | +75 to +150bp | Above +150bp | Owner's bands; agreed | +96bp (level 3.63%): amber |
| 13 | CCC spread minus BB spread, 3-month change | Below +150bp | +150 to +300bp | Above +300bp | The weakest borrowers move about twice as much as high yield overall, so the edges are doubled | +293bp (gap 11.68 points): amber, 7bp from red |
| 14 | BBB spread, 3-month change | Below +25bp | +25 to +50bp | Above +50bp | Investment grade moves about a third as much as high yield | +21bp: green |
| 15 | Chicago Fed NFCI | -0.25 or lower | Above -0.25 to 0 | Above 0 | Zero is average conditions since 1971; above zero is tighter than average | -0.48: green |
| 15 | St. Louis Fed stress index | 0 or lower | Above 0 to 1 | Above 1 | Zero is normal stress; 1 is one standard deviation above | -0.87: green |
| 16 | AI-debt canaries: equal-weight basket's 3-month return minus the S&P 500's | Better than -10 points | -10 to -25 points | Worse than -25 points | Basket proposed: CoreWeave, Oracle, Nebius, Applied Digital, IREN. All five have a working price feed | -42 points: red |
| 17 | Private credit: BIZD fall from its 3-month high | Less than 6% | 6% to 12% | 12% or more | Owner's decision (point 2) to use the 3-month high. A quarterly dividend alone knocks about 3% off the price, so green must allow for that | -9.6%: amber |
| 18 | Regional banks: KRE fall from its 1-year high | Less than 15% | 15% to 25% | 25% or more | Regional banks swing more than the market; they fell over 40% in March 2023 | -10.5%: green |
| 18 | Fed discount window borrowing | $10bn or less, and not up $5bn in 4 weeks | Above $10bn, or up $5bn in 4 weeks | Above $25bn, or up $10bn in 4 weeks | It reached $153bn in March 2023. Checked against history: over the past year the median was $6.0bn, the highest $11.0bn, and the largest 4-week rise $4.3bn, so the edges stand | $9.1bn: green |
| 18 | Fed standing repo facility, 5-day median | $1bn or less | Above $1bn to $10bn | Above $10bn | The median ignores routine one-day quarter-end spikes | about $0: green |

## D. Has the turn started?

For these, green = the turn signal has fired, amber = not fired, red = moving the wrong way.

| # | Dial | Green | Amber | Red | Why | Now |
|---|---|---|---|---|---|---|
| 19 | Dollar reversal | Closed back below 102.5 after being above (label "confirmed" below 100) | Above 102.5 but lower than 20 fixings ago | Above 102.5 and rising | Owner's levels, with the 0.3 two-fixing rule | 103.88, rising: red |
| 20 | Front-end easing: 2-year yield, 20-day change | Down 25bp or more | Between | Up 25bp or more | Owner's level | -6bp: amber |
| 21 | Fed buying: T-bill holdings, 4-week change | Up $20bn or more | Between | Down $20bn or more | Owner's level. Units confirmed: FRED reports millions | +$13bn: amber |
| 21 | Fed buying: bank reserves, 4-week change | Up **$150bn** or more | Between | Down $150bn or more | **Widened from $75bn**, which fired 12 times in two years. Never confirms a turn on its own | +$17bn: amber |
| 22 | Stablecoin supply turning | 30-day change positive | Negative but less negative than 30 days ago | Negative and getting worse | Owner's signal | -5.9%, worse than a month ago: red |
| 23 | Bitcoin weekly close reclaim | Weekly close above $73,000 ends a break; stays green for 12 weeks while weekly closes hold above $70,000 | No break in force | Break in force | Owner's level. The 12 weeks is mine, so an old reclaim does not count as a fresh turn forever | red |
| 24 | Treasury buybacks, liquidity-support operations only: latest 4 weeks against the average 4 weeks of the prior 12 | 1.5x or more (step up) | Between | 0.67x or less (step down) | Owner's level, kept at 1.5x so the August 2026 step-up Coutts cites fires (it reached 1.6x). It fires often (11 times in two years); the freshness rule and the two-family rule limit what that can do | 0.7x: amber |
| 25 | Rate hikes being priced out: dial 6a, 20-day change | Down **30bp** or more | Between | Up 10bp or more | **Widened from 20bp**, which fired 9 times in two years. Dial 6a itself keeps its approved 20bp band | -6bp: amber |

## Families (owner's change 3)

Each family counts once. A buy is blocked only by a *fresh* red (within 5 trading days) in a family marked "blocks a buy".

| Family | Dials | Blocks a buy? |
|---|---|---|
| Rates and dollar | 2-year yield, 10-year yield, rate-hike pricing, CPI, breakeven, liquidity proxy, dollar index | No |
| Money-market funding | SOFR minus IORB, discount window, standing repo facility | **Yes** |
| Credit spreads | High yield, CCC minus BB, BBB, Chicago Fed NFCI, St. Louis stress index | **Yes** |
| AI and private credit | AI-debt canaries, BIZD | No |
| Banks | KRE | **Yes** |
| Crypto leverage | Funding rate, altcoin open interest, stablecoin supply | No |
| Equities | S&P 500, margin debt | No |

Placements agreed by the owner (25 Nov): the two Fed stress indexes sit in credit spreads; stablecoin supply in crypto leverage; margin debt in equities; CPI, breakeven and the liquidity proxy in rates and dollar.

## Buy / hold / sell rules as built (owner's changes 1 to 3)

Checked in this order; the first that applies wins.

1. **SELL (reduce risk):** froth (funding at 30% or more, or altcoin open interest at or above its 90th percentile, or price above 2.4x realised price) AND liquidity deteriorating (the margin-debt signal has fired within 12 months, or the dollar dial is red, or **two or more families** are red).
2. **BUY (CONFIRMED):** price at or below 1.3x realised price AND the turn is confirmed AND no fresh red in funding, credit spreads or banks.
3. **BUY (STAGED):** price dial green AND (LTH-SOPR 30-day green OR net realised losses green) AND no fresh red in those three families. No turn signal needed.
4. **HOLD:** everything else, always saying which kind. CAUTION is added when the weekly close is below $70,000 and the price dial is not green.

**Turn confirmed** = the dollar reversal dial is *freshly* green, OR two of these families are freshly green together: rates (dials 20, 25); Fed and Treasury (T-bill holdings, buybacks); crypto liquidity (dial 22). Bank reserves are in no family, so alone they never confirm a turn. The weekly-close reclaim (dial 23) is a price signal and is in no family either.

**Fresh** (owner's decision, 25 Nov) = the dial turned green within the last 13 weeks. Dial colours stay as approved: a dial green for longer still shows green, but it no longer counts toward "turn confirmed" or the TURN regime. TURN needs at least one freshly green group D dial.

**Altcoins:** BUY only when the Bitcoin reading is BUY and altcoin open interest is below its 50th percentile.

The original single buy rule is kept in the code for the side-by-side replay at point 6.

## How often each turn signal fired, 25 Nov 2024 to 24 Nov 2026 (owner's change 2)

Replayed day by day with the no-flapping rule, using only what was known each day.

| Dial | Times it turned green | Share of days green | Action |
|---|---|---|---|
| 19 Dollar reversal | 2 | 80% | Counts only while fresh (13 weeks) |
| 20 Front-end easing (2-year down 25bp) | 4 | 3% | Kept |
| 25 Hikes priced out | 9 at 20bp | 9% | Widened to 30bp: 3 times, 1% of days |
| 21 T-bill holdings up $20bn | 2 | 33% | Kept; counts only while fresh |
| 21 Bank reserves | 12 at $75bn | 23% | Widened to $150bn: 3 times, 4% of days |
| 24 Buybacks step up | 11 at 1.5x | 16% | **Kept at 1.5x by the owner** (2.0x fired once) |
| 22 Stablecoin supply turning | 5 | 74% | Counts only while fresh |
| 23 Weekly close reclaim | 3 | 28% | Kept |

## "Turn confirmed" under the fresh rule (owner's question, 25 Nov)

| Setting | Share of days "turn confirmed" | Separate spells | TURN regime share of days |
|---|---|---|---|
| Before the fresh rule | 82% | 4 | 99% (721 of 730) |
| Fresh rule, buybacks at 1.5x (as built) | **24.7%** | 9 | 70% |
| Fresh rule, buybacks at 2.0x | 23.4% | 7 | 67% |

Putting buybacks back to 1.5x costs little: 1.3 points of days and two extra short spells (27–28 Nov 2024 and 7–11 Dec 2024).

Spells at 1.5x: 27–28 Nov 2024; 7–11 Dec 2024; 4–7 Apr 2025; 11 Apr–10 Jul 2025 (the dollar's fall through 102.5); 26 Dec 2025–5 Jan 2026; 18–22 Jan 2026; 3–26 Mar 2026; 26 Aug–10 Sep 2026; 1–22 Oct 2026.

**Still worth knowing:** the TURN *regime* (any one fresh turn dial) would have shown on 70% of days, mostly as "TURN (early, not confirmed)", because eight dials each stay fresh for 13 weeks. The banner always says whether the turn is confirmed. If that is too loose, the simple fix is to show TURN only when the turn is confirmed; this is the owner's call and is not built.

## Levels for the history replay (owner's decision, 25 Nov)

Fixed dollar levels mean nothing in earlier cycles, so the replay uses moving stand-ins:

| Live level (colours the dial) | Replay stand-in | Today |
|---|---|---|
| Value zone $58,600 | 1.10x realised price | $58,400 |
| Reclaim line $73,000 | Short-term holder realised price | $72,400 |
| Break line $70,000 | 0.96x short-term holder realised price | $69,500 |

Live dials keep the fixed levels and show the moving equivalents beside them, so drift between the two is visible.

## Dashboard layout (owner's instruction, for point 7)

Lead with the reading and one line per family (colour plus a sentence). Individual dials go underneath, grouped by family, so a phone screen is not 39 dials long.

## Dollar index accuracy over a longer window

Against the published close over ten years (2,491 days) the computed value was within 0.3 on 76% of days; the average gap was 0.21. The 63-day figure in the point 2 report (57 of 63 days) was kinder than the long-run record. The dial is labelled "ECB fixing, not the New York close" and shows the published close beside it.
