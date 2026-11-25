# Point 5: test push

Date: 25 November 2026.

## What was done

- Built the ntfy sender (`hub/notify.py`). The topic name is treated as a secret: it travels in the request body, never in a web address, and neither the topic nor ntfy's reply is printed or stored. Four tests cover this with a fake sender.
- Sent one test push from a GitHub Actions runner using the `NTFY_TOPIC` secret.

## Result

- GitHub run "Test push": **success**, finished 09:30 UTC (17:30 Hong Kong time), run 45585964542.
- ntfy accepted the message (HTTP 200).
- Title: "macro-hub: test push". Text: "If you can read this on your iPhone, alerts are working. This is only a test: no market reading has changed." Priority 3 (normal).

## Waiting on

The owner to confirm the push arrived on the iPhone. "Accepted by ntfy" proves the sending side only; it does not prove the phone is subscribed to the same topic or that notifications are allowed.

## Also done at this stop (decisions from the point 4 review)

- Fresh-turn rule built: a group D dial counts toward "turn confirmed" and the TURN regime only within 13 weeks of turning green.
- Buybacks step-up restored to 1.5x.
- Replay levels: 1.10x realised price for the value zone; short-term holder realised price for the reclaim line; 0.96x it for the break line. Live dials show these beside the fixed levels.
- Tests: 252, all passing locally and on GitHub (run 45585964217).
- Figures requested are in `03-dial-bands.md` ("Turn confirmed under the fresh rule").
