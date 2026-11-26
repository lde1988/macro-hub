# Point 14: source test on one real week (19 to 25 November 2026)

Date: 26 November 2026. Two test runs on GitHub runners: 09:36 UTC (run 45792204133) and 09:44 UTC (run 45794482788).
The code is on the `claude/sweep-check` branch; nothing is on `main` or scheduled. The full result tables and every
record are on the `sweep-check-results` branch (`source_test.md`, `records.jsonl`, from the second run).

## Cost of the test

| Run | xAI | Groq | Total |
|---|---|---|---|
| First (X part failed on a bug, since fixed) | $0.24 | $0.09 | $0.34 |
| Second | $1.03 | $0.14 | $1.17 |
| **Phase 2 so far, including the people checks ($0.42)** | | | **$1.93** |

## What works from a GitHub runner, source by source

| Source | Works? | Detail |
|---|---|---|
| **X search**, limited to the handles, images on | **Yes** | 149 posts read in two calls of 10 handles ($0.85). Charts are read: e.g. Rosenvold's oil-price chart, Kedrosky's data-centre chart, Bittel's earnings chart. **But coverage is thin**: only 10 records from 18 accounts. The build will use smaller batches (5 handles a call) so every account is searched |
| **Podcast feeds** (own shows) | **Yes** | Every listed feed answered |
| **Podcast guest appearances** (Apple's directory, searched by name) | **Yes, well** | 24 episodes of 10 minutes or more found this week. Examples: Baker on Monetary Matters, Visser on Pomp, Alden on TFTC and Palisades, Kedrosky on Alpha Exchange, Rasmussen on The Acquirers Podcast, Mumtaz on Crypto Banter, Steno and Rosenvold on Real Vision |
| **Paid transcription (Groq)** | **Yes** | 3.6 hours of audio for $0.14, about **$0.04 an hour** as listed |
| **YouTube channel feeds** | Yes, for listing | They list new videos but not their length |
| **YouTube name search** | Yes, after filtering | Unfiltered, it returned junk: Quran recitations for "Ali Yahya", a baseball pitcher for "Rasmussen", and many clickbait re-upload channels with invented quotes ("Raoul Pal Shared a Horrible News"). **Now only channels on a list in `config/sweep.yaml` count** (Real Vision, Monetary Matters, Morgan Stanley, TFTC and so on). You can add to it |
| **YouTube captions** | **No: blocked** | "YouTube is blocking requests from you" (RequestBlocked) |
| **YouTube audio download** | **No: blocked** | "Sign in to confirm you're not a bot" |
| **Gemini reading a YouTube link** | Built later, switched off | Waits for `GEMINI_API_KEY` (Monday). It is the only route to YouTube-only content, such as Visser's own videos or Morgan Stanley's Druckenmiller interview |
| **Substack newsletters** | **Sometimes** | The first runner read all of them; the second was refused (403) on every one, even with a browser-like request. Substack blocks some GitHub servers and not others. Fix in the build: retry, then fall back to reading the same posts through xAI's web search (a few cents) |
| **lynalden.com** | **No** | The site drops connections from the runner. Lyn Alden is still covered by X and her many podcast appearances |
| **Verdad, diamandis.com, a16z Frontier** | Yes | No new posts this week |

**Dormant newsletters:** these feeds have no posts for months, so the sweep will find little there. Most of what these people say now comes through X and guest appearances.

| Newsletter | Last post |
|---|---|
| Steno's Signals | Jul 2025 |
| pmarca | Jul 2024 |
| Kedrosky's Substack | Aug 2023 |
| Intelligent Internet | Jan 2025 |
| Diamandis blog | Jul 2025 |

## Handles settled

| Person | Handle | Evidence |
|---|---|---|
| Ali Yahya | **@alive_** | xAI found the account. Bio "Before: GP @a16z, Google Brain, @Stanford CS", posting on 25 Nov |
| Mert Mumtaz | **@mert** | xAI found the account. Bio "ceo @helius @heliusprivacy — Solana RPCs & APIs", posting on 25 Nov |

## Ten sample records (real content, 19 to 25 November)

Quotes are copied exactly from the source. For newsletters and podcasts, the code checks that every quote really appears in the text and drops any record whose quote does not. For X, the post text comes only through xAI, so that check is not possible; instead the link must be a post by one of the listed accounts.

**1. Jamie Coutts, X, 26 Nov.** [Post](https://x.com/Jamie1Coutts/status/2125796107737506016)
- Claim: "In DeFi, revenue is 5.5x, and the multiple is sub-10x (down 80%)."
- Chart read: "DeFi revenue growth and valuation multiple compression."
- Stances: none stated.

**2. Mikkel Rosenvold, X, 25 Nov.** [Post](https://x.com/RosenvoldGeo/status/2125681587190722937)
- Claim: "The all-in price of a Middle East barrel is down $50 from its October peak."
- Chart read: all-in barrel price peaking at $211 on 8 Oct, falling to about $160 by late November.
- Stances: none stated.

**3. Julien Bittel, X, 24 Nov.** [Post](https://x.com/BittelJulien/status/2125192486582682112)
- Claim: "The AI capex build-out sent 12-month forward earnings up 39%. But higher bond yields and tightening financial conditions crushed the multiple, from 23.3x a year ago to 17.3x today … my models say we're at peak earnings."
- Metric: forward earnings, +39%.
- Chart read: the S&P 500's 12-month change split into earnings and the multiple.

**4. Paul Kedrosky, X, 25 Nov.** [Post](https://x.com/pkedrosky/status/2125698834143793506)
- Claim: "Texas and the Mountain West now account for 67% of queued data-center capacity among the ten leading states, up from 40% in Q2 2025. Wyoming's queue grew from 1.3 GW to 27.6 GW."
- Chart read: Texas 57.0 GW, Wyoming 27.6 GW.

**5. Michael Howell, newsletter, 25 Nov.** [Post](https://capitalwars.substack.com/p/are-markets-huang-by-their-own-petard) ("Are Markets Huang By Their Own Petard?")
- Liquidity: **negative**. "We argue that weakening Global Liquidity is the underlying driver of market turbulence, with its effects now spreading towards economic activity."

**6. Michael Howell, newsletter, 24 Nov.** [Post](https://capitalwars.substack.com/p/global-liquidity-watch-weekly-update-54c) ("Global Liquidity Watch: Weekly Update")
- Claim: "Global liquidity is essentially flat, despite a marginal weekly increase taking it back up to its previous record high."
- Liquidity: **positive**. "Benign funding conditions continue to support liquidity."
- Records 5 and 6 together: Howell gave a negative and a positive liquidity line a day apart. That is the kind of nuance the "changed their mind" flag will need to treat with care.

**7. Andreas Steno Larsen, podcast (Real Vision, "Why This AI Selloff Looks Like 1998"), 23 Nov, at 7:33.** [Episode](https://podcasts.apple.com/us/podcast/why-this-ai-selloff-looks-like-1998-macro-mondays-with/id1210383304?i=1000803639813)
- Claim: the AI sell-off mirrors 1997–98, when semiconductors lost 50%.
- Credit risk: **negative**. "at some point during this build out, the credit market says, hey, hey, hey, hey, hey, we cannot continue funding this."
- AI spending: **negative**. "Oracle has traded like a junk credit as well."
- **Caveat:** Steno and Rosenvold share this show, and transcripts carry no speaker names. Who said it is the model's judgement (see problem 2).

**8. Gavin Baker, podcast (Monetary Matters), 23 Nov, at 12:47.** [Episode](https://podcasts.apple.com/us/podcast/gavin-baker-the-ai-capex-cycle-will-be-longer-than/id1769093906?i=1000803638716)
- AI spending: **positive**. "GPU rental prices. And those are going straight up. They're up dramatically over the last month, three months, year."

**9. Lyn Alden, podcast (Palisades Gold Radio), 25 Nov, at 33:15.** [Episode](https://podcasts.apple.com/us/podcast/lyn-alden-structural-run-it-hot-environment-gold-the/id1439485214?i=1000803966850)
- Claim: private credit is frothy but a low risk to the banks. "I tend to fade the idea that private credit is going to blow up in such a way that it kind of cascades into our banking system."
- Credit risk: **negative**. "I do think that's an area that has gotten frothy."

**10. Dan Rasmussen, podcast (The Acquirers Podcast), 19 Nov, at 54:04.** [Episode](https://podcasts.apple.com/us/podcast/ai-spending-market-risk-capex-valuations-returns-dan/id1454112457?i=1000802883466)
- Metric: high-yield spread, 330.
- Credit risk: **negative**. "I'm on the side of when you see spreads blowing out, be nervous."
- For comparison only: the hub's own high-yield spread on 23 Nov was 3.63% (363bp).

All 28 records from the second run are in `records.jsonl`: X 10, podcasts 18. The 7 newsletter records came from the first run.

## Problems found, and the fix for each (to be built at point 3)

| # | Problem | Fix |
|---|---|---|
| 1 | **Deadlines on calls were wrong.** Visser's "S&P 500 up 15% next year" was dated end of 2026 instead of 2027. Two of Alden's calls were given the episode's own date | A call is kept only if its deadline is after the date it was made. Deadlines like "next year" are worked out by the code from the date said, not by the model. Tested |
| 2 | **Podcasts have no speaker names.** On a shared show (Macro Mondays: Steno and Rosenvold) the model decides who spoke, and it can be wrong | When two or more listed people are on the same episode, the record is marked "speaker not certain" and the dashboard says so. Such records do not count toward anyone's change of mind |
| 3 | **Thin X coverage**: 10 records from 18 accounts | 5 accounts per call; caps still apply (300 posts a week) |
| 4 | **Metric and level sometimes swapped** (Coutts: metric "5.5x", level "DeFi revenue") | The level must contain a number and the metric a name; swapped pairs are put right; anything else is cleared |
| 5 | **Substack blocks some runners** | Retry; then read the same posts through xAI's web search |
| 6 | **YouTube words unreachable** until Gemini | Videos that are also podcasts are covered by the audio; YouTube-only videos wait for Gemini (Monday) |
| 7 | **An existing hub test reaches the internet** (`test_go_live_does_not_push_changes_that_are_only_the_warm_up_settling` calls DefiLlama). It passes on GitHub but fails where DefiLlama cannot be reached. That breaks the rule "tests use made-up data" | Give it a fake DefiLlama |

## Expected weekly cost, from this week's real volumes

| Part | This week's volume | Estimate a run |
|---|---|---|
| X, 4 calls of 5 accounts, images on | about 150–300 posts | $1.50–2.50 |
| Podcast audio (Groq) | 24 episodes, about 23 hours | $0.95 |
| Reading transcripts and newsletters (xAI) | | about $0.50 |
| Substack fallback, when needed | | under $0.20 |
| **Total** | | **about $3–4 a run, $13–17 a month**, within the $20 budget |

With these costs the audio cap can rise from 15 to 25 hours a week. Gemini (from Monday) adds YouTube-only videos at about $0.10 an hour, or free.
