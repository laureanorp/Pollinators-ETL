import pandas as pd
import numpy as np
from time import time


# Import CSV data
def read_data(path_to_csv):
    return pd.read_csv(path_to_csv, sep=";")


# Remove unused columns (at least for now)
def delete_unused_columns(data_frame):
    return data_frame.drop(columns=['Download Date', 'Download Time', 'Reader ID', 'HEX Tag ID',
                                    'Temperature,C', 'Signal,mV', 'Is Duplicate'])


# Round milliseconds to seconds (OPTION 1)
def round_milliseconds(data_frame, column):
    data_frame[column] = data_frame[column].dt.round('1s')


# Truncate milliseconds (OPTION 2)
def truncate_milliseconds(data_frame, column):
    data_frame[column] = data_frame[column].astype('datetime64[s]')


# Remove duplicate rows
def remove_duplicates(data_frame):
    return data_frame.drop_duplicates()


# Create a dict with "n" dataframes, being "n" the number of different antennas on the data
def create_antennas_dfs_new(data_frame):
    antennas_ids = sorted(data_frame['Antenna ID'].unique().tolist())
    antennas_data_frames = {}
    for antenna_number in antennas_ids:
        antenna_data_frame = data_frame['Antenna ID'] == antenna_number
        key_name = "antenna_" + str(antenna_number)
        antennas_data_frames[key_name] = data_frame[antenna_data_frame]
    return antennas_data_frames


# apply all the different functions to each antenna data frame
# Arguments like "round" or "truncate" will be passed to choose from future options
def apply_to_antennas_dfs(dict_of_dataframes):
    
    # TODO fix "copy of a slice" error without using df.copy() to avoid memory peaks

    for antenna_key, antenna_df in dict_of_dataframes.items():
        # Parse scan dates and times manually after reading the CSV
        antenna_df['Scan Date and Time'] = pd.to_datetime(antenna_df['Scan Date'] + ' ' +
                                                          antenna_df['Scan Time'], format="%d/%m/%Y %H:%M:%S.%f")

        # Remove milliseconds by rounding
        round_milliseconds(antenna_df, "Scan Date and Time")

        # Or remove milliseconds truncating
        # truncate_milliseconds(antenna_df, "Scan Date and Time")

        # Remove unused columns before removing duplicates!
        antenna_df = antenna_df.drop(columns=['Scan Date', 'Scan Time'])

        # Remove duplicates
        antenna_df = remove_duplicates(antenna_df)

        # Sort using DEC tag ID so the time delta is correctly calculated
        antenna_df = antenna_df.sort_values(by=['DEC Tag ID', 'Scan Date and Time'])

        # Calculate time delta by subtracting "Scan Time" rows
        antenna_df['Time Delta'] = (antenna_df['Scan Date and Time'] -
                                    antenna_df['Scan Date and Time'].shift(1)).astype('timedelta64[s]')

        # TODO - Calculate visit duration
        # Right now this only returns the time delta if is a valid visit, the sum has to be done
        min_visit_time = 7  # 7 seconds, arbitrary value

        antenna_df['Visit Duration'] = np.where((antenna_df['Time Delta'] <= min_visit_time) &
                                                (antenna_df['DEC Tag ID'] == antenna_df['DEC Tag ID'].shift(1)),
                                                antenna_df['Time Delta'], 0)

        # Reorder the columns
        antenna_df = antenna_df[['DEC Tag ID', 'Scan Date and Time', 'Time Delta', 'Visit Duration', 'Antenna ID']]

        antennas_dfs[antenna_key] = antenna_df

    return antennas_dfs


# Tracking some time to study performance
start_time = time()

# Create pandas df
df = read_data("data/Rawdata_enero.csv")

# Delete unused columns
df = delete_unused_columns(df)

# Create dataframes for each antenna
antennas_dfs = create_antennas_dfs_new(df)

# Apply all the necessary functions to the antennas data frames
antennas_dfs = apply_to_antennas_dfs(antennas_dfs)

# Print the dataframe and the dtypes of each column
print(df.dtypes)
print(df)
print(antennas_dfs["antenna_1"].dtypes)
print(antennas_dfs["antenna_1"])

# Some executing times
end_time = time()
print(end_time - start_time)
