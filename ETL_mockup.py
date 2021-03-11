
import pandas as pd


# Import CSV data
def read_data(path_to_csv):
    return pd.read_csv(path_to_csv, parse_dates=[['Scan Date', 'Scan Time']], sep=';')


# Remove unused columns (at least for now)
def delete_unused_columns(df):
    return df.drop(columns=['Download Date', 'Download Time', 'Reader ID', 'HEX Tag ID', 'Temperature,C','Signal,mV', 'Is Duplicate'])


# Remove date of datetime objects with an incorrect date
# Note: As a consequence, it becomes an object instead of datetime64[ns]
def remove_date_from_datetime(column):
    df[column] = pd.to_datetime(df[column], format='%H:%M:%S').dt.time


# Round milliseconds to seconds (OPTION 1)
def round_milliseconds(column):
    df[column] = df[column].dt.round('1s')


# Truncate milliseconds (OPTION 2)
def truncate_milliseconds(column):
    df[column] = df[column].astype('datetime64[s]')


# Remove duplicate rows
def remove_duplicates(df):
    return df.drop_duplicates()


# Create a list with "n" dataframes, being "n" the number of different antennas on the data
def create_antennas_dfs(df):
    antennas_ids = sorted(df['Antenna ID'].unique().tolist())
    antennas_dfs = []
    for antenna_number in antennas_ids:
        antenna_df = df['Antenna ID'] == antenna_number
        antennas_dfs.append(df[antenna_df])
    return antennas_dfs


# Create pandas df
df = read_data("data/Rawdata_enero.csv")

# Delete unused columns
df = delete_unused_columns(df)

# Remove milliseconds by rounding
round_milliseconds("Scan Date_Scan Time")

# Or... remove milliseconds truncating
# truncate_milliseconds("Scan Time")

# Remove fake date from some datetime columns
# remove_date_from_datetime("Scan Time")

# Remove duplicates
df = remove_duplicates(df)

# Create dataframes for each antenna
antennas_dfs = create_antennas_dfs(df)

# For now, JUST DATAFRAME ANTENNA 1:
# Create time delta by subtracting "Scan Time" rows
antennas_dfs[0]['Time Delta (s)'] = (antennas_dfs[0]['Scan Date_Scan Time'] - antennas_dfs[0]['Scan Date_Scan Time'].shift(1)).astype('timedelta64[s]')

# Reorder the columns
antennas_dfs[0] = antennas_dfs[0][['Scan Date_Scan Time', 'Time Delta (s)', 'Antenna ID', 'DEC Tag ID']]

# Print the dataframe and the dtypes of each column
print(df.dtypes)
print(df)
print(antennas_dfs[0])
