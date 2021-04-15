
from typing import List, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MINIMUM_VISIT_TIME = 7  # 7 seconds, arbitrary value


class Pipeline:
    """ Class that includes all the functions of the ETL pipeline """

    def __init__(self, path_to_csv: str, min_visit_time: int):
        self.csv_path = path_to_csv
        self.min_visit_time = min_visit_time


    def run_pipeline(self):
        pass


def csv_to_dataframe(path_to_csv: str):
    """ Imports the CSV file containing all the data from BioMark """
    return pd.read_csv(path_to_csv, sep=";")


def list_of_tags_with_all_antennas_visited(tag_id_list: List[str], dict_of_dataframes: Dict[str, pd.DataFrame]):
    """
    Creates and returns a set that includes only those Tag IDs that have visited all antennas
    Takes the list of Tag IDs and the dict of antennas dataframes as arguments,
    and iterates over the Tag IDs list, checking if each Tag ID is present on every dataframe
    """
    good_visitors = set([])
    for tag_id in tag_id_list:
        visitor_in_df = []
        for antenna_key, antenna_df in dict_of_dataframes.items():
            visitor_in_df.append(tag_id in antenna_df["DEC Tag ID"].values)  # True/False if in df
        if all(visitor_in_df):  # if all elements are True, it's a "good" visitor
            good_visitors.add(tag_id)
    return good_visitors


def delete_unused_columns(data_frame: pd.DataFrame, columns_to_delete: list):
    """ Deletes columns that won't be used anywhere """
    return data_frame.drop(columns=columns_to_delete)


def round_milliseconds(data_frame: pd.DataFrame, column: str):
    """ Rounds milliseconds on the desired column """
    data_frame[column] = data_frame[column].dt.round('1s')


def truncate_milliseconds(data_frame: pd.DataFrame, column: str):
    """ Truncates milliseconds on the desired column """
    data_frame[column] = data_frame[column].astype('datetime64[s]')


# Remove duplicate rows
def remove_duplicated_rows(data_frame: pd.DataFrame):
    """ Removes duplicated rows (where every column has the same value) """
    return data_frame.drop_duplicates()


def create_dict_of_antennas_dfs(data_frame: pd.DataFrame):
    """
    Create a dictionary with "n" dataframes, being "n" the number of different antennas on the data
    Each dataframe is named after the number of its antenna
    Structure of the returned dict is "antenna_n":pd.DataFrame
    """
    antennas_ids = sorted(data_frame['Antenna ID'].unique().tolist())
    antennas_data_frames = {}
    for antenna_number in antennas_ids:
        antenna_data_frame = data_frame['Antenna ID'] == antenna_number
        key_name = "antenna_" + str(antenna_number)
        antennas_data_frames[key_name] = data_frame[antenna_data_frame]
    return antennas_data_frames


def plot_avg_visit_duration(antennas_dfs: Dict[str, pd.DataFrame]):
    """
    Calculates the mean of no null visit durations for each antenna
    Then plots that average duration for each antenna using a bar plot
    """
    list_of_means = []
    for antenna_key, antenna_df in antennas_dfs.items():
        no_null = antenna_df[antenna_df["Visit Duration"] != 0]
        list_of_means.append(no_null["Visit Duration"].mean())
    plt.figure()
    plt.bar(antennas_dfs.keys(), list_of_means)
    plt.title("Average visit duration for each antenna")
    plt.xlabel("Antennas")
    plt.ylabel("Seconds")
    plt.xticks(rotation=45)
    plt.show()


def apply_to_all_antennas_dfs(dict_of_dataframes: Dict[str, pd.DataFrame], filter_start_datetime: str, filter_end_datetime: str, round_or_truncate: str, all_antennas_visited: str, list_of_good_visitors: List[str]):
    """
    Apply all the different functions to each antenna dataframe
    TODO Arguments like "round" or "truncate" should be passed to choose
    Probably this should be the main function
    """
    # TODO fix "copy of a slice" error without using df.copy() to avoid memory peaks

    for antenna_key, antenna_df in dict_of_dataframes.items():

        # Filter dataframe values by removing those "not good" tag IDs
        if all_antennas_visited == "2":
            antenna_df = antenna_df[antenna_df['DEC Tag ID'].isin(list_of_good_visitors)]

        # Parse scan dates and times manually after reading the CSV
        antenna_df['Scan Date and Time'] = pd.to_datetime(antenna_df['Scan Date'] + ' ' +
                                                          antenna_df['Scan Time'], format="%d/%m/%Y %H:%M:%S.%f")

        if round_or_truncate == "1":
            # Remove milliseconds by rounding
            round_milliseconds(antenna_df, "Scan Date and Time")
        elif round_or_truncate == "2":
            # Remove milliseconds truncating
            truncate_milliseconds(antenna_df, "Scan Date and Time")

        # Filter all data by date (start and end)
        if filter_start_datetime != "" and filter_end_datetime != "":
            antenna_df = antenna_df[(antenna_df["Scan Date and Time"] >= filter_start_datetime) &
                                    (antenna_df["Scan Date and Time"] <= filter_end_datetime)]

        # Remove unused columns before removing duplicates!
        antenna_df = antenna_df.drop(columns=['Scan Date', 'Scan Time'])

        antenna_df = remove_duplicated_rows(antenna_df)

        antenna_df = calculate_visit_duration(antenna_df)

        # Reorder the columns
        # antenna_df = antenna_df[['DEC Tag ID', 'Scan Date and Time', 'Time Delta', 'Visit Duration', 'Antenna ID']]

        dict_of_dataframes[antenna_key] = antenna_df

    return dict_of_dataframes


def calculate_visit_duration(antenna_df: pd.DataFrame):
    """ Calculates the duration of the visits of pollinators in each antenna """

    # Sort using DEC Tag ID so time delta is correctly calculated
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

    return antenna_df
