"""History store rules, with made-up data."""
import pandas as pd

from hub.store import Store


def s(d):
    return pd.Series({pd.Timestamp(k): v for k, v in d.items()}, dtype=float)


def test_new_values_are_recorded_with_first_seen(tmp_path):
    st = Store(tmp_path)
    assert st.append("X", s({"2026-01-01": 1.0, "2026-01-02": 2.0}), "2026-01-03 10:00") == 2
    raw = st.raw("X")
    assert list(raw["value"]) == [1.0, 2.0]
    assert (raw["first_seen"] == pd.Timestamp("2026-01-03 10:00")).all()


def test_unchanged_values_add_nothing(tmp_path):
    st = Store(tmp_path)
    st.append("X", s({"2026-01-01": 1.0}), "2026-01-03")
    assert st.append("X", s({"2026-01-01": 1.0}), "2026-01-04") == 0
    assert len(st.raw("X")) == 1


def test_a_revision_is_appended_never_overwritten(tmp_path):
    st = Store(tmp_path)
    st.append("X", s({"2026-01-01": 1.0}), "2026-01-03")
    assert st.append("X", s({"2026-01-01": 1.5}), "2026-02-10") == 1
    assert list(st.raw("X")["value"]) == [1.0, 1.5]          # both kept
    assert st.series("X")[pd.Timestamp("2026-01-01")] == 1.5  # latest wins today


def test_point_in_time_shows_only_what_was_known_then(tmp_path):
    st = Store(tmp_path)
    st.append("X", s({"2026-01-01": 1.0}), "2026-01-03")
    st.append("X", s({"2026-01-01": 1.5, "2026-02-01": 9.0}), "2026-02-10")
    then = st.series("X", asof="2026-01-20")
    assert then[pd.Timestamp("2026-01-01")] == 1.0 and len(then) == 1
    assert len(st.series("X", asof="2026-01-02")) == 0       # not yet fetched
    assert st.series("X", asof="2026-02-10")[pd.Timestamp("2026-01-01")] == 1.5


def test_backfilled_rows_become_known_after_the_publication_lag(tmp_path):
    st = Store(tmp_path)
    st.append("X", s({"2020-03-31": 5.0}), "2026-11-25", backfill=True)
    assert len(st.series("X", asof="2020-04-10", lag_days=25)) == 0
    assert len(st.series("X", asof="2020-04-25", lag_days=25)) == 1


def test_once_a_day_snapshots_are_not_revised(tmp_path):
    st = Store(tmp_path)
    st.append("X", s({"2026-01-01": 1.0}), "2026-01-01 00:15", once=True)
    assert st.append("X", s({"2026-01-01": 1.2}), "2026-01-01 00:30", once=True) == 0


def test_saved_in_one_file_per_year_and_read_back(tmp_path):
    st = Store(tmp_path)
    st.append("X", s({"2025-12-31": 1.0, "2026-01-01": 2.0}), "2026-01-03 10:00")
    files = st.save()
    assert sorted(f.split("/")[-1] for f in files) == ["2025.csv", "2026.csv"]
    again = Store(tmp_path)
    assert list(again.series("X")) == [1.0, 2.0]
    assert again.raw("X")["first_seen"].iloc[0] == pd.Timestamp("2026-01-03 10:00")
    again.append("X", s({"2026-01-02": 3.0}), "2026-01-04")
    assert [f.split("/")[-1] for f in again.save()] == ["2026.csv"]   # only the year that changed is rewritten


def test_known_at_matches_point_in_time(tmp_path):
    st = Store(tmp_path)
    st.append("X", s({"2026-01-01": 1.0, "2026-01-02": 2.0}), "2026-11-25", backfill=True)
    val, known, revised = st.known_at("X", lag_days=1)
    assert not revised and known[pd.Timestamp("2026-01-02")] == pd.Timestamp("2026-01-03")
