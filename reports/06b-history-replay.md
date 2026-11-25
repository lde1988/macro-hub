# Point 6b: history replay with the owner's four changes

Date: 25 November 2026. Replay period: 1 September 2017 to 24 November 2026 (3,372 days).
This replaces nothing in `06-history-replay.md`; it re-runs the same replay after four rule changes the owner
made on principle, not to fit the first replay's numbers. Nothing was adjusted after this run either.

## What changed in the rules

1. **The sell signal cannot fire when price is at or below 1.3x realised price.** Frothy and cheap cannot both be true.
2. **SELL is renamed FROTH WARNING (reduce-risk watch).** It pushes at priority 4, not 5, and the dashboard shows its record beside it.
3. **A separate trend-exit line** (Coutts' regime filter): RISK-OFF after a weekly close below the break line; RISK-ON again on a weekly close above the reclaim line. In the replay the lines are the moving stand-ins: reclaim = short-term holder realised price, break = 0.96x it. It is its own line and does not enter buy / hold.
4. **STRESS BUILDING needs two or more families red, or any one of the buy-blocking families** (money-market funding, credit spreads, banks).

The dollar-reversal rule and the two-level buy were left alone, as instructed.

## Caveats (unchanged)

Tiny sample (five lows, four highs); some bands were chosen with hindsight; back-filled data is today's version of history; one step per day. In the replay each day's close is known only the next day, whereas live the hub uses the live price.

## 1 and 2. Froth warning

| Spell | Days | Price at start | 6 months later | 12 months later | Worst fall within 12 months | Verdict |
|---|---|---|---|---|---|---|
| 20 Feb to 12 Mar 2020 | 22 | $9,610 | +23% | +483% | -49% | wrong |
| 20 to 30 Aug 2020 | 11 | $11,864 | +335% | +316% | -15% | wrong |
| 16 Jan to 20 May 2021 | 99 | $36,007 | -12% | +20% | -17% | wrong |
| 7 to 8 Sep 2021 | 2 | $46,894 | -17% | -59% | -60% | right |
| 8 Oct to 27 Nov 2021 | 51 | $53,964 | -22% | -64% | -66% | right |
| 1 Mar to 14 Apr 2024 | 37 | $62,437 | -5% | +38% | -14% | wrong |
| 13 Nov to 28 Dec 2024 | 45 | $90,494 | +14% | +10% | -16% | wrong |
| 19 Jan to 4 Feb 2025 | 7 | $101,211 | +16% | -9% | -25% | right |

**Record: right on 3 of 8**, unchanged, so the dashboard line "right on 3 of 8 past occasions" stands.

What the 1.3x guard did: the February 2020 spell now ends on 12 March instead of 15 March (274 flagged days in all, down from 277). In the replay the warning still shows on 12 March itself, the day of the low, because the replay learns each day's close a day late: at the end of 12 March it still saw the 11 March close ($7,935, 1.38x realised price). From 13 March it reads "Hold". Live, the hub uses the live price, so the guard would have acted during the fall on the day.

## 3. Trend exit

**Rule as replayed, fixed before running:** RISK-OFF from the weekly close below 0.96x short-term holder realised price; RISK-ON from the weekly close above short-term holder realised price.

### At the cycle lows and highs

| Episode | Trend exit on the day | 60 days later |
|---|---|---|
| 2017 high, 16 Dec 2017 | RISK-ON | RISK-OFF |
| 2018 low, 15 Dec 2018 | RISK-OFF | RISK-OFF |
| 2020 low, 12 Mar 2020 | RISK-OFF (from 9 Mar) | RISK-ON |
| 2021 first high, 13 Apr 2021 | RISK-ON | RISK-OFF |
| 2021 second high, 8 Nov 2021 | RISK-ON | RISK-OFF |
| 2022 June low, 18 Jun 2022 | RISK-OFF | RISK-OFF |
| 2022 November low, 21 Nov 2022 | RISK-OFF | RISK-ON |
| 2025 high, 6 Oct 2025 | RISK-ON | RISK-OFF |
| 2026 first-half low, 30 Jun 2026 | RISK-OFF | RISK-ON |

It was RISK-OFF at all five lows and turned RISK-OFF within 60 days after all four highs, including the 2017 and 2025 highs where the froth warning was silent.

### Every RISK-OFF spell: exit price against re-entry price

| Risk-off from | Price then | Risk-on again | Price then | Days out | Re-entry vs exit | Lowest while out |
|---|---|---|---|---|---|---|
| 5 Feb 2018 | $6,905 | 5 Mar 2018 | $11,378 | 28 | +65% | $6,905 (0%) |
| 12 Mar 2018 | $9,120 | 30 Jul 2018 | $8,170 | 140 | -10% | $5,852 (-36%) |
| 6 Aug 2018 | $6,938 | 3 Sep 2018 | $7,257 | 28 | +5% | $6,146 (-11%) |
| 10 Sep 2018 | $6,300 | 1 Apr 2019 | $4,137 | 203 | -34% | $3,183 (-49%) |
| 30 Sep 2019 | $8,305 | 20 Jan 2020 | $8,629 | 112 | +4% | $6,617 (-20%) |
| 9 Mar 2020 | $7,935 | 27 Apr 2020 | $7,790 | 49 | -2% | $4,857 (-39%) |
| 24 May 2021 | $38,879 | 16 Aug 2021 | $45,902 | 84 | +18% | $29,796 (-23%) |
| 6 Dec 2021 | $50,530 | 28 Mar 2022 | $47,145 | 112 | -7% | $35,066 (-31%) |
| 11 Apr 2022 | $39,536 | 7 Nov 2022 | $20,593 | 210 | -48% | $18,463 (-53%) |
| 14 Nov 2022 | $16,591 | 16 Jan 2023 | $21,188 | 63 | +28% | $15,760 (-5%) |
| 21 Aug 2023 | $26,125 | 2 Oct 2023 | $27,504 | 42 | +5% | $25,152 (-4%) |
| 8 Jul 2024 | $56,699 | 22 Jul 2024 | $67,558 | 14 | +19% | $56,699 (0%) |
| 5 Aug 2024 | $54,029 | 26 Aug 2024 | $62,840 | 21 | +16% | $54,029 (0%) |
| 2 Sep 2024 | $59,140 | 23 Sep 2024 | $63,339 | 21 | +7% | $53,950 (-9%) |
| 10 Mar 2025 | $78,545 | 28 Apr 2025 | $95,043 | 49 | +21% | $76,252 (-3%) |
| 20 Oct 2025 | $110,568 | 27 Oct 2025 | $114,087 | 7 | +3% | $107,586 (-3%) |
| 10 Nov 2025 | $105,979 | 11 May 2026 | $81,727 | 182 | -23% | $62,791 (-41%) |
| 1 Jun 2026 | $71,314 | 24 Aug 2026 | $78,982 | 84 | +11% | $58,524 (-18%) |
| 16 Nov 2026 | $64,817 | still risk-off | $59,741 so far | 9 | -8% so far | $58,815 (-9%) |

**19 spells. Re-entry was below the exit price in 7 and above it in 12.** Risk-off on 1,458 of 3,372 days (43%).

### Judged the same way as the other signals (lower 12 months after the spell began)

Spells less than 15 days apart are joined, as for the other signals: 14 joined spells; **right 7, wrong 5, too recent 2**.

### Read plainly

- **It caught every major decline** and was out for the worst of each: 2018 (re-entered 34% lower), 2022 (48% lower), late 2025 to 2026 (23% lower).
- **It cost money more often than it saved it.** In 12 of 19 spells the price was higher at re-entry than at exit, by 3% to 28% in most cases and 65% once (February 2018, a one-month whipsaw).
- **The three big saves are larger than the many small costs**, but that is three events.
- **It is late at lows by design.** At the 2020 low it turned RISK-ON on 27 April at $7,790, 60% above the low. At the November 2022 low it turned RISK-ON on 16 January 2023 at $21,188, 34% above the low.
- It says nothing about buying; it only describes whether the weekly trend filter is broken.

## 4. STRESS BUILDING

| Regime | Share of days before | Share of days now |
|---|---|---|
| BREAK | 41.5% | 41.5% |
| STRESS BUILDING | 40.5% | **20.5%** |
| CALM | 3.6% | 21.4% |
| TURN (confirmed only) | 14.0% | 14.0% |
| FRAGILE | 0.3% | 2.6% |

Over the last two years alone: BREAK 37%, CALM 25%, TURN 25%, STRESS BUILDING 11%, FRAGILE 3%.

## Buy rules: unchanged by these four changes

| Rule | Spells | Right | Wrong | Too recent | Days flagged |
|---|---|---|---|---|---|
| New: any BUY | 4 | 2 | 1 | 1 | 335 |
| New: BUY (STAGED) alone | 2 | 2 | 0 | 0 | 262 |
| New: BUY (CONFIRMED) alone | 6 | 4 | 1 | 1 | 73 |
| Original BUY | 5 | 5 | 0 | 0 | 152 |

Episode-by-episode buy results are identical to `06-history-replay.md`.

## What could not be replayed

Unchanged from `06-history-replay.md`: credit spreads before February 2024; altcoin open interest throughout; altcoin value; funding before February 2020; buybacks before June 2024; AI canaries before July 2025; the 2015 low and 2013 high.

## Files

- `06b-replay-daily.csv`: every day's regime, readings, trend exit and every dial.
- Tool: `tools/replay_report.py` on the `claude/build` branch.

---

# Appendix: raw output of the replay tool

Replay 2017-09-01 to 2026-11-24: 3372 days.

## Days in each reading

| | new rule | original rule |
|---|---|---|
| BUY | 0 | 152 |
| BUY (CONFIRMED) | 73 | 0 |
| BUY (STAGED) | 262 | 0 |
| FROTH WARNING | 274 | 274 |
| HOLD | 2763 | 2946 |

Regime days: BREAK 1401, CALM 722, STRESS BUILDING 691, TURN 472, FRAGILE 86

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

### FROTH WARNING (same rule in both)

| spell | days flagged | price at start | 6 months later | 12 months later | worst fall within 12 months | verdict |
|---|---|---|---|---|---|---|
| 20 Feb 2020 to 12 Mar 2020 | 22 | $9,610 | +23% | +483% | -49% | wrong |
| 20 Aug 2020 to 30 Aug 2020 | 11 | $11,864 | +335% | +316% | -15% | wrong |
| 16 Jan 2021 to 20 May 2021 | 99 | $36,007 | -12% | +20% | -17% | wrong |
| 07 Sep 2021 to 08 Sep 2021 | 2 | $46,894 | -17% | -59% | -60% | right |
| 08 Oct 2021 to 27 Nov 2021 | 51 | $53,964 | -22% | -64% | -66% | right |
| 01 Mar 2024 to 14 Apr 2024 | 37 | $62,437 | -5% | +38% | -14% | wrong |
| 13 Nov 2024 to 28 Dec 2024 | 45 | $90,494 | +14% | +10% | -16% | wrong |
| 19 Jan 2025 to 04 Feb 2025 | 7 | $101,211 | +16% | -9% | -25% | right |

Spells: 8; right 3, wrong 5, too recent 0.

### Trend exit: RISK-OFF spells

| spell | days flagged | price at start | 6 months later | 12 months later | worst fall within 12 months | verdict |
|---|---|---|---|---|---|---|
| 05 Feb 2018 to 31 Mar 2019 | 399 | $6,905 | +0% | -50% | -54% | right |
| 30 Sep 2019 to 19 Jan 2020 | 112 | $8,305 | -23% | +31% | -42% | wrong |
| 09 Mar 2020 to 26 Apr 2020 | 49 | $7,935 | +31% | +592% | -39% | wrong |
| 24 May 2021 to 15 Aug 2021 | 84 | $38,879 | +45% | -24% | -26% | right |
| 06 Dec 2021 to 27 Mar 2022 | 112 | $50,530 | -38% | -66% | -69% | right |
| 11 Apr 2022 to 15 Jan 2023 | 273 | $39,536 | -52% | -24% | -60% | right |
| 21 Aug 2023 to 01 Oct 2023 | 42 | $26,125 | +98% | +126% | -4% | wrong |
| 08 Jul 2024 to 21 Jul 2024 | 14 | $56,699 | +80% | +92% | -5% | wrong |
| 05 Aug 2024 to 22 Sep 2024 | 42 | $54,029 | +88% | +111% | -0% | wrong |
| 10 Mar 2025 to 27 Apr 2025 | 49 | $78,545 | +43% | -11% | -20% | right |
| 20 Oct 2025 to 26 Oct 2025 | 7 | $110,568 | -31% | -25% | -47% | right |
| 10 Nov 2025 to 10 May 2026 | 182 | $105,979 | -23% | -30% | -45% | right |
| 01 Jun 2026 to 23 Aug 2026 | 84 | $71,314 | n/a | n/a | -18% | too recent |
| 16 Nov 2026 to 24 Nov 2026 | 9 | $64,817 | n/a | n/a | -9% | too recent |

Spells: 14; right 7, wrong 5, too recent 2.

### Trend exit: what each RISK-OFF spell did

| risk-off from | price then | risk-on again | price then | days out | re-entry vs exit | lowest price while out |
|---|---|---|---|---|---|---|
| 05 Feb 2018 | $6,905 | 05 Mar 2018 | $11,378 | 28 | +65% | $6,905 (+0%) |
| 12 Mar 2018 | $9,120 | 30 Jul 2018 | $8,170 | 140 | -10% | $5,852 (-36%) |
| 06 Aug 2018 | $6,938 | 03 Sep 2018 | $7,257 | 28 | +5% | $6,146 (-11%) |
| 10 Sep 2018 | $6,300 | 01 Apr 2019 | $4,137 | 203 | -34% | $3,183 (-49%) |
| 30 Sep 2019 | $8,305 | 20 Jan 2020 | $8,629 | 112 | +4% | $6,617 (-20%) |
| 09 Mar 2020 | $7,935 | 27 Apr 2020 | $7,790 | 49 | -2% | $4,857 (-39%) |
| 24 May 2021 | $38,879 | 16 Aug 2021 | $45,902 | 84 | +18% | $29,796 (-23%) |
| 06 Dec 2021 | $50,530 | 28 Mar 2022 | $47,145 | 112 | -7% | $35,066 (-31%) |
| 11 Apr 2022 | $39,536 | 07 Nov 2022 | $20,593 | 210 | -48% | $18,463 (-53%) |
| 14 Nov 2022 | $16,591 | 16 Jan 2023 | $21,188 | 63 | +28% | $15,760 (-5%) |
| 21 Aug 2023 | $26,125 | 02 Oct 2023 | $27,504 | 42 | +5% | $25,152 (-4%) |
| 08 Jul 2024 | $56,699 | 22 Jul 2024 | $67,558 | 14 | +19% | $56,699 (+0%) |
| 05 Aug 2024 | $54,029 | 26 Aug 2024 | $62,840 | 21 | +16% | $54,029 (+0%) |
| 02 Sep 2024 | $59,140 | 23 Sep 2024 | $63,339 | 21 | +7% | $53,950 (-9%) |
| 10 Mar 2025 | $78,545 | 28 Apr 2025 | $95,043 | 49 | +21% | $76,252 (-3%) |
| 20 Oct 2025 | $110,568 | 27 Oct 2025 | $114,087 | 7 | +3% | $107,586 (-3%) |
| 10 Nov 2025 | $105,979 | 11 May 2026 | $81,727 | 182 | -23% | $62,791 (-41%) |
| 01 Jun 2026 | $71,314 | 24 Aug 2026 | $78,982 | 84 | +11% | $58,524 (-18%) |
| 16 Nov 2026 | $64,817 | still risk-off | $59,741 | 9 | -8% | $58,815 (-9%) |

RISK-OFF spells: 19; re-entry below the exit price in 7, above it in 12. Days risk-off: 1458 of 3372 (43%).

## Episode by episode

### 2017 high: 16 Dec 2017, $19,650

- **New rule: silent** (no FROTH WARNING within 60 days either side).
  - On the day: Hold: frothy, but liquidity is not deteriorating
- **Original rule: silent** (no FROTH WARNING within 60 days either side).
  - On the day: Hold: frothy, but liquidity is not deteriorating
- **Trend exit** on the day: RISK-ON; 60 days later: RISK-OFF
- Regime on the day: CALM
- Dials with no data (12 of 39): alt_value, alt_watch, sofr_iorb, funding, alt_oi, stable_30d, hy_spread, ccc_bb, bbb_spread, ai_basket, stable_turn, buybacks
- Green: btc_weekly, btc_ndx, margin_debt, cpi_mom, breakeven, liquidity, dollar, sp500, nfci, stlfsi, bizd, kre, discount_window, srf, dollar_reversal
- Red: btc_price, weekly_move, lth_sopr

### 2018 low: 15 Dec 2018, $3,183

- **New rule: BUY** as STAGED on 45 of 121 days in the window; first 27 Nov 2018 at $3,775 (-18 days from the low, +19% from it).
  - On the day: Buy (staged)
- **Original rule: BUY** on 53 of 121 days in the window; first 21 Nov 2018 at $4,545 (-24 days from the low, +43% from it).
  - On the day: Buy (in stages)
- **Trend exit** on the day: RISK-OFF; 60 days later: RISK-OFF
- Regime on the day: BREAK
- Dials with no data (9 of 39): alt_value, alt_watch, funding, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_price, net_loss, margin_debt, y10_chg, cpi_mom, breakeven, dollar, stable_30d, nfci, discount_window, srf, dollar_reversal, stable_turn
- Red: btc_weekly, btc_ndx, weekly_reclaim

### 2020 low: 12 Mar 2020, $4,857

- **New rule: BUY** as CONFIRMED on 14 of 121 days in the window; first 27 Mar 2020 at $6,372 (+15 days from the low, +31% from it).
  - On the day: Froth warning (reduce-risk watch)
- **Original rule: silent** (no BUY within 60 days either side).
  - On the day: Froth warning (reduce-risk watch)
- **Trend exit** on the day: RISK-OFF; 60 days later: RISK-ON
- Regime on the day: TURN
- Dials with no data (7 of 39): alt_value, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_ndx, alt_watch, margin_debt, y2_chg, y10_chg, hike_pricing, cpi_mom, breakeven, liquidity, dollar, stable_30d, discount_window, dollar_reversal, front_end, fed_bills, stable_turn, hikes_out
- Red: btc_weekly, sp500, funding, bizd, kre, srf, weekly_reclaim

### 2021 first high: 13 Apr 2021, $63,588

- **New rule: FROTH WARNING** on 72 of 121 days in the window; first 12 Feb 2021 at $47,408 (-60 days from the high, -25% from it).
  - On the day: Hold: frothy, but liquidity is not deteriorating
- **Original rule: FROTH WARNING** on 72 of 121 days in the window; first 12 Feb 2021 at $47,408 (-60 days from the high, -25% from it).
  - On the day: Hold: frothy, but liquidity is not deteriorating
- **Trend exit** on the day: RISK-ON; 60 days later: RISK-OFF
- Regime on the day: CALM (1 early turn signal: Fed buying: bank reserves)
- Dials with no data (7 of 39): alt_value, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_weekly, btc_ndx, alt_watch, sofr_iorb, liquidity, dollar, sp500, stable_30d, nfci, stlfsi, bizd, kre, discount_window, srf, dollar_reversal, fed_reserves, stable_turn
- Red: btc_price, lth_sopr, funding

### 2021 second high: 08 Nov 2021, $67,555

- **New rule: FROTH WARNING** on 51 of 121 days in the window; first 08 Oct 2021 at $53,964 (-31 days from the high, -20% from it).
  - On the day: Froth warning (reduce-risk watch)
- **Original rule: FROTH WARNING** on 51 of 121 days in the window; first 08 Oct 2021 at $53,964 (-31 days from the high, -20% from it).
  - On the day: Froth warning (reduce-risk watch)
- **Trend exit** on the day: RISK-ON; 60 days later: RISK-OFF
- Regime on the day: STRESS BUILDING
- Dials with no data (7 of 39): alt_value, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_weekly, btc_ndx, alt_watch, sofr_iorb, liquidity, dollar, sp500, stable_30d, nfci, stlfsi, bizd, kre, discount_window, srf, dollar_reversal, stable_turn
- Red: btc_price, cpi_mom, breakeven, funding

### 2022 June low: 18 Jun 2022, $18,949

- **New rule: BUY** as CONFIRMED, STAGED on 56 of 121 days in the window; first 27 May 2022 at $28,598 (-22 days from the low, +51% from it).
  - On the day: Hold: cheap, but fresh stress in banks (Regional banks (KRE))
- **Original rule: BUY** on 12 of 121 days in the window; first 08 Jul 2022 at $21,582 (+20 days from the low, +14% from it).
  - On the day: Hold: cheap, but no turn signal has fired
- **Trend exit** on the day: RISK-OFF; 60 days later: RISK-OFF
- Regime on the day: BREAK
- Dials with no data (7 of 39): alt_value, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_price, lth_sopr, net_loss, margin_debt, sofr_iorb, hike_pricing, stlfsi, discount_window, srf
- Red: btc_weekly, btc_ndx, y2_chg, y10_chg, cpi_mom, breakeven, dollar, sp500, bizd, kre, dollar_reversal, front_end, weekly_reclaim

### 2022 November low: 21 Nov 2022, $15,760

- **New rule: BUY** as STAGED on 107 of 121 days in the window; first 22 Sep 2022 at $19,401 (-60 days from the low, +23% from it).
  - On the day: Buy (staged)
- **Original rule: BUY** on 44 of 121 days in the window; first 06 Nov 2022 at $20,909 (-15 days from the low, +33% from it).
  - On the day: Buy (in stages)
- **Trend exit** on the day: RISK-OFF; 60 days later: RISK-ON
- Regime on the day: BREAK (1 early turn signal: Rate hikes being priced out)
- Dials with no data (7 of 39): alt_value, alt_oi, hy_spread, ccc_bb, bbb_spread, ai_basket, buybacks
- Green: btc_price, weekly_move, lth_sopr, margin_debt, sofr_iorb, y10_chg, hike_pricing, breakeven, funding, stlfsi, discount_window, srf, hikes_out
- Red: btc_weekly, btc_ndx, alt_watch, cpi_mom, liquidity, sp500, weekly_reclaim

### 2025 high: 06 Oct 2025, $124,720

- **New rule: silent** (no FROTH WARNING within 60 days either side).
  - On the day: Hold: neither cheap nor frothy
- **Original rule: silent** (no FROTH WARNING within 60 days either side).
  - On the day: Hold: neither cheap nor frothy
- **Trend exit** on the day: RISK-ON; 60 days later: RISK-OFF
- Regime on the day: STRESS BUILDING
- Dials with no data (2 of 39): alt_value, alt_oi
- Green: btc_weekly, breakeven, dollar, sp500, stable_30d, hy_spread, ccc_bb, bbb_spread, nfci, stlfsi, ai_basket, kre, discount_window, srf, dollar_reversal, stable_turn
- Red: hike_pricing, bizd, fed_reserves, hikes_out

### 2026 first-half low: 30 Jun 2026, $58,524

- **New rule: silent** (no BUY within 60 days either side).
  - On the day: Hold: fairly cheap, but the turn is not confirmed (CAUTION: weekly close below the break level)
- **Original rule: silent** (no BUY within 60 days either side).
  - On the day: Hold: neither cheap nor frothy (CAUTION: weekly close below the break level)
- **Trend exit** on the day: RISK-OFF; 60 days later: RISK-ON
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
