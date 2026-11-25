# Point 2: source check

Date: 25 November 2026. Every row was fetched live on a GitHub Actions runner (US address).
First run 08:40 UTC; re-run with the Coinalyze key 08:52 UTC. The raw table from the runner is at the end.

## Result in brief

- **Works from a runner:** FRED (all 35 series, with the owner's key), Coinbase, Bitview, Coin Metrics, BGeometrics (7 days late), DefiLlama, ECB, FINRA, US Treasury fiscal data, Nasdaq's quote service, CoinGecko, Coinalyze, ntfy.
- **Does not work:** Stooq (refuses the runner; dropped). Binance (HTTP 451, blocked for US addresses, as expected).
- **No longer free:** Coin Metrics realised cap. Replaced by price ÷ MVRV, which gives the same realised price.
- **Stopped on FRED:** money supply for the euro area (2023), Japan (2017) and China (2019); no People's Bank of China balance sheet.

## Cross-checks against the owner's figures

| Check | Owner's figure | Live figure | Verdict |
|---|---|---|---|
| Realised price | $53,000 | $53,097 (Bitview), $53,099 (Coin Metrics); gap 0.01% | Match |
| Long-term holder cost | $48,000 | $48,302 | Match |
| Short-term holder cost | about $75,000 | $72,410 | Close; live value used |
| Margin debt, 3-month annualised | +129% Jun, -5.7% Sep | +129.1% Jun, -5.7% Sep; **October +9.1%** | Match; note the October bounce |
| Stablecoin supply | about $287bn, -5.4% mid Nov | $287.1bn on 15 Nov; now $282.5bn, -5.9% | Match |
| LTH-SOPR | about 1.0 mid Nov | 30-day version 0.90 to 0.99 over 10–20 Nov; now 0.88. 7-day 0.72 | Match on the 30-day version |
| Realised losses "a tenth of February" | 0.1 | Gross 30-day losses: 0.43 on 15 Nov. **Net** 30-day losses: 0.12 | Match on net losses only |
| Dollar index within 0.3 of a published quote | 0.3 | Mean gap 0.15; within 0.3 on 57 of 63 days; worst 0.63 | **Fails on 6 of 63 days** (ECB fixing is hours before the New York close) |
| Alt ÷ BTC open interest 1.66x on 27 Sep 2026 | 1.66x, 98th percentile | Pending: history pull in progress | Open |
| WSHOBL, WRESBAL units | to confirm | Both in millions of dollars | Confirmed |

## Owner's decisions on this report (25 Nov)

1. LTH-SOPR: 30-day version is the main dial; 7-day shown beside it as early warning.
2. Realised losses: the definition matching Coutts is **net** realised loss (profits minus losses) over 30 days; see the table above.
3. Dollar index: ECB-computed value stays the main source; a dial changes only after two fixings in a row at least 0.3 beyond a level; the published close is shown as a check only.
4. Altcoin value: CoinGecko altcoin total minus stablecoin supply. Today: $0.586tn, 0.49x Bitcoin's value.
5. BIZD: fall from its 3-month high (today -9.6%), not a long comparison with the S&P 500, because the price ignores dividends.
6. Buybacks: split by operation type (table below).
7. Every stop-point report is saved in this folder.

## Buybacks by operation type, 2026 ($bn par accepted)

| Month | Cash management | Liquidity support |
|---|---|---|
| Jan | 0.0 | 9.7 |
| Feb | 0.0 | 12.3 |
| Mar | 29.7 | 6.9 |
| Apr | 45.0 | 6.4 |
| May | 0.0 | 8.8 |
| Jun | 24.6 | 7.3 |
| Jul | 0.0 | 10.7 |
| Aug | 0.0 | 11.1 |
| Sep | 25.0 | 12.8 |
| Oct | 0.0 | 26.1 |
| Nov (to the 19th) | 0.0 | 12.0 |

A few older operations have no type or no accepted amount recorded; they will be kept out of both columns and counted in a note.

## Coinalyze findings

- Funding history is daily and goes back to 2020 (Binance, Bybit, OKX). The Binance 30-day average is 0.0061% per 8 hours, about +6.7% a year. Days negative in the last 30: 2 (Binance), 3 (Bybit), 7 (OKX).
- Bitcoin perpetual open interest across all exchanges: $19.8bn.
- **Open-interest history is limited to about 1,500 days (from 16 October 2022)**, so "percentile since 2022" means since October 2022. The hub will keep its own copy so the window grows instead of rolling.
- **Rate limit: 40 markets a minute**, and there are 5,700 perpetual markets. A full pull takes about 2.5 hours. A one-off pull is running; from its result I will pick the smallest set of markets that covers nearly all altcoin open interest, so the regular update takes minutes.
- Two venues (tradeXYZ, Polymarket) list equity and prediction contracts, not altcoins, and are excluded.

## Limits to carry into later points

- Credit spreads on FRED start 27 November 2023: the 2018, 2020 and 2022 replays will run without the credit dials.
- S&P 500 on FRED starts November 2016 and is posted a day late.
- Bitcoin dominance and altcoin value have no free history.
- Nasdaq's quote service is unofficial and gives 10 years of prices, not adjusted for dividends.
- Bitview is at version 0.x and counts "long-term" as 150 days (some other providers use 155).
- The liquidity proxy will be Fed + ECB + Bank of Japan assets in dollars plus US M2.

## Would need paid data

- Coutts' own liquidity index.
- The official ICE dollar index.
- Fed funds futures (true rate-hike pricing).
- History of Bitcoin dominance and total altcoin value.
- China's central bank balance sheet; money supply outside the US.
- BGeometrics' latest 7 days (about $8 a month; republishing needs a separate licence). Not needed: Bitview covers it.

## Raw table from the runner (re-run, 08:52 UTC)

Source check run 2026-11-25T08:52:37Z on GitHub Actions 1000000007

| id | source | works here? | latest value | value date | age | history from | note |
|---|---|---|---|---|---|---|---|
| SP500 | FRED | yes | 7237.17 (Index) | 2026-11-23 | 2d | 2016-11-25 | S&P 500 / D / updated 2026-11-24 |
| NASDAQ100 | FRED | yes | 26214.17 (Index) | 2026-11-24 | 1d | 1986-01-02 | NASDAQ-100 / D / updated 2026-11-24 |
| SOFR | FRED | yes | 3.92 (%) | 2026-11-23 | 2d | 2018-04-03 | Secured Overnight Financing Rate / D / updated 2026-11-24 |
| IORB | FRED | yes | 3.9 (%) | 2026-11-25 | 0d | 2021-07-29 | Interest Rate on Reserve Balances (IORB Rate) / D / updated 2026-11-24 |
| DGS2 | FRED | yes | 4.63 (%) | 2026-11-23 | 2d | 1976-06-01 | Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity, Quoted on an Investment Basis / D / updated 2026-11-24 |
| DGS10 | FRED | yes | 4.92 (%) | 2026-11-23 | 2d | 1962-01-02 | Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis / D / updated 2026-11-24 |
| T10Y2Y | FRED | yes | 0.28 (%) | 2026-11-24 | 1d | 1976-06-01 | 10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity / D / updated 2026-11-24 |
| DFF | FRED | yes | 3.88 (%) | 2026-11-23 | 2d | 1954-07-01 | Federal Funds Effective Rate / D / updated 2026-11-24 |
| EFFR | FRED | yes | 3.88 (%) | 2026-11-23 | 2d | 2000-07-03 | Effective Federal Funds Rate / D / updated 2026-11-24 |
| DFEDTARU | FRED | yes | 4 (%) | 2026-11-24 | 1d | 2008-12-16 | Federal Funds Target Range - Upper Limit / D / updated 2026-11-24 |
| DFEDTARL | FRED | yes | 3.75 (%) | 2026-11-24 | 1d | 2008-12-16 | Federal Funds Target Range - Lower Limit / D / updated 2026-11-24 |
| CPIAUCSL | FRED | yes | 337.476 (Index 1982-1984=100) | 2026-10-01 | 55d | 1947-01-01 | Consumer Price Index for All Urban Consumers: All Items in U.S. City Average / M / updated 2026-11-10 |
| T5YIE | FRED | yes | 2.11 (%) | 2026-11-24 | 1d | 2003-01-02 | 5-Year Breakeven Inflation Rate / D / updated 2026-11-24 |
| WALCL | FRED | yes | 6741452 (Mil. of U.S. $) | 2026-11-18 | 7d | 2002-12-18 | Assets: Total Assets: Total Assets (Less Eliminations from Consolidation): Wednesday Level / W / updated 2026-11-19 |
| ECBASSETSW | FRED | yes | 5923063 (Mil. of Euros) | 2026-11-20 | 5d | 1999-01-01 | Central Bank Assets for Euro Area (11-19 Countries) / W / updated 2026-11-24 |
| JPNASSETS | FRED | yes | 6261882 (100 Mil. Yen) | 2026-10-01 | 55d | 1998-04-01 | Bank of Japan: Total Assets for Japan / M / updated 2026-11-04 |
| M2SL | FRED | yes | 23532.8 (Bil. of $) | 2026-10-01 | 55d | 1959-01-01 | M2 / M / updated 2026-11-24 |
| DEXUSEU | FRED | yes | 1.0981 (U.S. $ to  1 Euro) | 2026-11-20 | 5d | 1999-01-04 | U.S. Dollars to Euro Spot Exchange Rate / D / updated 2026-11-23 |
| DEXJPUS | FRED | yes | 158.76 (Japanese Yen to  1 U.S. $) | 2026-11-20 | 5d | 1971-01-04 | Japanese Yen to U.S. Dollar Spot Exchange Rate / D / updated 2026-11-23 |
| DEXUSUK | FRED | yes | 1.3104 (U.S. $ to  1 U.K. Pound Sterling) | 2026-11-20 | 5d | 1971-01-04 | U.S. Dollars to U.K. Pound Sterling Spot Exchange Rate / D / updated 2026-11-23 |
| DEXCAUS | FRED | yes | 1.4323 (Canadian $ to  1 U.S. $) | 2026-11-20 | 5d | 1971-01-04 | Canadian Dollars to U.S. Dollar Spot Exchange Rate / D / updated 2026-11-23 |
| DEXSDUS | FRED | yes | 10.2114 (Swedish Kronor to  1 U.S. $) | 2026-11-20 | 5d | 1971-01-04 | Swedish Kronor to U.S. Dollar Spot Exchange Rate / D / updated 2026-11-23 |
| DEXSZUS | FRED | yes | 0.8394 (Swiss Francs to  1 U.S. $) | 2026-11-20 | 5d | 1971-01-04 | Swiss Francs to U.S. Dollar Spot Exchange Rate / D / updated 2026-11-23 |
| DEXCHUS | FRED | yes | 6.677 (Chinese Yuan Renminbi to  1 U.S. $) | 2026-11-20 | 5d | 1981-01-02 | Chinese Yuan Renminbi to U.S. Dollar Spot Exchange Rate / D / updated 2026-11-23 |
| DTWEXBGS | FRED | yes | 123.5978 (Index Jan 2006=100) | 2026-11-20 | 5d | 2006-01-02 | Nominal Broad U.S. Dollar Index / D / updated 2026-11-23 |
| BAMLH0A0HYM2 | FRED | yes | 3.63 (%) | 2026-11-23 | 2d | 2023-11-27 | ICE BofA US High Yield Index Option-Adjusted Spread / D / updated 2026-11-24 |
| BAMLH0A3HYC | FRED | yes | 13.87 (%) | 2026-11-23 | 2d | 2023-11-27 | ICE BofA CCC & Lower US High Yield Index Option-Adjusted Spread / D / updated 2026-11-24 |
| BAMLH0A1HYBB | FRED | yes | 2.19 (%) | 2026-11-23 | 2d | 2023-11-27 | ICE BofA BB US High Yield Index Option-Adjusted Spread / D / updated 2026-11-24 |
| BAMLC0A4CBBB | FRED | yes | 1.2 (%) | 2026-11-23 | 2d | 2023-11-27 | ICE BofA BBB US Corporate Index Option-Adjusted Spread / D / updated 2026-11-24 |
| NFCI | FRED | yes | -0.478 (Index) | 2026-11-13 | 12d | 1971-01-08 | Chicago Fed National Financial Conditions Index / W / updated 2026-11-18 |
| STLFSI4 | FRED | yes | -0.8655 (Index) | 2026-11-13 | 12d | 1993-12-31 | St. Louis Fed Financial Stress Index / W / updated 2026-11-18 |
| WLCFLPCL | FRED | yes | 9055 (Mil. of U.S. $) | 2026-11-18 | 7d | 2002-12-18 | Assets: Liquidity and Credit Facilities: Loans: Primary Credit: Wednesday Level / W / updated 2026-11-19 |
| RPONTSYD | FRED | yes | 0.002 (Bil. of US $) | 2026-11-24 | 1d | 2000-01-03 | Overnight Repurchase Agreements: Treasury Securities Purchased by the Federal Reserve in the Temporary Open Market Operations / D / updated 2026-11-24 |
| WSHOBL | FRED | yes | 580660 (Mil. of U.S. $) | 2026-11-18 | 7d | 2002-12-18 | Assets: Securities Held Outright: U.S. Treasury Securities: Bills: Wednesday Level / W / updated 2026-11-19 |
| WRESBAL | FRED | yes | 2979656 (Mil. of U.S. $) | 2026-11-18 | 7d | 1984-01-04 | Liabilities and Capital: Other Factors Draining Reserve Balances: Reserve Balances with Federal Reserve Banks: Week Average / W / updated 2026-11-19 |
| BTC-USD daily candles | Coinbase | yes | close 59,741 | 2026-11-24 | 1d |  | 350 candles per request; history pages back to 2015 |
| BTC weekly close (Sunday candle) | Coinbase | yes | 61,163 | 2026-11-22 | 3d |  | close of the daily candle that ends Sunday 24:00 UTC |
| SOL-USD | Coinbase | yes | 67.94 | 2026-11-25 | 0d |  | priced in BTC by dividing by BTC-USD |
| SUI-USD | Coinbase | yes | 0.6431 | 2026-11-25 | 0d |  | priced in BTC by dividing by BTC-USD |
| NEAR-USD | Coinbase | yes | 2.8738 | 2026-11-25 | 0d |  | priced in BTC by dividing by BTC-USD |
| LINK-USD | Coinbase | yes | 8.736 | 2026-11-25 | 0d |  | priced in BTC by dividing by BTC-USD |
| TAO-USD | Coinbase | yes | 176.26 | 2026-11-25 | 0d |  | priced in BTC by dividing by BTC-USD |
| realized_price | Bitview | yes | 53,096.6 | 2026-11-24 | 1d |  | today so far 5.309e+04; 6538 daily rows (from 2009) |
| lth_realized_price | Bitview | yes | 48,302.1 | 2026-11-24 | 1d |  | today so far 4.83e+04; 6538 daily rows (from 2009) |
| sth_realized_price | Bitview | yes | 72,410.3 | 2026-11-24 | 1d |  | today so far 7.237e+04; 6538 daily rows (from 2009) |
| lth_sopr_24h | Bitview | yes | 0.717504 | 2026-11-24 | 1d |  | today so far 0.7192; 10-20 Nov 2026 range 0.645-1.154; 6538 daily rows (from 2009) |
| lth_sopr_1w | Bitview | yes | 0.717346 | 2026-11-24 | 1d |  | today so far 0.7168; 10-20 Nov 2026 range 0.763-0.963; 6538 daily rows (from 2009) |
| lth_sopr_1m | Bitview | yes | 0.8753 | 2026-11-24 | 1d |  | today so far 0.8744; 10-20 Nov 2026 range 0.901-0.990; 6538 daily rows (from 2009) |
| realized_loss_sum_1m | Bitview | yes | 2.8722e+10 | 2026-11-24 | 1d |  | today so far 2.869e+10; Feb 2026 peak 4.062e+10 on 2026-02-20; share of that peak on 15 Nov 0.43, now 0.71; 6538 daily rows (from 2009) |
| lth_realized_loss_sum_1m | Bitview | yes | 1.05621e+10 | 2026-11-24 | 1d |  | today so far 1.059e+10; Feb 2026 peak 7.939e+09 on 2026-02-27; share of that peak on 15 Nov 0.88, now 1.33; 6538 daily rows (from 2009) |
| net_realized_pnl_sum_1m | Bitview | yes | -1.94642e+10 | 2026-11-24 | 1d |  | today so far -1.968e+10; Feb 2026 peak -3.004e+10 on 2026-02-20; share of that peak on 15 Nov 0.12, now 0.65; 6538 daily rows (from 2009) |
| sth_net_realized_pnl_sum_1m | Bitview | yes | -1.34882e+10 | 2026-11-24 | 1d |  | today so far -1.366e+10; Feb 2026 peak -2.865e+10 on 2026-02-18; share of that peak on 15 Nov 0.08, now 0.47; 6538 daily rows (from 2009) |
| realized_loss_sum_1w | Bitview | yes | 1.07e+10 | 2026-11-24 | 1d |  | today so far 1.054e+10; Feb 2026 peak 1.794e+10 on 2026-02-07; share of that peak on 15 Nov 0.40, now 0.60; 6538 daily rows (from 2009) |
| BTC realised price = PriceUSD / CapMVRVCur | Coin Metrics community | yes | 53,099 | 2026-11-24 | 1d | 2010 | price 59,791, MVRV 1.126 |
| lth-sopr | BGeometrics (free) | yes | 0.7195 | 2026-11-18 | 7d |  | free plan withholds the latest 7 days |
| stablecoin supply, USD-pegged | DefiLlama | yes | $282.5bn; 30d -5.9% | 2026-11-25 | 0d | 2017-11-29 | all pegs $284.2bn; 30d -5.9%; mid-Nov (15th) USD-pegged $287.1bn |
| ECB euro reference rates (USD JPY GBP CAD SEK CHF) | ECB | yes | computed DXY 103.88 | 2026-11-24 | 1d | 1999 | set about 14:15 Frankfurt time each business day, published about 16:00 |
| DXY published close (verification only) | Yahoo chart | yes | 104.01 | 2026-11-25 | 0d |  | worst gap vs computed over 63 days: 0.63 |
| DXY future dx.f (verification only) | Stooq | NO |  |  |  |  | KeyError: 'Date' |
| margin debt (debit balances, $m) | FINRA xlsx | yes | 1,448,360; 3m annualised +9.1% | 2026-10-01 | 55d | 1997-01-01 | 3m annualised, last 6 months: {'May 2026': '+62.8%', 'Jun 2026': '+129.1%', 'Jul 2026': '+39.4%', 'Aug 2026': '+11.3%', 'Sep 2026': '-5.7%', 'Oct 2026': '+9.1%'} |
| buyback operations (par accepted) | Treasury fiscal data | yes | $0.25bn latest op | 2026-11-19 | 6d | 2000-03-09 | monthly $bn: 2026-04 51.4, 2026-05 8.8, 2026-06 31.9, 2026-07 10.7, 2026-08 11.1, 2026-09 37.8, 2026-10 26.1, 2026-11 12.0 / types: ['Cash Management', 'Liquidity Support', 'Small Value', 'null'] |
| CRWV | Nasdaq quote service (unofficial) | yes | $42.605 | 2026-11-24 | 1d | 2025-03-28 | not dividend-adjusted; fall from 3-month high -57.3%; from 1-year high -69.1% |
| ORCL | Nasdaq quote service (unofficial) | yes | $109.50 | 2026-11-24 | 1d | 2016-11-25 | not dividend-adjusted; fall from 3-month high -32.6%; from 1-year high -55.9% |
| BIZD | Nasdaq quote service (unofficial) | yes | 12.21 | 2026-11-24 | 1d | 2016-11-25 | not dividend-adjusted; fall from 3-month high -9.6%; from 1-year high -18.9% |
| KRE | Nasdaq quote service (unofficial) | yes | 69.76 | 2026-11-24 | 1d | 2016-11-25 | not dividend-adjusted; fall from 3-month high -7.3%; from 1-year high -10.5% |
| NDX | Nasdaq quote service (unofficial) | yes | 26,746.10 | 2026-11-23 | 2d | 2015-01-01 | not dividend-adjusted; fall from 3-month high -14.3%; from 1-year high -14.3% |
| NBIS | Nasdaq quote service (unofficial) | yes | $87.31 | 2026-11-24 | 1d | 2016-11-25 | not dividend-adjusted; fall from 3-month high -65.1%; from 1-year high -69.5% |
| APLD | Nasdaq quote service (unofficial) | yes | $12.22 | 2026-11-24 | 1d | 2021-06-16 | not dividend-adjusted; fall from 3-month high -57.2%; from 1-year high -75.4% |
| IREN | Nasdaq quote service (unofficial) | yes | $12.95 | 2026-11-24 | 1d | 2021-11-17 | not dividend-adjusted; fall from 3-month high -73.3%; from 1-year high -80.9% |
| kre.us | Stooq | NO |  |  |  |  | KeyError: 'Close' |
| crwv.us | Stooq | NO |  |  |  |  | KeyError: 'Close' |
| BTC dominance / total crypto value | CoinGecko (no key) | yes | dominance 57.8%; total $2.06tn; alts excluding stablecoins $0.586tn = 0.49x Bitcoin's value | 2026-11-25 | 0d |  | current value only; no free history. Stablecoin supply (DefiLlama, all pegs) subtracted |
| BTC perpetual open interest, all exchanges | Coinalyze | yes | $19.8bn | 2026-11-25 | 0d |  | largest: BTCUSDT_PERP.A 5.8, BTCUSDT.6 4.1, BTC.H 2.1, BTCUSDT_PERP.3 1.9, BTCUSDC_PERP.A 1.5, BTCUSD_PERP.A 0.9, BTC-PERPETUAL.2 0.8, BTCUSD_PERP.3 0.7, BTCUSDT_PERP.F 0.5, BTCUSD.6 0.5, BTCUSDT_PERP.4 0.5, BTC_USDC-PERPETUAL.2 0.1 |
| funding-rate-history BTCUSDT_PERP.A | Coinalyze | yes | last 0.0072% per interval; 30d mean 0.0061% | 2026-11-25 | 0d | 2020-01-21 | 2501 daily rows; days negative in last 30: 2; last 5: [0.0009, -0.001, 0.0042, 0.0022, 0.0072]; record {"t": 1795564800, "o": 0.002227, "h": 0.007286, "l": 0.002227, "c": 0.007217} |
| funding-rate-history BTCUSDT.6 | Coinalyze | yes | last 0.0003% per interval; 30d mean 0.0055% | 2026-11-25 | 0d | 2020-04-04 | 2427 daily rows; days negative in last 30: 3; last 5: [-0.0011, -0.0004, 0.0019, 0.0034, 0.0003]; record {"t": 1795564800, "o": 0.003905, "h": 0.003905, "l": 0.000255, "c": 0.000255} |
| funding-rate-history BTCUSDT_PERP.3 | Coinalyze | yes | last 0.0042% per interval; 30d mean 0.0048% | 2026-11-25 | 0d | 2020-03-28 | 2434 daily rows; days negative in last 30: 7; last 5: [-0.0038, 0.0015, 0.0054, 0.0056, 0.0042]; record {"t": 1795564800, "o": 0.00550189519743, "h": 0.006953095496, "l": 0.00312879542107, "c": 0.004206961367910001} |
| funding-rate-history BTC.H | Coinalyze | yes | last -0.0002% per interval; 30d mean 0.0008% | 2026-11-25 | 0d | 2024-10-10 | 777 daily rows; days negative in last 30: 5; last 5: [-0.0012, 0.0008, 0.0013, -0.0005, -0.0002]; record {"t": 1795564800, "o": -0.00046768, "h": -0.00015753, "l": -0.00128821, "c": -0.00022485} |
| open-interest-history BTCUSDT_PERP.A | Coinalyze | yes | $5.82bn | 2026-11-25 | 0d | 2022-10-16 | 1502 daily rows |
| open-interest-history ETHUSDT_PERP.A | Coinalyze | yes | $3.95bn | 2026-11-25 | 0d | 2022-10-16 | 1502 daily rows |
| open-interest-history SOLUSDT_PERP.A | Coinalyze | yes | $0.54bn | 2026-11-25 | 0d | 2022-10-16 | 1502 daily rows |
| ntfy health (no push sent) | ntfy.sh | yes | {"healthy":true,"role":"active"} |  |  |  |  |
| Binance futures (expected blocked) | Binance | NO | HTTP 451 |  |  |  | {
  "code": 0,
  "msg": "Service unavailable from a restricted location according to 'b. Eligibility' in https://www.bin |

Notes:
- FRED search 'People's Bank of China total assets': 
- FRED search 'China M2': MYAGM2CNM189N "M2 for China" M National Currency to 2019-08-01 || CHNPRCNTO01MLQ "Production: Construction: Total for China" Q Square metres, Month to 2018-07-01 || CHNPRCNTO01MLM "Production: Construction: Total for China" M Square metres, Month to 2023-11-01 || MABMM201CNM189S "M2 for China (DISCONTINUED)" M National Currency to 2013-12-01 || MABMM201CNM189N "M2 for China (DISCONTINUED)" M National Currency to 2013-12-01 || DDDI05CNA156NWDB "Liquid Liabilities to GDP for China" A % to 2020-01-01
- FRED search 'euro area M3': MABMM301EZM189S "Monetary Aggregates and Their Components: Broad Money and Co" M Euro to 2023-11-01 || MABMM301EZA657S "Monetary Aggregates and Their Components: Broad Money and Co" A Growth rate previous to 2025-01-01 || MYAGM3EZM196N "M3 for Euro Area" M Euros to 2017-03-01 || MABMM301EZM657S "Monetary Aggregates and Their Components: Broad Money and Co" M Growth rate previous to 2025-12-01 || EA19MABMM301GYSAM "Monetary Aggregates and Their Components: Broad Money and Co" M Growth rate same per to 2025-12-01 || MABMM301EZM189N "Monetary Aggregates and Their Components: Broad Money and Co" M Euro to 2023-11-01
- FRED search 'Japan M2': MYAGM2JPM189S "M2 for Japan" M National Currency to 2017-02-01 || MYAGM2JPM189N "M2 for Japan" M National Currency to 2017-02-01 || MABMM201JPM189S "M2 for Japan (DISCONTINUED)" M National Currency to 2013-12-01 || MABMM201JPA189N "M2 for Japan (DISCONTINUED)" A National Currency to 2013-01-01 || MABMM201JPQ189S "M2 for Japan (DISCONTINUED)" Q National Currency to 2013-10-01 || MABMM201JPM189N "M2 for Japan (DISCONTINUED)" M National Currency to 2013-12-01
- FRED search 'standing repo facility': 
- FRED search 'discount window primary credit': DPCREDIT "Discount Window Primary Credit Rate" D % to 2026-11-23 || BORROW "Total Borrowings from the Federal Reserve" M Mil. of $ to 2026-10-01 || MPCREDIT "Discount Window Primary Credit Rate" M % to 2026-10-01 || RIFSRPF02ND "Discount Window Primary Credit Rate" D % to 2026-11-23 || WPCREDIT "Discount Window Primary Credit Rate" W % to 2026-11-18 || RIFSRPF02NA "Discount Window Primary Credit Rate" A % to 2025-01-01
- FRED search 'margin debt': AMTCCDEBT0101 "Bankrate Consumer Survey Poll: Do You Have More Credit Card " A % to 2025-01-01 || UNEXPECTEDBR0103 "Bankrate Consumer Survey Poll: How Would You Pay for a $1,00" A % to 2024-01-01 || UNEXPECTEDBR0104 "Bankrate Consumer Survey Poll: How Would You Pay for a $1,00" A % to 2024-01-01 || AMTCCDEBT0102 "Bankrate Consumer Survey Poll: Do You Have More Credit Card " A % to 2025-01-01 || FINANCIALPRIO0101 "Bankrate Consumer Survey Poll: What is Your Biggest Financia" A % to 2025-01-01 || UNEXPECTEDBR0105 "Bankrate Consumer Survey Poll: How Would You Pay for a $1,00" A % to 2024-01-01
- FRED search 'ICE BofA CCC option-adjusted spread': BAMLH0A3HYC "ICE BofA CCC & Lower US High Yield Index Option-Adjusted Spr" D % to 2026-11-23
- Bitview version: "389ae58"
- Coin Metrics CapRealUSD (realised cap) on the free tier: HTTP 403
- ECB full history file: HTTP 200, ? bytes
- Computed DXY, last 8 fixings: 2026-11-13 103.24, 2026-11-16 103.47, 2026-11-17 103.61, 2026-11-18 103.80, 2026-11-19 103.72, 2026-11-20 103.65, 2026-11-23 104.09, 2026-11-24 103.88
- DXY gap stats over 63 days: mean 0.15, within 0.3 on 57 days, worst 0.63
- DXY check, published close (Yahoo DX-Y.NYB, verification only) vs computed from ECB: 2026-11-11 102.91/102.60 (-0.31), 2026-11-12 103.17/102.97 (-0.20), 2026-11-13 103.41/103.24 (-0.17), 2026-11-16 103.55/103.47 (-0.08), 2026-11-17 103.49/103.61 (+0.12), 2026-11-18 103.86/103.80 (-0.06), 2026-11-19 103.90/103.72 (-0.18), 2026-11-20 103.81/103.65 (-0.16), 2026-11-23 104.32/104.09 (-0.23), 2026-11-24 103.81/103.88 (+0.07) | worst gap over 63 days: 0.63
- Buybacks by type, $bn par accepted per month 2026: operation_type  Cash Management  Liquidity Support ; operation_date                                     ; 2026-01                     0.0                9.7 ; 2026-02                     0.0               12.3 ; 2026-03                    29.7                6.9 ; 2026-04                    45.0                6.4 ; 2026-05                     0.0                8.8 ; 2026-06                    24.6                7.3 ; 2026-07                     0.0               10.7 ; 2026-08                     0.0               11.1 ; 2026-09                    25.0               12.8 ; 2026-10                     0.0               26.1 ; 2026-11                     0.0               12.0
- Buyback ops with type 'null' or zero accepted: [{'operation_date': Timestamp('2024-08-21 00:00:00'), 'operation_type': 'Liquidity Support', 'total_par_amt_accepted': 'null'}, {'operation_date': Timestamp('2024-07-17 00:00:00'), 'operation_type': 'Liquidity Support', 'total_par_amt_accepted': 'null'}, {'operation_date': Timestamp('2023-03-30 00:00:00'), 'operation_type': 'null', 'total_par_amt_accepted': '24000000.00'}, {'operation_date': Timestamp('2022-03-30 00:00:00'), 'operation_type': 'null', 'total_par_amt_accepted': '25000000.00'}, {'operation_date': Timestamp('2021-04-07 00:00:00'), 'operation_type': 'null', 'total_par_amt_accepted': '25000000.00'}]
- Coinalyze sample market record: {"symbol": "MNTUSDT.6", "exchange": "6", "symbol_on_exchange": "MNTUSDT", "base_asset": "MNT", "quote_asset": "USDT", "expire_at": null, "has_buy_sell_data": true, "is_perpetual": true, "margined": "STABLE", "oi_lq_vol_denominated_in": "BASE_ASSET", "has_long_short_ratio_data": true, "has_ohlcv_data": true}
- Coinalyze: 5776 futures markets, 5700 perpetuals, 1235 base assets. Perps per exchange: {'Gate.io': 1043, 'Bybit': 923, 'Binance': 832, 'OKX': 553, 'Aster': 549, 'Huobi': 435, 'WOO X': 221, 'Kraken': 196, 'Lighter': 191, 'Hyperliquid': 179, 'Deribit': 153, 'tradeXYZ': 125, 'Coinbase': 96, 'Polymarket': 84, 'dYdX': 57, 'Bitfinex': 55, 'Phemex': 8}
- Coinalyze BTC perps: BTCUSD_PERP.A(Binance), BTCUSDT.6(Bybit), BTCUSD.6(Bybit), BTCUSDC_PERP.A(Binance), BTCUSDT_PERP.A(Binance), BTCU_PERP.A(Binance), BTCUSD1_PERP.A(Binance), pf_xbtusd.K(Kraken), BTCUSD_PERP.3(OKX), BTCUSDT_PERP.4(Huobi), BTCUSDT_PERP.F(Bitfinex), BTCUSDT_PERP.3(OKX), BTC.H(Hyperliquid), BTC-USD.8(dYdX), BTC-PERPETUAL.2(Deribit), PERP_BTC_USDT.W(WOO X), BTCUSD_PERP.4(Huobi), BTC_USDT.Y(Gate.io), BTC-PERP.C(Coinbase), BTC_USDC-PERPETUAL.2(Deribit), 1.T(Lighter), 6.O(Polymarket), BTCUSD.7(Phemex), BTCUSDT.S(Aster), BTCPERP.6(Bybit), BTC_USD.Y(Gate.io)
- Coinalyze rate-limit test, 4 calls x 20 symbols in 0.8s: ['200', '429(retry-after 58.397)', '429(retry-after 58.21)', '429(retry-after 58.018)']; headers {'Retry-After': '58.018'}
- Runner: Linux GitHub Actions 1000000007; time 2026-11-25T08:52:37Z
- Realised price cross-check: Bitview 53,097 (2026-11-24) vs Coin Metrics 53,099 (2026-11-24): gap 0.01%
