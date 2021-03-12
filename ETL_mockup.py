
import pandas as pd
import numpy as np
from time import time


# Import CSV data
def read_data(path_to_csv):
    return pd.read_csv(path_to_csv, sep=";")


# Remove unused columns (at least for now)
def delete_unused_columns(data_frame):
    return data_frame.drop(columns=['Download Date', 'Download Time', 'Reader ID', 'HEX Tag ID',
                                    'Temperature,C','Signal,mV', 'Is Duplicate'])


# Round milliseconds to seconds (OPTION 1)
def round_milliseconds(data_frame, column):
    data_frame[column] = data_frame[column].dt.round('1s')


# Truncate milliseconds (OPTION 2)
def truncate_milliseconds(data_frame, column):
    data_frame[column] = data_frame[column].astype('datetime64[s]')


# Remove duplicate rows
def remove_duplicates(data_frame):
    return data_frame.drop_duplicates()


# Create a list with "n" dataframes, being "n" the number of different antennas on the data
def create_antennas_dfs(data_frame):
    antennas_ids = sorted(data_frame['Antenna ID'].unique().tolist())
    antennas_data_frames = []
    for antenna_number in antennas_ids:
        antenna_data_frame = data_frame['Antenna ID'] == antenna_number
        antennas_data_frames.append(data_frame[antenna_data_frame])
    return antennas_data_frames


# Tracking some time to study performance
start_time = time()

# Create pandas df
df = read_data("data/Rawdata_enero.csv")

# Delete unused columns
df = delete_unused_columns(df)

# Create dataframes for each antenna
antennas_dfs = create_antennas_dfs(df)

# For now, WE WILL WORK JUST ON DATAFRAME "ANTENNA 1":
antenna_1 = antennas_dfs[0]

# PERFORMANCE IMPROVEMENT TESTS
# Parse scan dates and times manually after reading the CSV
antenna_1['Scan Date and Time'] = pd.to_datetime(antenna_1['Scan Date'] + ' ' +
                                                 antenna_1['Scan Time'], format="%d/%m/%Y %H:%M:%S.%f")

# Remove milliseconds by rounding
round_milliseconds(antenna_1, "Scan Date and Time")

# Or... remove milliseconds truncating
# truncate_milliseconds(antenna_1, "Scan Date and Time")

# Remove unused columns before removing duplicates!
antenna_1 = antenna_1.drop(columns=['Scan Date', 'Scan Time'])

# Remove duplicates
antenna_1 = remove_duplicates(antenna_1)

# Sort using DEC tag ID so the time delta is correctly calculated
antenna_1 = antenna_1.sort_values(by=['DEC Tag ID', 'Scan Date and Time'])

# Calculate time delta by subtracting "Scan Time" rows
antenna_1['Time Delta'] = (antenna_1['Scan Date and Time'] -
                           antenna_1['Scan Date and Time'].shift(1)).astype('timedelta64[s]')

# TODO Calculate visit duration
# Right now this only returns the time delta if is a valid visit, the sum has to be done
min_visit_time = 7  # 7 seconds, arbitrary value

antenna_1['Visit Duration'] = np.where((antenna_1['Time Delta'] <= min_visit_time) &
                                       (antenna_1['DEC Tag ID'] == antenna_1['DEC Tag ID'].shift(1)),
                                       antenna_1['Time Delta'], 0)


# Reorder the columns
antenna_1 = antenna_1[['DEC Tag ID', 'Scan Date and Time', 'Time Delta', 'Visit Duration', 'Antenna ID']]

# Print the dataframe and the dtypes of each column
print(df.dtypes)
print(df)
print(antenna_1.dtypes)
print(antenna_1)

# Some executing times
end_time = time()
print(end_time - start_time)
