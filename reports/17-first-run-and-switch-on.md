# Point 17: published, first full run, its cost, and switched on

Date: 26 November 2026.

## Date window (owner's check)

Each run reads **the 7 days before it starts**. The first run started at 10:47 UTC on 26 Nov, so it read 19 Nov 10:47 UTC to 26 Nov 10:47 UTC; the X search covered 19 to 26 Nov. A test now locks this in. My earlier "26 November to 3 December" was a slip in my message, not in the code.

## Published

- **`main`** has the sweep code: first commit bea6659, then fixes 7123364 and the backstop 2342b20.
- **Tests**: 554, all passing here and on GitHub.
- **The reading did not change.** The first hub runs on the new code (11:00, 11:30 UTC) gave the same Hold, BREAK, trend line RISK-OFF, with 39 of 40 dials coloured.
- **Your outside scheduler is working.** Since about 10:15 UTC the hub has run every 15 minutes, started from outside ("workflow_dispatch").

## First full run (Weekly sweep, run 45804599493, 10:47 to 11:12 UTC)

**53 records. Cost $2.34** (xAI $1.66, Groq $0.68, Gemini $0).

| Part | Volume |
|---|---|
| X | 150 posts from 20 accounts, 4 calls |
| Podcasts | 20 episodes, 16.9 hours (own shows and guest appearances) |
| Newsletters | Substack refused this runner again; read through xAI web search: Pal 2 posts, Howell 4 posts; 2 long enough to read |
| YouTube | 49 videos listed, waiting for the Gemini key |

**Month so far: $2.34 of $20** in the sweep's cost log. The $1.93 spent on checks and tests earlier today was on the same xAI and Groq accounts but is **not** in that log.

**Pushes sent**: one, "weekly sweep done" (priority 2). No Coutts level was stated, so there were no level updates and no questions.

### What the group said, 19 to 26 November (as on the dashboard)

| Topic | Positive | Neutral | Negative | Mixed |
|---|---|---|---|---|
| Liquidity | 0 | 0 | 2 | 1 |
| Crypto | 4 | 0 | 0 | 1 |
| AI spending | 1 | 0 | 3 | 1 |
| Credit risk | 0 | 0 | 3 | 0 |

**Measures cited by several people:**

| Measure | People |
|---|---|
| Bitcoin price | 4 |
| Global liquidity | 4 |
| AI capital spending | 3 |
| Corporate earnings | 2 |
| Oil | 2 |
| S&P 500 | 2 |
| Stock valuation multiples | 2 |

**Scorecard** (four open calls):
- Howell, by end of 2027.
- Steno, "rate cuts next year" by end of 2027. His speaker is "not certain": it comes from Macro Mondays.
- Pal, by 2030.
- Alden, by 2030.

## Problems the first run showed, all fixed and published the same day

| # | Problem | Fix | Cost to fix |
|---|---|---|---|
| 1 | **A wrong comparison was live for about 20 minutes**: Pal's "140%" was read as a Bitcoin price of $140, shown as a −99.8% gap | A percentage or basis points is never compared with a price or an index. Also found: "330bp" was read as 330 billion. Both fixed; the panel was rebuilt for free from the saved records, and the comparison now reads "units not comparable" | $0 |
| 2 | Two X calls (Alden, Howell, Garg, Follonier, Diamandis, Druckenmiller, Mostaque, Odd Lots, Kedrosky) returned 0 records from 74 posts | When an answer cannot be read, the reason is logged and each account is retried on its own, within the caps and budget | $0 now; a few cents on a bad week |
| 3 | Odd Lots gave 0 records: the model named "Tracy Alloway", who was not on the list | The hosts are listed as names for the show, and count as one speaker, not a shared show | $0 |
| 4 | One Diamandis episode failed on an empty last audio piece | Pieces under a second are not sent | $0 |
| 5 | The Druckenmiller name search found a 2023 talk re-posted this week | Titles naming an earlier year are skipped as old talks | $0 |
| 6 | The weekly sweep depends on GitHub's own timer, which proved unreliable this week | Backstop: each hub run checks; on Sunday evening or Monday, if no sweep has been saved for 6 days and none is running, it starts one. It never starts a second one and respects `enabled` | $0 |

There is also a new **"rebuild only"** tick-box on the Weekly sweep button. It works the panel out again from saved records, for free.

## Switched on

- `enabled: true` in `config/sweep.yaml`.
- **Next run: Sunday 29 November, 12:07 UTC (20:07 Hong Kong).** If GitHub's timer misses it, the hub starts it from 21:30 Hong Kong.
- Gemini stays off until `GEMINI_API_KEY` exists. Once the secret is added, the next run reads the YouTube-only videos with no other change.

## Not checked from here

The live page itself: GitHub's file storage is outside this workspace's network rules. The checks made were:
- the saved panel data on the data branch;
- the hub run at 11:30 UTC, which used the new code after the rebuild and succeeded;
- the same rendering checked locally at point 16.
