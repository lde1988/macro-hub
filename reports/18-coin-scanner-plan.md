# Point 18: Coin scanner tab, plan (nothing built)

Date: 27 November 2026. Waiting for the owner's approval.

**What was checked:**
- A free, read-only check on a GitHub runner (run 45945660268, results on the `scanner-check-results` branch).
- Calculations on the hub's own saved history.

**Nothing paid was used. Nothing is on `main`.**

## In short

- A third tab, **Coin scanner**, next to Dashboard and Coin valuations.
- **What it covers:**
  - About 100 coins plus your 10.
  - Two trend ratings per coin: in dollars, and against Bitcoin.
  - A quality score from free revenue and supply data.
  - The hub's Bitcoin regime as the gate.
- **Daily job:** it runs once a day after the 00:00 UTC close and costs nothing.
- **Context only:** it never touches the buy / hold reading or a dial.
- **One push at most a day:** only when a coin newly becomes Dual Bull, passes quality, and the regime is ON.
- **Backtest:** daily snapshots are kept, and a backtest from 2020 is reported with its survivorship bias stated.

## 1. Cross-check: the Bitcoin regime line

Helios showed its regime line at **$72,210** on the 25 November close, regime OFF.

Bitcoin's close on 25 Nov:
- Coinbase: $60,384
- Coin Metrics: $60,268

| Candidate line, 25 Nov close | Level | Difference from Helios |
|---|---|---|
| **Short-term holder realised price** (Bitview, already in the hub) | **$72,134** | **−$76 (−0.1%)** |
| 200-day simple average (Coinbase closes) | $72,027 | −$183 (−0.25%) |
| 150-day simple average | $72,902 | +1.0% |
| 30-week simple average | $72,628 | +0.6% |
| 200-day exponential average | $74,655 | +3.4% |
| The hub's trend exit today | break $70,000 / reclaim $73,000 (fixed, weekly closes) | −3.1% / +1.1% |

**Regime state:**
- Every candidate puts Bitcoin well below the line, so the regime is **OFF**, as in Helios.
- The hub's own trend exit reads **RISK-OFF**, which agrees.

The two closest are the short-term holder cost and the 200-day average. Both are within 0.25%, so I cannot tell from one day which Helios uses.

**Proposal for the gate (decision A):**
- Use the hub's existing trend exit: ON when it reads RISK-ON. This is the line Coutts' levels feed, and it moves only on weekly closes.
- Show the short-term holder cost beside it as "the regime line, $72,134".
- The alternative is a daily gate on the short-term holder cost, with the hub's 2% buffer and two-closes rule. It reacts faster, but would sometimes disagree with the dashboard's trend line.

## 2. Universe

**Rule:**
- Start from CoinGecko's top 250 by market cap (one free call).
- Remove:
  - stablecoins;
  - wrapped, bridged and liquid-staking or restaking copies;
  - tokenized gold, commodities, funds, Treasuries and stocks;
  - anything whose price hardly moves (30-day volatility under 1%, a safety net for pegged tokens the categories miss).
- Take the first 100 that remain.
- Always add your 10.

**What the check found today:**
- CoinGecko's categories do the main work:
  - 15 categories were usable;
  - 2 were not found (crypto-backed tokens, tokenized Treasury bills).
- **Its "exchange-based tokens" category is too broad.** It also holds DEX and trading-platform tokens: HYPE, UNI, JUP, CRV, CAKE, PENDLE, RAY, ASTER, PUMP.
- **The raw top 100 still holds tokenized funds and stocks** that the categories miss: BUIDL, USYC, OUSG, USTB, JAAA, EUTBL, NVDAB and a few more. The "price hardly moves" test and a short exclusion list in the config will catch these.
- Every exclusion will be listed in the tab with its reason, so nothing disappears silently.

**Exchange tokens (decision B).** I read "exchange-pegged tokens" as tokens whose price is tied to something else, and these are removed as above. Exchange-issued tokens such as BNB, OKB, LEO, CRO, KCS and GT are not pegged. **Proposal:** keep them, labelled "exchange token" and hideable like memecoins. The alternative is to exclude them.

**Memecoins:** kept, labelled and hideable. Today: DOGE, SHIB, PEPE, BONK, PENGU, TRUMP and a few smaller ones.

**Sectors:** from CoinGecko's coin pages (one call per coin, refreshed weekly in small batches to stay within the free limit) and DefiLlama's category. I will keep a short list of plain sector names: L1, L2, DeFi, AI, Payments, Privacy, Meme, Exchange, Infrastructure, Gaming, RWA, Other.

## 3. Two trend ratings per coin (an open approximation)

Alex Cole's Trend Chameleon formula is not public, so this is my own transparent rule, not a copy.

**Each rating is computed for:**
- the coin in dollars (own trend);
- the coin divided by Bitcoin (vs BTC).

**On each daily close, three yes / no / neither tests:**
1. **Position**: is the price more than 3% above its 50-day average (+1), more than 3% below (−1), or in between (0)?
2. **Direction**: has the 50-day average risen by more than 1% over the last 10 days (+1), fallen by more than 1% (−1), or neither (0)?
3. **Momentum**: is the 20-day move large compared with the coin's normal swings? The test is the 20-day move divided by its usual 20-day size (from the last 90 days): above +0.75 is +1, below −0.75 is −1, otherwise 0.

**Score = the sum, from −3 to +3:**

| Score | State |
|---|---|
| +3 | Strong Bull |
| +2 | Bull |
| −1 to +1 | Neutral |
| −2 | Bear |
| −3 | Strong Bear |

**Settling (hysteresis):**
- A new state counts only after **5 daily closes in a row**.
- The 3%, 1% and 0.75 bands stop a price sitting on a line from flipping.
- "Days since" counts from the confirmed change.

**Dual Bull** = own trend Bull or Strong Bull **and** vs BTC Bull or Strong Bull.

**Tried on real history (Coin Metrics, 2020 to today):**

| Variant | State changes a year | Entries into "Bull or better" a year (what alerts depend on) |
|---|---|---|
| 3 days to settle, narrow bands | 25 to 27 | 3.7 to 4.6 |
| **5 days to settle, wider bands (proposed)** | **16 to 18** | **2.1 to 3.3** |
| 7 days to settle | 13 to 15 | 2.0 to 3.0 |
| 5 days, 100-day average | 14 to 16 | 1.8 to 2.5 |

Most of the 16 to 18 changes a year are between neighbours (Bull ↔ Strong Bull). Bitcoin's own trend on 25 Nov reads **Strong Bear**. Every setting is in the config, with a comment.

## 4. Quality score (free data; "no data" is never "bad")

| Part | Measure | Good | Neutral | Bad | Data today |
|---|---|---|---|---|---|
| **Revenue growth** | Protocol or chain revenue, last 90 days against the 90 before (DefiLlama; fees when no revenue figure) | up 20% or more | −20% to +20% | down 20% or more | fees for 51 of 103 coins, revenue for 34 |
| **Dilution** | Circulating supply growth over a year (CoinGecko market cap ÷ price, 365 days, free); also circulating ÷ fully diluted | under 2% a year | 2% to 10% | over 10% a year, or under 50% of supply circulating | about every coin, where CoinGecko gives a market cap |
| **Value accrual** | Share of revenue going to token holders (buybacks, burns, staking), last 90 days (DefiLlama "holders revenue") | 50% or more | 10% to 50% | under 10% | 21 of 103 coins |

**Score:**
- Each part is ✓ good, ● neutral, ✗ bad, or – no data.
- **Passes quality** = no ✗ and at least one part with data.
- A coin with no revenue data (most memecoins, Bitcoin itself) is judged on dilution alone and shown as "1 of 3 parts scored".

**Your 10 today:**

| Coins | Revenue data from DefiLlama |
|---|---|
| ETH, SOL, NEAR, SUI, HYPE | fees, revenue and holder revenue |
| WAL | fees and revenue |
| BTC, ZEC | fees only |
| LINK, DEEP | not matched automatically; DefiLlama has them (Chainlink, DeepBook, from point 12), so a short hand-made mapping file will link them |

**Unlocks: not available free.** DefiLlama's unlock data answered "Upgrade to the paid API plan" (HTTP 402). A list of the protocols it covers is free, but the schedules are not. Per your rule I have not used anything paid. Unlocks show "no free data", and the dilution part relies on past supply growth and circulating ÷ fully diluted.

## 5. The table (Helios-style)

**Columns:**
- asset, with its sector and labels (meme, exchange token, one of yours);
- price;
- % since signal: since its current own-trend state began;
- 7-day %;
- own trend;
- vs BTC;
- days since: the later of the two changes;
- quality: three small marks plus pass or fail.

**On a phone:**
- Coin and state stay visible, and the other columns scroll sideways.
- Tap a row for its detail: the three trend tests, the three quality parts with numbers and sources.

**Controls:**
- Sort by any column (a small piece of code inside the page; no outside scripts, as now).
- Filter chips: All, Dual Bull, Bull, Neutral, Bear, Strong Bear, Yours.
- "Hide memecoins" and "Hide exchange tokens" switches, remembered on your phone.

**Top banner:**
- **Regime OFF:** "No buy candidates: Bitcoin regime OFF", then the **relative-strength watchlist**. These are the 15 coins holding up best against Bitcoin since the regime turned OFF (coin ÷ BTC since that date), with their vs-BTC trend.
- **Regime ON:** "Buy candidates", the coins that are Dual Bull and pass quality.

Every row and banner carries "context, not advice; never part of the reading".

## 6. Push alert

- **At most one a day**, priority 3, a short digest: "New Dual Bull with quality, regime ON: SOL (L1, quality 2/3 ✓), …"
- **Only for coins that newly** became Dual Bull and pass quality, on a day the regime is ON.
- **Nothing else pushes**: no exits, no regime messages. The dashboard already pushes the trend line.

## 7. History and honesty

**Daily snapshots:**
- One file per day on the data branch (`scanner/snapshots/YYYY-MM-DD.csv`).
- Each holds every coin's rank, price, market cap, both states, quality parts and the regime, as known that day.
- These snapshots are the honest record; the backtest is not.

**Backtest from 1 Jan 2020** (Coin Metrics daily closes, free):
- **Rule tested:**
  - each day, the coins that are Dual Bull while the regime is ON;
  - held in equal weights, rebalanced weekly;
  - in cash while the regime is OFF.
- **Compared against:** holding Bitcoin, and Bitcoin with the same regime gate.
- **Reported:** yearly return, worst fall, time in the market, and each signal's 30 and 90-day result against Bitcoin.
- **Quality is not in the backtest.** Supply history is free for only a year, and revenue history covers too few coins in 2020 to 2022. It is judged going forward from the snapshots.

**Caveats, stated on the tab and in the report:**
- **Survivorship bias.** Only 23 of today's coins have free price history from 2020, and today's top 100 is chosen with hindsight. Coins that died (LUNA, FTT and many others) are missing, so the backtest flatters the rule.
- **No trading costs** or slippage are included.
- **The rule's bands were chosen on this same history.** A backtest on the history used to choose them is not proof.

## 8. Data sources (all free), schedule and cost

| Need | Source | Check today |
|---|---|---|
| Top coins, prices, market caps, supply, categories | CoinGecko (no key, already used by the hub) | works; 250 coins in one call; about 15 category calls |
| Daily price history | Coin Metrics community (74 of 103 coins), then Coinbase (65), then CoinGecko's free 365 days | 24 coins have none of the first two; most of them are excluded anyway (tokenized funds, stocks). The rest start from CoinGecko's year and grow from there |
| Revenue, holder revenue | DefiLlama (no key, already used) | as in section 4 |
| Supply growth | CoinGecko 365-day market cap ÷ price | works |
| Bitcoin regime | the hub's own trend exit and Bitview | already there |

**Schedule:**
- A daily job at 00:50 UTC (08:50 Hong Kong), after the open-interest job, takes about 10 to 15 minutes.
- **The first load** of price history takes longer, once.
- **Backstop:** if the day's snapshot is missing, the hub run starts the job, as for the weekly sweep.
- **Cost: $0.** No keys, and no paid source.

## 9. Rules kept

- **Context only:** it never changes the buy / hold reading, a dial, a band or a rule. A test will run the hub with and without scanner data and require identical results, as for the sweep.
- **No exchange keys, no holdings.**
- **Tests for everything** (made-up data):
  - the trend rules and each band edge;
  - the 5-day settling;
  - Dual Bull;
  - each quality part and "no data";
  - universe exclusions;
  - the alert's once-a-day rule;
  - the snapshot format;
  - the backtest arithmetic;
  - page escaping.

## Decisions for the owner

| | Decision | My proposal |
|---|---|---|
| A | Regime gate | The hub's trend exit (weekly closes, $70,000 / $73,000, Coutts-updatable); short-term holder cost shown as the line |
| B | Exchange-issued tokens (BNB, OKB, LEO, CRO…) | Keep, labelled and hideable |
| C | Trend settings | 50-day average, 3% / 1% / 0.75 bands, 5 closes to settle |
| D | Quality thresholds | As in section 4; "passes" = no ✗ and at least one part scored |
