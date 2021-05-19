from typing import Dict

import pandas as pd
import pytest

from pollinators_ETL import Pipeline


@pytest.fixture
def df_round_truncate_ms() -> pd.DataFrame:
    """ Sample dataset with timestamps converted to pandas datetime objects """
    df = pd.DataFrame({'time': ["01/01/2020 00:00:00.000", "01/01/2020 00:00:00.499", "01/01/2020 00:00:00.500",
                                "01/01/2020 00:00:01.501", "01/01/2020 00:00:02.000", "01/01/2020 00:00:03.499"]})
    df['time'] = pd.to_datetime(df['time'], format="%d/%m/%Y %H:%M:%S.%f")
    return df


@pytest.fixture
def dict_of_dataframes() -> Dict[str, pd.DataFrame]:
    """ Sample dictionary with three dataframes used to test _list_of_tags_with_all_antennas_visited() """
    df_1 = pd.DataFrame({'DEC Tag ID': ["0001", "0002", "0004", "0005", "0006"]})
    df_2 = pd.DataFrame({'DEC Tag ID': ["0001", "0002", "0002", "0002", "0006"]})
    df_3 = pd.DataFrame({'DEC Tag ID': ["0001", "0003", "0003", "0003", "0006"]})
    dict_of_dfs = {"df_1": df_1, "df_2": df_2, "df_3": df_3}
    return dict_of_dfs


TAG_IDS_IN_ALL_DATAFRAMES = {"0001", "0006"}

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
    pipeline_for_testing = Pipeline("imports/test_csv.csv")
    pipeline_for_testing._round_milliseconds("time", df_round_truncate_ms)
    assert df_round_truncate_ms["time"].tolist() == ROUNDED_MILLISECONDS


def test_truncate_milliseconds(df_round_truncate_ms: pd.DataFrame):
    """ Tests if milliseconds are being truncated correctly """
    pipeline_for_testing = Pipeline("imports/test_csv.csv")
    pipeline_for_testing._truncate_milliseconds("time", df_round_truncate_ms)
    assert df_round_truncate_ms["time"].tolist() == TRUNCATED_MILLISECONDS


def test__list_of_tags_with_all_antennas_visited(dict_of_dataframes):
    pipeline_for_testing = Pipeline("imports/test_csv.csv")
    df = pd.concat(dict_of_dataframes.values())
    all_tag_ids = df['DEC Tag ID'].unique().tolist()
    antennas_required = ["df_1", "df_2", "df_3"]
    pipeline_for_testing.antennas_dfs = dict_of_dataframes
    assert pipeline_for_testing._obtain_good_visitors(all_tag_ids,
                                                      antennas_required) == TAG_IDS_IN_ALL_DATAFRAMES
