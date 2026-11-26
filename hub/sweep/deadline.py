"""Working out a call's deadline from the words used ("next year", "by end of 2027", "in three months")
and the date the call was made. The code does this, not the model: in the source test the model dated
"S&P 500 up 15% next year" (said in Nov 2026) to Dec 2026, and gave two calls the episode's own date."""
import calendar
import datetime as dt
import re

WORDS = {"one": 1, "a": 1, "an": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "eighteen": 18, "twenty-four": 24}
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})


def month_end(y, m):
    return dt.date(y, m, calendar.monthrange(y, m)[1])


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def from_words(text, said):
    """Deadline from plain words, or None when the words give no clear date."""
    t = (text or "").lower().replace("’", "'")
    y = said.year
    m = re.search(r"\b(?:end of |by |before |in )?(?:q([1-4])|([1-4])q)\s*(?:of\s*)?'?(\d{2,4})\b", t)
    if m:
        q = int(m.group(1) or m.group(2))
        yy = int(m.group(3))
        yy = yy + 2000 if yy < 100 else yy
        return month_end(yy, q * 3)
    m = re.search(r"\b(" + "|".join(MONTHS) + r")\.? (\d{4})\b", t)
    if m:
        return month_end(int(m.group(2)), MONTHS[m.group(1)])
    m = re.search(r"\b(?:end of |by |before |in |during |through )?(20\d{2})\b", t)
    if m:
        return dt.date(int(m.group(1)), 12, 31)
    m = re.search(r"\b(?:in|within|over|next|the next|in the next)\s+(\d+|" + "|".join(WORDS) + r")\s+(day|week|month|year)s?\b", t)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else WORDS[m.group(1)]
        unit = m.group(2)
        if unit == "day":
            return said + dt.timedelta(days=n)
        if unit == "week":
            return said + dt.timedelta(weeks=n)
        return add_months(said, n * (12 if unit == "year" else 1))
    if re.search(r"\bnext year\b", t):
        return dt.date(y + 1, 12, 31)
    if re.search(r"\b(this year|year[- ]end|end of the year|by the end of this year)\b", t):
        return dt.date(y, 12, 31)
    if re.search(r"\bnext month\b", t):
        nm = add_months(said, 1)
        return month_end(nm.year, nm.month)
    if re.search(r"\bnext week\b", t):
        return said + dt.timedelta(days=7)
    if re.search(r"\bnext quarter\b", t):
        q = (said.month - 1) // 3 + 2
        yy = y + (q - 1) // 4
        q = (q - 1) % 4 + 1
        return month_end(yy, q * 3)
    return None


def resolve(horizon, model_by, said):
    """The deadline to keep, or None (then the call is dropped).
    Words win over the model's date; either way the deadline must be after the day the call was made."""
    d = from_words(horizon, said)
    if d is None and model_by:
        try:
            d = dt.date.fromisoformat(str(model_by)[:10])
        except ValueError:
            d = None
    if d is None or d <= said:
        return None
    return d
