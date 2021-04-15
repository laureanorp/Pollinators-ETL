import pandas as pd
import pytest

from pollinators_ETL import round_milliseconds, truncate_milliseconds


@pytest.fixture
def df_round_truncate_ms() -> pd.DataFrame:
    """ Sample dataset with timestamps converted to pandas datetime objects """
    df = pd.DataFrame({'time': ["01/01/2020 00:00:00.000", "01/01/2020 00:00:00.499", "01/01/2020 00:00:00.500",
                                "01/01/2020 00:00:01.501", "01/01/2020 00:00:02.000", "01/01/2020 00:00:03.499"]})
    df['time'] = pd.to_datetime(df['time'], format="%d/%m/%Y %H:%M:%S.%f")
    return df


ROUNDED_MILLISECONDS = [pd.Timestamp('2020-01-01 00:00:00'),
                        pd.Timestamp('2020-01-01 00:00:00'),
                        pd.Timestamp('2020-01-01 00:00:00'),
                        pd.Timestamp('2020-01-01 00:00:02'),
                        pd.Timestamp('2020-01-01 00:00:02'),
                        pd.Timestamp('2020-01-01 00:00:03')]

TRUNCATED_MILLISECONDS = [pd.Timestamp('2020-01-01 00:00:00'),
                          pd.Timestamp('2020-01-01 00:00:00'),
                          pd.Timestamp('2020-01-01 00:00:00'),
                          pd.Timestamp('2020-01-01 00:00:01'),
                          pd.Timestamp('2020-01-01 00:00:02'),
                          pd.Timestamp('2020-01-01 00:00:03')]


def test_round_milliseconds(df_round_truncate_ms: pd.DataFrame):
    """
    Tests if milliseconds are being rounded correctly
    Including extreme cases like 0.500ms
    """
    round_milliseconds(df_round_truncate_ms, "time")
    assert df_round_truncate_ms["time"].tolist() == ROUNDED_MILLISECONDS


def test_truncate_milliseconds(df_round_truncate_ms: pd.DataFrame):
    """ Tests if milliseconds are being truncated correctly """
    truncate_milliseconds(df_round_truncate_ms, "time")
    assert df_round_truncate_ms["time"].tolist() == TRUNCATED_MILLISECONDS
