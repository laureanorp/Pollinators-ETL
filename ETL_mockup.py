
import pandas as pd
import numpy as np


# Import CSV data
def read_data(path_to_csv):
    return pd.read_csv(path_to_csv, parse_dates=[['Scan Date', 'Scan Time']], sep=';')


# Remove unused columns (at least for now)
def delete_unused_columns(df):
    return df.drop(columns=['Download Date', 'Download Time', 'Reader ID', 'HEX Tag ID',
                            'Temperature,C','Signal,mV', 'Is Duplicate'])


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

# For now, WE WILL WORK JUST ON DATAFRAME "ANTENNA 1":
antenna_1 = antennas_dfs[0]

# Sort using DEC tag ID so the time delta is correctly calculated
antenna_1 = antenna_1.sort_values(by=['DEC Tag ID', 'Scan Date_Scan Time'])

# Calculate time delta by subtracting "Scan Time" rows
antenna_1['Time Delta'] = (antenna_1['Scan Date_Scan Time'] -
                           antenna_1['Scan Date_Scan Time'].shift(1)).astype('timedelta64[s]')

# TODO Calculate visit duration
# Right now this only returns the time delta if is a valid visit, the sum has to be done
min_visit_time = 7  # 7 seconds, arbitrary value

antenna_1['Visit Duration'] = np.where((antenna_1['Time Delta'] <= min_visit_time) &
                                       (antenna_1['DEC Tag ID'] == antenna_1['DEC Tag ID'].shift(1)),
                                       antenna_1['Time Delta'], 0)


# Reorder the columns
antenna_1 = antenna_1[['DEC Tag ID', 'Scan Date_Scan Time', 'Time Delta', 'Visit Duration', 'Antenna ID']]

# Print the dataframe and the dtypes of each column
print(df.dtypes)
print(df)
print(antenna_1.dtypes)
print(antenna_1)
