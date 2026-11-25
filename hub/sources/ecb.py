"""ECB euro reference rates (one fixing per business day, about 14:15 Frankfurt time)."""
import xml.etree.ElementTree as ET

import pandas as pd

from hub.sources import Result

RECENT = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
FULL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
NS = "{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube"


def parse(xml_bytes):
    """Returns {currency: Series(date -> units per euro)}."""
    out = {}
    for day in ET.fromstring(xml_bytes).iter(NS):
        if "time" not in day.attrib:
            continue
        d = pd.Timestamp(day.attrib["time"])
        for c in day:
            try:
                out.setdefault(c.attrib["currency"], {})[d] = float(c.attrib["rate"])
            except (KeyError, ValueError):
                continue
    return {k: pd.Series(v, dtype=float).sort_index() for k, v in out.items()}


def fetch(entries, ctx):
    res = Result()
    lasts = [pd.Timestamp(ctx.last[e["id"]]) for e in entries if e["id"] in ctx.last]
    gap = (ctx.today - min(lasts)).days if len(lasts) == len(entries) and lasts else 9999
    # the short file holds 90 days; after a longer pause (or a first run) take the full file
    rates = parse(ctx.web.get(FULL if (ctx.backfill or gap > 80) else RECENT, timeout=120).content)
    for e in entries:
        if e["code"] in rates:
            s = rates[e["code"]]
            res.history[e["id"]] = s[s.index >= ctx.since(e, 120)]
        else:
            res.errors[e["id"]] = "currency missing from ECB file"
    return res
