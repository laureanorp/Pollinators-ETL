
from time import time

from pollinators_ETL import *


# Input variables that will be frontend UI elements (textbox, checkboxes, etc)
# Default values are here temporary, should be default values in each function or other workarounds
filter_start_datetime = input("Start date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                              "\nLeave this input blank if you don't want to filter by date: ")

filter_end_datetime = input("End date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                            "\nLeave this input blank if you don't want to filter by date: ")

round_or_truncate = input("Choose to round (1, default), truncate (2) or leave (3) ms of the timestamps: ") or "1"

all_antennas_visited = input("Choose to include all pollinators (1, default) or only those that have "
                             "visited all antennas of the experiment (2): ") or "1"

# Tracking some time to study performance
start_time = time()

# Create pandas df
df = csv_to_dataframe("data/Rawdata_enero.csv")

# Delete unused columns
df = delete_unused_columns(df, ['Download Date', 'Download Time', 'Reader ID', 'HEX Tag ID',
                                'Temperature,C', 'Signal,mV', 'Is Duplicate'])

# Create a list of unique Tag IDs to use in other functions
all_tag_ids = df['DEC Tag ID'].unique().tolist()

# Create dataframes for each antenna
antennas_dfs = create_dict_of_antennas_dfs(df)

# Create list of good visitors (Tag IDs with all antennas are visited)
list_of_good_visitors = list_of_tags_with_all_antennas_visited(all_tag_ids, antennas_dfs)

# Apply all the necessary functions to the antennas data frames
antennas_dfs = apply_to_all_antennas_dfs(antennas_dfs, filter_start_datetime, filter_end_datetime, round_or_truncate, all_antennas_visited, list_of_good_visitors)

# Print the main dataframe
print(df)
# Print the first antenna_df
print(antennas_dfs["antenna_1"])

# Some executing times
end_time = time()
print(end_time - start_time)
