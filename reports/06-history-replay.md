# Point 6: the rules replayed over history

Date: 25 November 2026. Replay period: 1 September 2017 to 24 November 2026 (3,372 days), one step per day.
The rules and thresholds are exactly those in `config/thresholds.yaml`. Nothing was tuned after seeing the result.

## Read this first: how far to trust it

- **The sample is tiny.** Five cycle lows and four cycle highs. The new rule produced 4 separate buy periods and the sell rule 8. No statistic from this is reliable; treat it as a sanity check, not proof.
- **Hindsight is baked into some bands.** The LTH-SOPR edge (0.7) and the net-loss edge (95th percentile) were chosen knowing where past lows sat. BUY (STAGED) passing 2018 and 2022 is therefore partly circular.
- **Moving stand-ins replace fixed dollar levels** (owner's decision): value zone = 1.10x realised price; reclaim line = short-term holder realised price; break line = 0.96x it. The dollar levels (102.5 and 100) stay fixed, which suits 2022 but means little in 2018, when the dollar index sat near 97.
- **Back-filled data is today's version of history.** Revised figures (CPI, margin debt, Fed balance sheet) appear as later revised, dated by their usual publication lag. A live system would sometimes have seen different first prints.
- **Daily steps.** "Two runs in a row" means two days here; live it means 30 minutes.

## Yardsticks, fixed before running

- A buy or sell *spell* = flagged days less than 15 days apart.
- A buy spell is **right** if Bitcoin is higher 365 days after the spell's first day; a sell spell is right if it is lower.
- At a cycle low or high a rule is **silent** if it gave no buy (low) or sell (high) within 60 days either side.
- The sell rule is the same in both columns (the current one, counting families). Only the buy rule differs.

## Episode by episode, old and new side by side

| Episode | New rule (two-level buy) | Original rule | Dials with no data |
|---|---|---|---|
| **2017 high**, 16 Dec 2017, $19,650 | **Silent.** "Hold: frothy, but liquidity is not deteriorating" | Same (sell rule is shared) | 12 of 39 |
| **2018 low**, 15 Dec 2018, $3,183 | **Right.** BUY (STAGED) from 27 Nov 2018 at $3,775: 18 days early, 19% above the low. +99% a year later | **Right.** BUY from 21 Nov 2018 at $4,545: 43% above the low. +68% a year later | 9 of 39 |
| **2020 low**, 12 Mar 2020, $4,857 | **Wrong on the day, then right.** Showed SELL on the day of the low (30-day funding average still 41%). BUY (CONFIRMED) on 27 Mar at $6,372: 15 days after, 31% above the low. +777% a year later | **Silent** on the buy; same SELL on the day | 7 of 39 |
| **2021 first high**, 13 Apr 2021, $63,588 | **Early.** SELL from 16 Jan 2021 at $36,007, three months and 43% before the high. Counted wrong (+20% a year later) | Same | 7 of 39 |
| **2021 second high**, 8 Nov 2021, $67,555 | **Right.** SELL from 8 Oct 2021 at $53,964, a month early. -64% a year later | Same | 7 of 39 |
| **2022 June low**, 18 Jun 2022, $18,949 | **Wrong first, then right.** BUY (CONFIRMED) on 27 May at $28,598 on a false dollar reversal: 51% above the low, -6% a year later, -45% at worst. On the low itself: hold, blocked by fresh red in banks. BUY (STAGED) from 22 Jun at $19,968: +50% a year later | **Right, late.** First BUY 8 Jul 2022 at $21,582, 20 days after the low | 7 of 39 |
| **2022 November low**, 21 Nov 2022, $15,760 | **Right.** BUY (STAGED) on 107 of the 121 days around the low, including the day itself | **Right.** BUY from 6 Nov 2022 at $20,909, and on the day | 7 of 39 |
| **2025 high**, 6 Oct 2025, $124,720 | **Silent.** "Hold: neither cheap nor frothy": price was under 2.4x realised price and funding only 6% | Same | 2 of 39 |
| **2026 first-half low**, 30 Jun 2026, $58,524 | **Silent at the low.** Price never confirmed inside the value zone and LTH-SOPR bottomed at 0.76. Earlier, BUY (CONFIRMED) on 3–25 Mar 2026 at $68,336: about 13% under water today, too recent to judge | **Silent** | 2 of 39 |

**Score at the lows:** new rule gave a buy near 4 of 5; original rule near 3 of 5. Neither caught 2026.
**Score at the highs:** the sell rule fired near 2 of 4, and one of those was three months early.

## Every spell

| Rule | Spells | Right | Wrong | Too recent | Days flagged |
|---|---|---|---|---|---|
| New: any BUY | 4 | 2 | 1 | 1 | 335 |
| New: BUY (STAGED) alone | 2 | 2 | 0 | 0 | 262 |
| New: BUY (CONFIRMED) alone | 6 | 4 | 1 | 1 | 73 |
| Original BUY | 5 | 5 | 0 | 0 | 152 |
| SELL | 8 | 3 | 5 | 0 | 277 |

The new rule's "wrong" spell is the whole of May 2022 to February 2023 judged from its first day ($28,598). Most of its 213 days were bought far lower.

## What the replay says, plainly

1. **The two-level buy does what you wanted.** It bought 2020, which the original rule missed entirely, and it was in the market much longer near the 2018 and 2022 lows (335 flagged days against 152).
2. **Its cost is one bad early entry.** BUY (CONFIRMED) in late May 2022 came from the dollar dipping back under 102.5 for a few days before climbing to 114. A "confirmed" turn was a false one.
3. **The original rule never bought wrong, but only because it rarely bought.** Five for five on 152 days, and silent in 2020.
4. **The sell rule is the weak part.** Five of eight spells were wrong by the 12-month test: February and August 2020, January 2021, March 2024 and November 2024. Two of those were followed by sharp falls within weeks (-49% after February 2020), so "wrong" at 12 months hides some short-term value, but as a reduce-risk signal for a mid-term portfolio it fired too early, too often.
5. **Funding lags.** A 30-day average kept the reading on SELL on the very day of the March 2020 low.
6. **Both rules were silent at both the 2017 and 2025 highs.** In 2017 there was froth but nothing counted as deteriorating liquidity; in 2025 price never reached 2.4x realised price.
7. **Regime banner:** with "TURN only when confirmed", TURN showed on 14% of days. BREAK 42%, STRESS BUILDING 41%, CALM 4%, FRAGILE under 1%. STRESS BUILDING on four days in ten is a lot: one red dial among 23 is enough to trigger it.

## What could not be replayed

| Dial or family | Available from | Effect on the replay |
|---|---|---|
| Credit spreads (high yield, CCC minus BB, BBB) | 24 Feb 2024 | Missing at every past low. The buy-blocking "credit spreads" family ran on the two Fed stress indexes alone |
| Altcoin ÷ Bitcoin open interest | Not in this replay | Coinalyze history starts Oct 2022 and is still loading. One of the three froth tests was absent throughout; the altcoin line could not be replayed |
| Altcoin value against Bitcoin | Never | No free history exists |
| Funding rate | 20 Feb 2020 | Absent at the 2017 high and 2018 low |
| Treasury buybacks | 26 Jun 2024 | The programme restarted in 2024 |
| AI-debt canaries | 1 Jul 2025 | Left out earlier on purpose: CoreWeave listed in March 2025 |
| Altcoin watchlist | 28 Jul 2019 | Only LINK that early; SOL from 2021, SUI 2023, TAO 2024 |
| SOFR minus IORB | 10 Apr 2018 | Uses the older reserves rate before July 2021 |
| Stablecoin supply | 1 Feb 2018 | Absent at the 2017 high |
| Regional banks (KRE) | 1 Dec 2017 | Fine from then |
| **Episodes that cannot be replayed at all** | | The 2015 low and the 2013 high: no S&P 500 before late 2016 on FRED and Coinbase prices only from mid-2015 |

## Not changed

No rule, band or threshold was altered in response to these results. Possible changes the results suggest (a longer confirmation for the dollar reversal; a faster funding measure; a stricter sell rule; a higher bar for STRESS BUILDING) are the owner's to decide and would themselves be fitted to this small sample.

## Files

- `06-replay-daily.csv`: every day's regime, both readings, and every dial's colour and value.
- The tool that produced this: `tools/replay_report.py` on the `claude/build` branch.

---

# Appendix: raw output of the replay tool

Replay 2017-09-01 to 2026-11-24: 3372 days.

## Days in each reading

| | new rule | original rule |
|---|---|---|
| BUY | 0 | 152 |
| BUY (CONFIRMED) | 73 | 0 |
| BUY (STAGED) | 262 | 0 |
| HOLD | 2760 | 2943 |
| SELL | 277 | 277 |

Regime days: BREAK 1401, STRESS BUILDING 1366, TURN 472, CALM 122, FRAGILE 11

## Every spell, judged 12 months on

### New rule: BUY (STAGED)

| spell | days flagged | price at start | 6 months later | 12 months later | worst fall within 12 months | verdict |
|---|---|---|---|---|---|---|
| 27 Nov 2018 to 28 Mar 2019 | 88 | $3,775 | +131% | +99% | -16% | right |
| 22 Jun 2022 to 21 Jan 2023 | 174 | $19,968 | -16% | +50% | -21% | right |

Spells: 2; right 2, wrong 0, too recent 0.

### New rule: BUY (CONFIRMED)

| spell | days flagged | price at start | 6 months later | 12 months later | worst fall within 12 months | verdict |
|---|---|---|---|---|---|---|
| 29 Mar 2019 to 03 Apr 2019 | 6 | $4,091 | +100% | +53% | +0% | right |
| 27 Mar 2020 to 13 Apr 2020 | 14 | $6,372 | +68% | +777% | -8% | right |
| 27 May 2022 to 12 Jun 2022 | 13 | $28,598 | -42% | -6% | -45% | wrong |
| 01 Aug 2022 to 20 Aug 2022 | 12 | $23,274 | -2% | +28% | -32% | right |
| 24 Jan 2023 to 06 Feb 2023 | 14 | $22,636 | +29% | +77% | -11% | right |
| 03 Mar 2026 to 25 Mar 2026 | 14 | $68,336 | +13% | n/a | -14% | too recent |

Spells: 6; right 4, wrong 1, too recent 1.

### New rule: any BUY

| spell | days flagged | price at start | 6 months later | 12 months later | worst fall within 12 months | verdict |
|---|---|---|---|---|---|---|
| 27 Nov 2018 to 03 Apr 2019 | 94 | $3,775 | +131% | +99% | -16% | right |
| 27 Mar 2020 to 13 Apr 2020 | 14 | $6,372 | +68% | +777% | -8% | right |
| 27 May 2022 to 06 Feb 2023 | 213 | $28,598 | -42% | -6% | -45% | wrong |
| 03 Mar 2026 to 25 Mar 2026 | 14 | $68,336 | +13% | n/a | -14% | too recent |

Spells: 4; right 2, wrong 1, too recent 1.

### Original rule: BUY

| spell | days flagged | price at start | 6 months later | 12 months later | worst fall within 12 months | verdict |
|---|---|---|---|---|---|---|
| 21 Nov 2018 to 03 Apr 2019 | 94 | $4,545 | +68% | +68% | -30% | right |
| 08 Jul 2022 to 08 Jul 2022 | 1 | $21,582 | -21% | +40% | -27% | right |
| 06 Aug 2022 to 18 Aug 2022 | 12 | $22,961 | +2% | +26% | -31% | right |
| 06 Nov 2022 to 07 Dec 2022 | 32 | $20,909 | +36% | +68% | -25% | right |
| 25 Dec 2022 to 21 Jan 2023 | 13 | $16,829 | +81% | +159% | -2% | right |

Spells: 5; right 5, wrong 0, too recent 0.

### SELL (same rule in both)

| spell | days flagged | price at start | 6 months later | 12 months later | worst fall within 12 months | verdict |
|---|---|---|---|---|---|---|
| 20 Feb 2020 to 15 Mar 2020 | 25 | $9,610 | +23% | +483% | -49% | wrong |
| 20 Aug 2020 to 30 Aug 2020 | 11 | $11,864 | +335% | +316% | -15% | wrong |
| 16 Jan 2021 to 20 May 2021 | 99 | $36,007 | -12% | +20% | -17% | wrong |
| 07 Sep 2021 to 08 Sep 2021 | 2 | $46,894 | -17% | -59% | -60% | right |
| 08 Oct 2021 to 27 Nov 2021 | 51 | $53,964 | -22% | -64% | -66% | right |
| 01 Mar 2024 to 14 Apr 2024 | 37 | $62,437 | -5% | +38% | -14% | wrong |
| 13 Nov 2024 to 28 Dec 2024 | 45 | $90,494 | +14% | +10% | -16% | wrong |
| 19 Jan 2025 to 04 Feb 2025 | 7 | $101,211 | +16% | -9% | -25% | right |

Spells: 8; right 3, wrong 5, too recent 0.

## Episode by episode

### 2017 high: 16 Dec 2017, $19,650

- **New rule: silent** (no SELL within 60 days either side).
  - On the day: Hold: frothy, but liquidity is not deteriorating
- **Original rule: silent** (no SELL within 60 days either side).
  - On the day: Hold: frothy, but liquidity is not deteriorating
- Regime on the day: CALM
- Dials with no data (12 of 39): alt_value, alt_watch, sofr_iorb, funding, alt_oi, stable_30d, hy_spread, ccc_bb, bbb_spread, ai_basket, stable_turn, buybacks
- Green: btc_weekly, btc_ndx, margin_debt, cpi_mom, breakeven, liquidity, dollar, sp500, nfci, stlfsi, bizd, kre, discount_window, srf, dollar_reversal
- Red: btc_price, weekly_move, lth_sopr

### 2018 low: 15 Dec 2018, $3,183

- **New rule: BUY** as STAGED on 45 of 121 days in the window; first 27 Nov 2018 at $3,775 (-18 days from the low, +19% from it).
  - On the day: Buy (staged)
- **Original rule: BUY** on 53 of 121 days in the window; first 21 Nov 2018 at $4,545 (-24 days from the low, +43% from it).
  - On the day: Buy (in stages)
- Regime on the day: BREAK
- Dials with no data (9 of 39): alt_value, alt_watch, funding, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_price, net_loss, margin_debt, y10_chg, cpi_mom, breakeven, dollar, stable_30d, nfci, discount_window, srf, dollar_reversal, stable_turn
- Red: btc_weekly, btc_ndx, weekly_reclaim

### 2020 low: 12 Mar 2020, $4,857

- **New rule: BUY** as CONFIRMED on 14 of 121 days in the window; first 27 Mar 2020 at $6,372 (+15 days from the low, +31% from it).
  - On the day: Sell (reduce risk)
- **Original rule: silent** (no BUY within 60 days either side).
  - On the day: Sell (reduce risk)
- Regime on the day: TURN
- Dials with no data (7 of 39): alt_value, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_ndx, alt_watch, margin_debt, y2_chg, y10_chg, hike_pricing, cpi_mom, breakeven, liquidity, dollar, stable_30d, discount_window, dollar_reversal, front_end, fed_bills, stable_turn, hikes_out
- Red: btc_weekly, sp500, funding, bizd, kre, srf, weekly_reclaim

### 2021 first high: 13 Apr 2021, $63,588

- **New rule: SELL** on 72 of 121 days in the window; first 12 Feb 2021 at $47,408 (-60 days from the high, -25% from it).
  - On the day: Hold: frothy, but liquidity is not deteriorating
- **Original rule: SELL** on 72 of 121 days in the window; first 12 Feb 2021 at $47,408 (-60 days from the high, -25% from it).
  - On the day: Hold: frothy, but liquidity is not deteriorating
- Regime on the day: STRESS BUILDING (1 early turn signal: Fed buying: bank reserves)
- Dials with no data (7 of 39): alt_value, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_weekly, btc_ndx, alt_watch, sofr_iorb, liquidity, dollar, sp500, stable_30d, nfci, stlfsi, bizd, kre, discount_window, srf, dollar_reversal, fed_reserves, stable_turn
- Red: btc_price, lth_sopr, funding

### 2021 second high: 08 Nov 2021, $67,555

- **New rule: SELL** on 51 of 121 days in the window; first 08 Oct 2021 at $53,964 (-31 days from the high, -20% from it).
  - On the day: Sell (reduce risk)
- **Original rule: SELL** on 51 of 121 days in the window; first 08 Oct 2021 at $53,964 (-31 days from the high, -20% from it).
  - On the day: Sell (reduce risk)
- Regime on the day: STRESS BUILDING
- Dials with no data (7 of 39): alt_value, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_weekly, btc_ndx, alt_watch, sofr_iorb, liquidity, dollar, sp500, stable_30d, nfci, stlfsi, bizd, kre, discount_window, srf, dollar_reversal, stable_turn
- Red: btc_price, cpi_mom, breakeven, funding

### 2022 June low: 18 Jun 2022, $18,949

- **New rule: BUY** as CONFIRMED, STAGED on 56 of 121 days in the window; first 27 May 2022 at $28,598 (-22 days from the low, +51% from it).
  - On the day: Hold: cheap, but fresh stress in banks (Regional banks (KRE))
- **Original rule: BUY** on 12 of 121 days in the window; first 08 Jul 2022 at $21,582 (+20 days from the low, +14% from it).
  - On the day: Hold: cheap, but no turn signal has fired
- Regime on the day: BREAK
- Dials with no data (7 of 39): alt_value, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_price, lth_sopr, net_loss, margin_debt, sofr_iorb, hike_pricing, stlfsi, discount_window, srf
- Red: btc_weekly, btc_ndx, y2_chg, y10_chg, cpi_mom, breakeven, dollar, sp500, bizd, kre, dollar_reversal, front_end, weekly_reclaim

### 2022 November low: 21 Nov 2022, $15,760

- **New rule: BUY** as STAGED on 107 of 121 days in the window; first 22 Sep 2022 at $19,401 (-60 days from the low, +23% from it).
  - On the day: Buy (staged)
- **Original rule: BUY** on 44 of 121 days in the window; first 06 Nov 2022 at $20,909 (-15 days from the low, +33% from it).
  - On the day: Buy (in stages)
- Regime on the day: BREAK (1 early turn signal: Rate hikes being priced out)
- Dials with no data (7 of 39): alt_value, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_price, weekly_move, lth_sopr, margin_debt, sofr_iorb, y10_chg, hike_pricing, breakeven, funding, stlfsi, discount_window, srf, hikes_out
- Red: btc_weekly, btc_ndx, alt_watch, cpi_mom, liquidity, sp500, weekly_reclaim

### 2025 high: 06 Oct 2025, $124,720

- **New rule: silent** (no SELL within 60 days either side).
  - On the day: Hold: neither cheap nor frothy
- **Original rule: silent** (no SELL within 60 days either side).
  - On the day: Hold: neither cheap nor frothy
- Regime on the day: STRESS BUILDING
- Dials with no data (2 of 39): alt_value, alt_oi
- Green: btc_weekly, breakeven, dollar, sp500, stable_30d, hy_spread, ccc_bb, bbb_spread, nfci, stlfsi, ai_basket, kre, discount_window, srf, dollar_reversal, stable_turn
- Red: hike_pricing, bizd, fed_reserves, hikes_out

### 2026 first-half low: 30 Jun 2026, $58,524

- **New rule: silent** (no BUY within 60 days either side).
  - On the day: Hold: fairly cheap, but the turn is not confirmed (CAUTION: weekly close below the break level)
- **Original rule: silent** (no BUY within 60 days either side).
  - On the day: Hold: neither cheap nor frothy (CAUTION: weekly close below the break level)
- Regime on the day: BREAK
- Dials with no data (2 of 39): alt_value, alt_oi
- Green: sofr_iorb, breakeven, dollar, sp500, hy_spread, ccc_bb, bbb_spread, nfci, stlfsi, ai_basket, kre, discount_window, srf, dollar_reversal, fed_bills
- Red: btc_weekly, btc_ndx, cpi_mom, liquidity, stable_turn, weekly_reclaim

## When each dial first has data

| dial | first day with a reading |
|---|---|
| btc_price | 01 Sep 2017 |
| btc_weekly | 01 Sep 2017 |
| weekly_move | 01 Sep 2017 |
| lth_sopr | 01 Sep 2017 |
| net_loss | 01 Sep 2017 |
| btc_ndx | 01 Sep 2017 |
| alt_value | never in this replay |
| alt_watch | 28 Jul 2019 |
| margin_debt | 01 Sep 2017 |
| sofr_iorb | 10 Apr 2018 |
| y2_chg | 01 Sep 2017 |
| y10_chg | 01 Sep 2017 |
| hike_pricing | 01 Sep 2017 |
| cpi_mom | 01 Sep 2017 |
| breakeven | 01 Sep 2017 |
| liquidity | 01 Sep 2017 |
| dollar | 01 Sep 2017 |
| sp500 | 13 Sep 2017 |
| funding | 20 Feb 2020 |
| alt_oi | never in this replay |
| stable_30d | 01 Feb 2018 |
| hy_spread | 24 Feb 2024 |
| ccc_bb | 24 Feb 2024 |
| bbb_spread | 24 Feb 2024 |
| nfci | 01 Sep 2017 |
| stlfsi | 01 Sep 2017 |
| ai_basket | 01 Jul 2025 |
| bizd | 01 Sep 2017 |
| kre | 01 Dec 2017 |
| discount_window | 01 Sep 2017 |
| srf | 01 Sep 2017 |
| dollar_reversal | 01 Sep 2017 |
| front_end | 01 Sep 2017 |
| fed_bills | 01 Sep 2017 |
| fed_reserves | 01 Sep 2017 |
| stable_turn | 03 Mar 2018 |
| weekly_reclaim | 01 Sep 2017 |
| buybacks | 26 Jun 2024 |
| hikes_out | 01 Sep 2017 |
