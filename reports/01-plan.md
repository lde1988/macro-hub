# Point 1: the plan

Date: 25 November 2026. Status: approved by the owner.

## How it is built

1. **One job, every 15 minutes, on GitHub Actions.** It fetches data, updates the history, works out the dials and the reading, then publishes the dashboard, the feed and any pushes, all from that same run.
2. **Series registry** (`registry/series.yaml`): one entry per data series. Small "adapters" in `hub/sources/` know how to talk to each site (FRED, Coinbase, Bitview and so on).
3. **History store**: one tidy table per series with the columns *date the value is for, value, when we first saw it*. A revised figure is added as a new row and never overwrites the old one, so a bot being tested sees only what was known at the time.
4. **Signals** (`hub/signals/`): plain calculations over the store with no internet access, each tested with made-up data. Tests run on every change.
5. **Config** (`config/thresholds.yaml`): every level and band in one file, each with a comment.
6. **Where state lives**: a separate `data` branch holds history, the verdict log, alert state and levels. It is committed only when something changed, so the main branch stays small.
7. **Dashboard**: published straight to GitHub Pages from the run, with no extra branch. A single dark page with drawn dials, installable on an iPhone.
8. **Feed**: `latest.json` (versioned), history files and `FEED.md` describing the layout.
9. **Alerts**: ntfy on change only, a silent first run, retry on failure, a "source down" push after 4 failed runs, and the 08:00 HKT digest.
10. **Keeping the schedule alive**: GitHub switches schedules off after 60 days without activity. The daily digest commit counts as activity. GitHub's timer is "best effort", so runs often start 5 to 20 minutes late; the dashboard shows data age so this is visible. Owner's addition: if GitHub ever disables the schedule the job cannot re-enable itself, so a backstop is to be added at point 9, with the manual switch-back-on steps in the README.
11. **Room to grow**: empty, documented slots for SEC EDGAR, equities and bots. Nothing is built for them.
12. **Phase 2** (weekly sweep): plumbing only, switched off until `XAI_API_KEY` exists.

## No free source: would need paid data, or a labelled substitute

- **Coutts' own liquidity index**: proprietary. A labelled proxy is shown instead.
- **The official ICE dollar index quote**: licensed. Computed from ECB rates instead.
- **True rate-hike pricing from Fed funds futures**: CME data is paid. The 2-year yield minus Fed funds stands in.
- **History of Bitcoin dominance / total altcoin value**: free only for "now". The dial builds its own history from launch and cannot be replayed over past cycles.
- **China's central bank balance sheet and non-US money supply**: FRED's series have stopped (confirmed at point 2).

## Working arrangements found at the start

- The repository held only a one-line README.
- The build workspace could not reach market-data sites until a "macro-hub" environment allowing only the named public data hosts was approved.
- FRED refuses keyless downloads from the build workspace, so FRED is always verified through a GitHub Actions run.
