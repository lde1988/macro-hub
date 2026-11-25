# Point 7: dashboard

Date: 25 November 2026. Status: **built and running; waiting for the owner to switch GitHub Pages on** so it has an address.

## What was built

- **Dashboard** (`hub/outputs/dashboard.py`): one static page, dark, no external scripts or fonts. One column on a phone, two or three on a desktop.
  - Order: regime banner with "updated … HKT" (turns amber when older than 60 minutes); the Bitcoin reading with its reasons, what would change it and how long it has been in force; the altcoin line; the trend-exit line; one line per family (colour, word, symbol and a sentence) with that family's dials folded underneath; "what they're watching" (empty until Phase 2); sources footer with each source's last successful fetch.
  - Under the reading: "Framework reading, not financial advice" and "Built to spot buy zones. Its exit signals have a weak record."
  - A froth warning shows its record beside it ("right on 3 of 8 past occasions").
  - Every dial is a drawn semi-circular gauge with a needle, three bands, the reading, the word (Supports / Neutral / Against) with a symbol, and one sentence on what would move it. Stale dials are greyed with the reason.
  - Live dials show the fixed levels and the moving equivalents side by side (value zone $58,600 fixed against 1.10x realised price; weekly lines $70,000 / $73,000 against short-term holder cost).
  - On a phone the families are folded (the page is about three screens long); on a desktop they open automatically.
- **Installable**: web app manifest and icons (drawn in code, so the repository holds no binary files).
- **Feed** (`feed/latest.json`, version 1.0), per-series history files, the verdict log and the dial-change log, with the layout documented in `FEED.md`.
- **Alerts** (`hub/alerts.py`): push on change only; first run is a silent baseline; failed pushes are retried next run; "source down" after 4 failed runs; one quiet digest at 08:00 Hong Kong time.
  - Priorities: reading change 5 (4 when a froth warning is involved); regime change 5; trend exit 5; dial to red 4; dial green-to-amber 3; improvements 2; source down 3; digest 2.
- **Run script and workflow** (`hub/run.py`, `.github/workflows/hub.yml`): one run does fetch, evaluate, outputs, log and pushes. Not on a schedule yet (point 9).
- **State without bloat**: history, dial state and logs go to the `data` branch only when something changed. Fast-changing bookkeeping (when each source was last asked, live values) lives in the Actions cache, so the data branch is not committed every 15 minutes.

## Rule changes made at this stop (owner's decisions after point 6)

Froth warning with the 1.3x guard; the trend-exit line; STRESS BUILDING needing two families or one buy-blocking family. Replayed in `06b-history-replay.md`.

## Tests

287 tests, all passing locally and on GitHub. New at this stop: feed layout, stale-data marking, dashboard order and self-containment, colour never the only cue, alert priorities, digest timing, and a full two-run test (silent baseline, then a change whose push fails once and is retried).

## First run on the main branch (10:18 UTC)

- The code was published to `main` (a fast-forward from `claude/build`), which GitHub requires for Pages.
- Fetch, evaluation, outputs, log and data save all succeeded. First verdict logged: Hold: fairly cheap, but the turn is not confirmed (CAUTION); regime BREAK; trend exit RISK-OFF; Bitcoin $58,917, 1.11x realised price.
- No push was sent: the first run is the silent baseline.
- **The publishing step failed because GitHub Pages is not switched on for the repository.** That needs one setting only the owner can change: Settings → Pages → Source: GitHub Actions.

## Known gaps at this stop

- Funding and altcoin open-interest: funding history is loaded; the open-interest totals wait on the one-off Coinalyze pull.
- The owner's comparison of Bitcoin, the S&P 500 and the dollar index against their phone has not happened yet (needs the live address).
