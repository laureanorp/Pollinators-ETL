import pandas as pd
import pytest

from ETL_mockup import round_milliseconds, truncate_milliseconds


# TODO add 0.500 ms order 0.501
# Sample dataset with timestamps, then converted to datetime object

@pytest.fixture
def df_round_truncate_ms() -> pd.DataFrame:
    df = pd.DataFrame({'time': ["01/01/2020 00:00:01.600", "01/01/2020 00:00:02.000", "01/01/2020 00:00:03.499"]})
    df['time'] = pd.to_datetime(df['time'], format="%d/%m/%Y %H:%M:%S.%f")
    return df


# TODO rename this
DF_ROUNDED_MS = [pd.Timestamp('2020-01-01 00:00:02'),
                 pd.Timestamp('2020-01-01 00:00:02'),
                 pd.Timestamp('2020-01-01 00:00:03')]

DF_TRUNCATED_MS = [pd.Timestamp('2020-01-01 00:00:01'),
                   pd.Timestamp('2020-01-01 00:00:02'),
                   pd.Timestamp('2020-01-01 00:00:03')]


# TODO add docstring
def test_round_milliseconds(df_round_truncate_ms: pd.DataFrame):
    """

    :param df_round_truncate_ms:
    :return:
    """
    round_milliseconds(df_round_truncate_ms, "time")
    assert df_round_truncate_ms["time"].tolist() == DF_ROUNDED_MS


def test_truncate_milliseconds(df_round_truncate_ms):
    truncate_milliseconds(df_round_truncate_ms, "time")
    assert df_round_truncate_ms["time"].tolist() == DF_TRUNCATED_MS
