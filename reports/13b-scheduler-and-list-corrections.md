# Point 13b: the 15-minute schedule, and corrections to the people list

Date: 26 November 2026.

## The hub's schedule was not firing

- **What I found:** the Hub run workflow is switched on ("active"), but GitHub's timer started it only twice in about 20 hours: 22:27 UTC on 25 Nov and 04:20 UTC on 26 Nov. Every other run in that period was started by a change being published, not by the timer. Nothing was broken in the hub itself. GitHub's timer is "best effort", and this repository is being starved of it.
- **Run started by hand:** 07:40 UTC (15:40 Hong Kong time), run 45777096753. Both jobs succeeded: the run job finished 07:41:24 and publishing 07:41:38. History was saved to the data branch at 07:41:19 UTC, so the dashboard is fresh as of then.
- **Fix:** an outside scheduler (cron-job.org) starts the hub every 15 minutes through GitHub's API, using a fine-grained token limited to Actions on `lde1988/macro-hub`. GitHub's timer stays on as a backup, and so does the watchdog. The step-by-step setup is in the README on `main` under "Outside scheduler". Waiting for the owner to create the token and the cron job; nothing can be tested until then.

### Permissions to tick on the token

| Setting | Choice |
|---|---|
| Resource owner | lde1988 |
| Repository access | Only select repositories → lde1988/macro-hub |
| Repository permissions → **Actions** | **Read and write** |
| Repository permissions → Metadata | Read-only (added automatically; required) |
| Everything else, and all account permissions | No access |

## Owner's corrections to the people list (approved, with these changes)

| Person | Change | Checked |
|---|---|---|
| Kevin Follonier | Confirmed: @KevinWSHPod, host of When Shift Happens | Yes (point 13) |
| Mikkel Rosenvold | Add X **@RosenvoldGeo** | **Confirmed** on 26 Nov: display name "Mikkel Rosenvold", bio "Geopolitical Analyst @RealVision", five posts on 25 Nov on Iran, Ukraine and markets |
| Stan Druckenmiller | Add X **@standuquesne**; interview search stays his main source | See below |
| Balancing voices | Keep all three: Odd Lots, Paul Kedrosky, Dan Rasmussen | |

### Is @standuquesne genuinely Druckenmiller?

The owner asked for checks on verification, account age, and links to Duquesne or interviews that cite the account.

- **Display name:** "Stan Druckenmiller".
- **Content matches his widely reported post:** its post of 6 April 2025, "I do not support tariffs exceeding 10% which I made abundantly clear in the interview you cite", is the X post that CNBC/NBC, Fortune, Benzinga and others reported as his, a reply to a clip of his January 2025 CNBC interview. Coverage at the time said he had made only about two dozen posts, which fits.
- **Other posts are in keeping with him:**
  - 13 Oct 2025: "Duquesne had zero position at the time of the Treasury intervention".
  - 29 Oct 2026: he says he is an investor in trade(xyz).
- **Not established:**
  - The verification badge, the account's creation date and the profile link: xAI's search tool does not report them, and x.com cannot be read from here.
  - Posts by other accounts that name the handle itself: xAI's search found none.

**Verdict: included, with the evidence above.** The content match with a post that the press attributed to him is strong. The badge and account age remain unchecked. The owner can look at the profile on a phone in a few seconds: a badge, a join date before 2025, and the tariff reply are the three things to look for. Expect few posts. Interviews stay his main source.

### Two handles that now fail

xAI reported both **@alive_eth** (Ali Yahya) and **@0xMert_** (Mert Mumtaz) as "account cannot be found".

- Yahya left a16z in October 2026, and the account may have been renamed or closed.
- For Mumtaz, two Stocktwits articles from June 2026 credit his posts to **@mert**. That is a lead, not a confirmation.

Both will be resolved in the source test, and neither will be guessed.

## Gemini (owner's decision)

- The owner will create `GEMINI_API_KEY` in the UK on Monday.
- The Gemini route for YouTube will be built now but stay switched off until that secret exists.
- Until then, podcast audio will be transcribed by Groq (paid, about $0.04 an audio hour), within the $20 monthly budget, and YouTube captions will be used where they work.

## Cost of checks so far

The xAI checks cost $0.20 (point 13) plus $0.22 (this point): **$0.42 in total**.
