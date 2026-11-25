"""Building blocks for signals. Nothing in hub/signals touches the network:
every function works on the history store (through a View) and the config."""
import dataclasses

import pandas as pd

G, A, R = "green", "amber", "red"
WORD = {G: "Supports", A: "Neutral", R: "Against", None: "No data"}


@dataclasses.dataclass
class Raw:
    """What a dial calculation returns, before the no-flapping rule is applied."""
    value: float = None        # the main number (None = no data)
    colour: str = None         # green / amber / red, or None when it cannot be judged
    text: str = "no data"      # the reading as shown under the dial
    moves: str = ""            # one plain sentence on what would move it
    obs: object = None         # date of the newest data used
    gauge: dict = None         # {"min":, "max":, "bands": [[from, to, colour], ...]}
    extra: dict = dataclasses.field(default_factory=dict)


class View:
    """Read-only window on the store as it was known at `now`.

    asof=False (live runs): everything recorded so far is visible.
    asof=True (replays and bot tests): only what was known at `now` is visible.
    live: {series id: {"value":, "time":}} values still moving today (never stored).
    """

    def __init__(self, store, registry, now, live=None, asof=False, cache=None, blackout=None):
        self.blackout = blackout or {}   # {series id: date}; replays hide a series before that date
        self.store, self.now, self.asof = store, pd.Timestamp(now).tz_localize(None) if pd.Timestamp(now).tzinfo else pd.Timestamp(now), asof
        self.lag = {e["id"]: e.get("lag_days", 0) for e in registry["series"]}
        self.livevals = live or {}
        self._cache = cache if cache is not None else {}
        self._s = {}

    def s(self, sid):
        """History of one series (finished periods only)."""
        if sid in self._s:
            return self._s[sid]
        if sid in self.blackout and self.now < pd.Timestamp(self.blackout[sid]):
            self._s[sid] = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
            return self._s[sid]
        if not self.asof:
            out = self.store.series(sid)
            out = out[out.index <= self.now]
        else:
            if sid not in self._cache:
                self._cache[sid] = self.store.known_at(sid, self.lag.get(sid, 0))
            val, known, revised = self._cache[sid]
            out = self.store.series(sid, asof=self.now, lag_days=self.lag.get(sid, 0)) if revised else val[known <= self.now]
        self._s[sid] = out
        return out

    def live(self, sid):
        x = self.livevals.get(sid)
        return float(x["value"]) if x and x.get("value") is not None else None

    def latest(self, sid):
        """Live value if there is one, otherwise the last finished value. Returns (value, date) or (None, None)."""
        lv = self.live(sid)
        if lv is not None:
            return lv, self.now.normalize()
        s = self.s(sid)
        return (float(s.iloc[-1]), s.index[-1]) if len(s) else (None, None)

    def with_live(self, sid):
        """History plus today's live value as a final point."""
        s = self.s(sid)
        lv = self.live(sid)
        if lv is not None:
            s = s.copy()
            s.loc[self.now.normalize()] = lv
        return s


def band(x, edges, colours, prev=None, buf=0.0, rel=False, right=True):
    """Which colour zone a value falls in.

    edges ascending; colours has one more entry than edges.
    right: True means a value exactly on an edge belongs to the lower zone
           ("at or below"); False means the upper zone. May be a list, one per edge.
    prev/buf: buffer against flapping. If the dial already has colour `prev`, the
           value must be `buf` beyond that zone's edge (a fraction of the edge when
           rel=True) before the colour changes.
    """
    if x is None or pd.isna(x):
        return None
    rights = right if isinstance(right, (list, tuple)) else [right] * len(edges)

    def zone(v):
        for i, e in enumerate(edges):
            on_edge = abs(v - e) <= 1e-9 * max(1.0, abs(e))  # ignore rounding noise in the arithmetic
            if (v < e and not on_edge) or (rights[i] and on_edge):
                return i
        return len(edges)

    z = zone(x)
    if prev in colours and buf and colours[z] != prev:
        for p in [i for i, c in enumerate(colours) if c == prev]:
            lo = edges[p - 1] if p > 0 else None
            hi = edges[p] if p < len(edges) else None
            lo_b = None if lo is None else (lo * (1 - buf) if rel else lo - buf)
            hi_b = None if hi is None else (hi * (1 + buf) if rel else hi + buf)
            if (lo_b is None or x >= lo_b) and (hi_b is None or x <= hi_b):
                return prev
    return colours[z]


def gauge(lo, hi, edges, colours):
    pts = [lo] + [min(max(e, lo), hi) for e in edges] + [hi]
    return {"min": lo, "max": hi, "bands": [[pts[i], pts[i + 1], colours[i]] for i in range(len(colours))]}


def change(s, n):
    """Latest value minus the value n observations earlier."""
    return float(s.iloc[-1] - s.iloc[-1 - n]) if len(s) > n else None


def value_days_ago(s, days):
    """Value in force `days` calendar days before the last observation."""
    if not len(s):
        return None
    cut = s[s.index <= s.index[-1] - pd.Timedelta(days=days)]
    return float(cut.iloc[-1]) if len(cut) else None


def pct_change_days(s, days):
    old = value_days_ago(s, days)
    return None if old in (None, 0) else float(s.iloc[-1] / old - 1)


def percentile_of_last(s):
    """Share of all values (including the last) that are at or below the last one, 0-100."""
    return float((s <= s.iloc[-1]).mean() * 100) if len(s) else None


def weekly_closes(daily):
    """Bitcoin weekly close: the daily candle that ends Sunday 24:00 UTC (its date is the Sunday)."""
    return daily[daily.index.dayofweek == 6]


def finished_month_ends(daily):
    """Month-end closes of finished months only. A month counts as finished only
    once data exists for a later month."""
    if not len(daily):
        return daily
    m = daily.groupby(daily.index.to_period("M")).last()
    return m[m.index < daily.index[-1].to_period("M")]


def level_state(s, level, margin, n, lookback=750):
    """True when the series is 'below' the level, False when 'above'.

    The state flips only after n observations in a row at least `margin` beyond
    the level. Returns (below_now, number of flips to below, date of last flip to below).
    """
    s = s.iloc[-lookback:]
    if not len(s):
        return None, 0, None
    below = bool(s.iloc[0] < level)
    up = down = flips = 0
    last = None
    for d, x in s.items():
        if x >= level + margin - 1e-9:
            up, down = up + 1, 0
        elif x <= level - margin + 1e-9:
            down, up = down + 1, 0
        else:
            up = down = 0
        if up >= n and below:
            below = False
        if down >= n and not below:
            below, flips, last = True, flips + 1, d
    return below, flips, last


def weekly_state(weekly, brk, reclaim):
    """(break in force, date of the reclaim that ended the last break or None).
    brk and reclaim are numbers, or Series giving the level in force on each date."""
    def at(level, d):
        if not isinstance(level, pd.Series):
            return level
        cut = level[level.index <= d]
        return float(cut.iloc[-1]) if len(cut) else None
    in_break, when = False, None
    for d, x in weekly.items():
        b, r = at(brk, d), at(reclaim, d)
        if b is None or r is None:
            continue
        if x < b:
            in_break, when = True, None
        elif x > r and in_break:
            in_break, when = False, d
    return in_break, when


def dxy_from_ecb(usd, jpy, gbp, cad, sek, chf):
    """ICE dollar index formula from ECB rates quoted per one euro."""
    return (50.14348112 * usd ** -0.576 * (jpy / usd) ** 0.136 * (usd / gbp) ** -0.119
            * (cad / usd) ** 0.091 * (sek / usd) ** 0.042 * (chf / usd) ** 0.036)


def money(x, digits=0):
    return "n/a" if x is None else f"${x:,.{digits}f}"


def bn(x, digits=1):
    return "n/a" if x is None else f"${x:,.{digits}f}bn"


def ordinal(n):
    """51 -> '51st', 98 -> '98th'."""
    n = int(round(n))
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
