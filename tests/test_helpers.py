import numpy as np
import pandas as pd

from marketflows import _helpers


class TestFindFirstValidTime:
    def test_find_first_valid_time_success(self):
        df = pd.DataFrame()
        df.index = [
            pd.Timestamp("1970-01-01 00:00:00+0000", tz="UTC"),
            pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC"),
            pd.Timestamp("1970-01-01 00:10:00+0000", tz="UTC"),
        ]
        df["nvidia"] = [np.nan, 900, 1100]
        first_valid = _helpers.find_first_valid_time(df)
        assert first_valid == pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC")

    def test_find_first_valid_time_no_valid(self):
        df = pd.DataFrame()
        df.index = [
            pd.Timestamp("1970-01-01 00:00:00+0000", tz="UTC"),
            pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC"),
            pd.Timestamp("1970-01-01 00:10:00+0000", tz="UTC"),
        ]
        df["nvidia"] = [np.nan, np.nan, np.nan]
        df["amazon"] = [np.nan, np.nan, np.nan]
        first_valid = _helpers.find_first_valid_time(df)
        assert first_valid is None


class TestFindLastValidTime:
    def test_find_last_valid_time_success(self):
        df = pd.DataFrame()
        df.index = [
            pd.Timestamp("1970-01-01 00:00:00+0000", tz="UTC"),
            pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC"),
            pd.Timestamp("1970-01-01 00:10:00+0000", tz="UTC"),
        ]
        df["nvidia"] = [1100, 900, np.nan]
        last_valid = _helpers.find_last_valid_time(df)
        assert last_valid == pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC")

    def test_find_last_valid_time_no_valid(self):
        df = pd.DataFrame()
        df.index = [
            pd.Timestamp("1970-01-01 00:00:00+0000", tz="UTC"),
            pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC"),
            pd.Timestamp("1970-01-01 00:10:00+0000", tz="UTC"),
        ]
        df["nvidia"] = [np.nan, np.nan, np.nan]
        df["amazon"] = [np.nan, np.nan, np.nan]
        last_valid = _helpers.find_last_valid_time(df)
        assert last_valid is None
