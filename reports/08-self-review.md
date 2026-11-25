# Point 8: review of my own work

Date: 25 November 2026. Question asked: what could show a wrong colour, miss a change, or fail silently?

Two passes were made: my own, and an independent reviewer that read the code cold, was told only the question, and had to prove each finding with a small script. Every confirmed finding below is fixed and has a test. Tests: **308, all passing** locally and on GitHub. The fixes are live on `main`.

## A mistake in my own reporting

I told the owner at point 7 that no push had been sent after go-live. **One had.** At 10:37 UTC (18:37 Hong Kong time) the hub sent a priority-2 push, "Margin debt growth: Against → Neutral". It was not a real change (finding 1). I had not checked the dial-change log before making the statement. The log is now the first thing checked after each run.

## Findings that could show a wrong colour

| # | Finding | Found by | Fix |
|---|---|---|---|
| 1 | **Go-live baseline was not settled.** The warm-up replay dates back-filled data later than a live run sees it (it ended on September's margin debt; the live run saw October's). The first live runs then "changed" a dial and pushed | Me | After the warm-up the dials are settled on the live view before the baseline is recorded |
| 2 | **Stale data could still change a colour.** A dial was greyed when its data was old, but its colour kept being recalculated from that old data | Me | Data older than the dial's limit now counts as "no data": the last colour is kept, greyed, and cannot change |
| 3 | **A stale live price could be used as "now".** If Coinbase failed, the last live price stayed in the bookkeeping and kept being treated as current | Me | A live value expires after twice its source's interval plus 15 minutes |
| 4 | **Buybacks dial froze after my own fix 2.** It is driven by the calendar (no operations means the 4-week total falls), but was dated by the last operation, so after 21 quiet days it would have stayed green as "stale" | Reviewer | Dated "today"; quiet spells are judged, not frozen. Nothing in either period reads neutral |
| 5 | **Liquidity proxy understated growth.** The "now" total used M2 (two months late) and the Bank of Japan (one month late) against values exactly 365 days back, so those parts showed 10 to 11 months of growth. A true 6% read as 5.4% | Reviewer | Each part is compared with its own figure a year before its own latest date |
| 6 | **The no-flap rule could get stuck.** A dial alternating amber and red never confirmed either and stayed green; and "red, no data, no data, red" counted as two runs in a row | Reviewer | Two runs in a row away from the current colour change it, taking the latest; a no-data run restarts the count |
| 7 | **Margin debt with a missing month.** "Three months ago" would silently have become four | Me | Months are laid on a true monthly calendar; a gap gives no reading |
| 8 | **A share price from a session still trading could be stored as a close** if the quote service returned today's row during New York hours | Reviewer (suspicion) | Rows are kept only for New York sessions that finished at least an hour ago |
| 9 | **Liquidity dial's date** was the newer of the Fed and ECB figures, hiding a stale one | Me | Uses the older of the two |

## Findings that could miss a change

| # | Finding | Found by | Fix |
|---|---|---|---|
| 10 | **The "price at or below 1.3x realised price" test had no protection.** A price hovering on that line flipped the reading every run and would have sent a priority-5 push each time | Reviewer | It now gets the same 2% buffer and two-runs-in-a-row rule as every dial |
| 11 | **A dial that failed for one run cleared BREAK, FRAGILE or RISK-OFF.** The facts those rely on vanished with the failed calculation, which would have pushed "BREAK → CALM" | Reviewer | Those facts are carried forward from the last good run |
| 12 | **Holes in history after a pause.** Sources were asked for a fixed number of recent days. Pausing the hub for longer would have left permanent gaps (a missed weekly close, for one) | Me | Each request reaches back to the last stored date. The ECB switches to its full file after 80 days |
| 13 | **Pushes waiting for retry were discarded** when a run was made with pushes switched off | Reviewer | They are kept |
| 14 | **No alert when a dial went stale** | Me | One priority-3 push when a dial goes stale; stale dials are listed in the daily digest |
| 15 | **One working series hid another that kept failing** within the same source | Reviewer (suspicion) | Failures are counted per series; four in a row sends "source partly down" |

## Findings that could fail silently

| # | Finding | Found by | Fix |
|---|---|---|---|
| 16 | **The save step reported success when every attempt to save had failed** | Me | It now exits with an error |
| 17 | **Its retry could not work** on GitHub's shallow checkout, and a network error while opening the data branch was treated as "the branch does not exist", so a run could have started from empty | Reviewer | Fetches enough history before retrying; only a definite "no such branch" answer starts a new one. Tested against a competing writer and a dead remote |
| 18 | **A crashed or timed-out run told nobody** | Me, sharpened by the reviewer | A priority-4 push, at most once an hour, on failure or timeout. Publishing failures push too, at most twice an hour |
| 19 | **Two workflows could write the data branch at once** | Me | They share one queue |

## Checked and found sound

Band edges and the 2% buffer; the dollar's two-fixing rule; weekly close on the Sunday candle; the month-end rule (a month counts only once a later month has data); units (FRED millions and billions, basis points); look-back lengths; lining up 7-day crypto data with 5-day market data; Coinbase around midnight UTC; the store's revision and point-in-time logic; digest timing in Hong Kong time; first-run silence; page text escaping.

## Known and accepted, not fixed

- **A source that answers "200 OK" with no rows** is treated as healthy. Finding 14's stale alert catches it within the dial's age limit (5 days for daily data), not at once.
- **Bitcoin price during a Coinbase outage** falls back to the last daily close and shows "(1d old)". After a day it greys out. For up to a day the price dial could sit on yesterday's close.
- **Failure pushes are rate-limited by the clock** for the publishing job (it has no memory between runs), so a publishing failure could take up to 30 minutes to announce.
- **GitHub's own timer** can run late or skip. The dashboard's "updated" label turns amber after 60 minutes, and the daily digest is the heartbeat. The backstop for a disabled schedule is point 9.
- **The replay was not re-run** after these fixes. Fix 6 (the no-flap rule) and fix 10 (the 1.3x test) can shift a signal by a day; fix 5 changes the liquidity reading slightly. The staleness rule is switched off in replays, as back-filled data is dated by estimate. `06b-history-replay.md` therefore describes the rules a hair before these fixes.

## Owner's instruction at this stop: S&P 500

FRED's close keeps setting the colour. Beside it the dial shows an unofficial same-day figure.
**Nasdaq's quote service does not carry the S&P 500 index itself.** The same-day figure is therefore FRED's last close moved by the change in the SPY fund since that day, labelled "unofficial, same day … from the SPY fund". On 24 November that gives about 7,202; the owner's phone showed 7,201. It never colours the dial and is hidden when it is not newer than FRED's figure.

## Queued by the owner for after point 9

1. "Coin valuations" tab (log-regression channels, ten coins).
2. Plain-language dashboard redesign (traffic light, backdrop line, group sentences).
