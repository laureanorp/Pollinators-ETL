
from ETL_mockup import *
from pandas import Timestamp

# Test round_ms()
# Sample dataset with timestamps, convert to datetime object
df = pd.DataFrame({'time': ["01/01/2020 00:00:01.600", "01/01/2020 00:00:02.000", "01/01/2020 00:00:03.499"]})
df['time'] = pd.to_datetime(df['time'], format="%d/%m/%Y %H:%M:%S.%f")

def test_round_ms():
    round_milliseconds(df, "time")
    assert df["time"].tolist() == [Timestamp('2020-01-01 00:00:02'), Timestamp('2020-01-01 00:00:02'), Timestamp('2020-01-01 00:00:03')]

def test_truncate_ms():
    truncate_milliseconds(df, "time")
    assert df["time"].tolist() == [Timestamp('2020-01-01 00:00:02'), Timestamp('2020-01-01 00:00:02'), Timestamp('2020-01-01 00:00:03')]