import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from time import time


MINIMUM_VISIT_TIME = 7  # 7 seconds, arbitrary value


# Import CSV data
def read_data(path_to_csv):
    return pd.read_csv(path_to_csv, sep=";")


# Remove unused columns (at least for now)
def delete_unused_columns(data_frame, columns_to_delete):
    return data_frame.drop(columns=columns_to_delete)


# Round milliseconds to seconds (OPTION 1)
def round_milliseconds(data_frame, column):
    data_frame[column] = data_frame[column].dt.round('1s')


# Truncate milliseconds (OPTION 2)
def truncate_milliseconds(data_frame, column):
    data_frame[column] = data_frame[column].astype('datetime64[s]')


# Remove duplicate rows
def remove_duplicates(data_frame):
    return data_frame.drop_duplicates()


# Create a dictionary with "n" dataframes, being "n" the number of different antennas on the data
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
def apply_to_all_antennas_dfs(dict_of_dataframes):

    # TODO fix "copy of a slice" error without using df.copy() to avoid memory peaks

    for antenna_key, antenna_df in dict_of_dataframes.items():
        # Parse scan dates and times manually after reading the CSV
        antenna_df['Scan Date and Time'] = pd.to_datetime(antenna_df['Scan Date'] + ' ' +
                                                          antenna_df['Scan Time'], format="%d/%m/%Y %H:%M:%S.%f")

        if round_or_truncate == 1:
            # Remove milliseconds by rounding
            round_milliseconds(antenna_df, "Scan Date and Time")
        elif round_or_truncate == 2:
            # Remove milliseconds truncating
            truncate_milliseconds(antenna_df, "Scan Date and Time")

        # Filter all data by date (start and end)
        if filter_start_datetime != "" and filter_end_datetime != "":
            antenna_df = antenna_df[(antenna_df["Scan Date and Time"] >= filter_start_datetime) &
                                    (antenna_df["Scan Date and Time"] <= filter_end_datetime)]

        # Remove unused columns before removing duplicates!
        antenna_df = antenna_df.drop(columns=['Scan Date', 'Scan Time'])

        # Remove duplicates
        antenna_df = remove_duplicates(antenna_df)

        # Sort using DEC tag ID so the time delta is correctly calculated
        antenna_df = antenna_df.sort_values(by=['DEC Tag ID', 'Scan Date and Time'])

        # Calculate time delta by subtracting "Scan Time" rows
        antenna_df['Time Delta'] = (antenna_df['Scan Date and Time'] -
                                    antenna_df['Scan Date and Time'].shift(1)).astype('timedelta64[s]')

        # Calculate which individual visits are valid and their durations
        # It has to be the same Tag ID and a visit between 1 and 7 seconds
        min_visit_time = MINIMUM_VISIT_TIME

        antenna_df['Valid Visits'] = 0
        antenna_df['Valid Visits'] = np.where((antenna_df['Time Delta'] > 0) &
                                              (antenna_df['Time Delta'] <= min_visit_time) &
                                              (antenna_df['DEC Tag ID'] == antenna_df['DEC Tag ID'].shift(1)),
                                              antenna_df['Time Delta'], 0)

        # Stopper: 1 when the running summation has to stop
        antenna_df['Visit Stopper'] = np.where(antenna_df['Valid Visits'] == 0, 1, 0)

        # Sum the duration of the individual visits to find the total
        sum_duration = antenna_df.groupby(antenna_df['Visit Stopper'].shift(fill_value=0)
                                          .cumsum())['Valid Visits'].transform('sum')
        antenna_df['Visit Duration'] = np.where(antenna_df['Visit Stopper'] == 1, sum_duration, 0)
        # Shift up al rows so the visit duration is in line with the correct Tag ID
        antenna_df['Visit Duration'] = antenna_df['Visit Duration'].shift(-1)

        # Reorder the columns
        # antenna_df = antenna_df[['DEC Tag ID', 'Scan Date and Time', 'Time Delta', 'Visit Duration', 'Antenna ID']]

        antennas_dfs[antenna_key] = antenna_df

    return antennas_dfs


# Quick plot just for fun
# Average duration of the visits for each antenna
def average_plot():
    list_of_means = []
    for antenna_key, antenna_df in antennas_dfs.items():
        no_null = antenna_df[antenna_df["Visit Duration"] != 0]
        list_of_means.append(no_null["Visit Duration"].mean())
    plt.figure()
    plt.bar(['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8'], list_of_means)
    plt.title("Average visit duration for each antenna")
    plt.xlabel("Antennas")
    plt.ylabel("Seconds")
    plt.show()


# Input variables that will be frontend UI elements (textbox, checkboxes, etc)
# Default values are here temporary, should be default values in each function or other workarounds
filter_start_datetime = input("Start date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                              "\nLeave this input blank if you don't want to filter by date: ")
filter_end_datetime = input("End date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                            "\nLeave this input blank if you don't want to filter by date: ")
round_or_truncate = input("Choose to round (1, default), truncate (2) or leave (3) ms of the timestamps: ") or "1"

# Tracking some time to study performance
start_time = time()

# Create pandas df
df = read_data("data/Rawdata_enero.csv")

# Delete unused columns
df = delete_unused_columns(df, ['Download Date', 'Download Time', 'Reader ID', 'HEX Tag ID',
                                'Temperature,C', 'Signal,mV', 'Is Duplicate'])

# Create a list of unique Tag IDs to use in other functions
all_tag_ids = df['DEC Tag ID'].unique().tolist()

# Create dataframes for each antenna
antennas_dfs = create_antennas_dfs_new(df)


# Creates a list with only the Tag IDs that have visited all antennas. Warning, this code is a bit hacky
def create_list_of_good_visitors(tag_id_list, dict_of_dataframes):
    good_visitors = set([])
    for tag_id in tag_id_list:
        visitor_in_df = []
        for antenna_key, antenna_df in dict_of_dataframes.items():
            visitor_in_df.append(tag_id in antenna_df["DEC Tag ID"].values)  # True/False if in df
        if all(visitor_in_df):  # if all elements are True, is a "good" visitor
            good_visitors.add(tag_id)
    return good_visitors


print(len(create_list_of_good_visitors(all_tag_ids, antennas_dfs)))
print(create_list_of_good_visitors(all_tag_ids, antennas_dfs))


# Apply all the necessary functions to the antennas data frames
antennas_dfs = apply_to_all_antennas_dfs(antennas_dfs)

# Print the main dataframe
# print(df)
# Print the first antenna_df
print(antennas_dfs["antenna_1"])

# Some executing times
end_time = time()
print(end_time - start_time)
