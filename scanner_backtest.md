# Coin scanner backtest, 01 Jan 2020 to 26 Nov 2026

**Read this first: survivorship bias.** Only coins that are in today's scanner and have free price history are tested (97 coins; 26 of them from the start of 2020). Coins that died or dropped out (LUNA, FTT and many others) are missing, so these results flatter the rule. No trading costs or slippage. The trend settings were chosen on this same history. Quality is not tested.

| Rule | Growth | Per year | Worst fall | Days invested |
|---|---|---|---|---|
| Dual Bull coins, equal weight, only while the regime is ON (cash otherwise) | 68.38x | +84% | -71% | 60% |
| the same, memecoins left out | 19.78x | +54% | -75% | 59% |
| the same, without its 5 biggest winners (DOGE, SHIB, FET, ADA, SOL) | 12.45x | +44% | -77% | 60% |
| Hold Bitcoin | 8.44x | +36% | -77% | 100% |
| Bitcoin only while the regime is ON | 7.37x | +34% | -50% | 62% |
| Dual Bull rule, from 2022 only | 1.99x | +15% | -58% | 55% |
| Hold Bitcoin, from 2022 only | 1.31x | +6% | -67% | 100% |

## Each new Dual Bull while the regime was ON

| After | Signals | Beat Bitcoin | Median coin | Median Bitcoin |
|---|---|---|---|---|
| 30 days | 565 | 41% | -5.4% | -1.7% |
| 90 days | 508 | 35% | -11.7% | +1.7% |
| 90 days, memecoins left out | 480 | 35% | -11.9% | +1.0% |

## Price data cleaned before testing

- aptos: one-day move of x1.05e+03 on 2022-10-19 treated as a data error: history before it dropped
- sun-token: one-day move of x0.0164 on 2021-06-14 treated as a data error: history before it dropped
- every coin's first 14 days after listing are left out

Regime ON on 62% of days since 2020. Coins tested: AAVE, ADA, AERO, ALGO, APEPE, APT, ARB, ASTER, ATOM, AVAX, BCH, BDX, BGB, BNB, BSV, BTT, BTW, CAKE, CC, CRO, CRV, DASH, DEEP, DOGE, DOT, DRV, ENA, ETC, ETH, ETHFI, FET, FF, FIL, FLR, GRAM, GRASS, GT, HASH, HBAR, HTX, HYPE, ICP, INJ, JST, JUP, KAS, KCS, KITE, LEO, LINK, LIT, LTC, M, MNT, MON, MORPHO, NEAR, NEXO, NIGHT, OKB, ONDO, PENGU, PEPE, PI, PIEVERSE, POL, PUMP, PYTH, QNT, RAIN, RAY, RENDER, SHIB, SKY, SOL, STABLE, STX, SUI, SUN, TAO, TIA, TRX, UB, UNI, VET, VVV, WAL, WBT, WLD, WLFI, XDC, XLM, XMR, XRP, ZEC, ZRO, 币安人生.
