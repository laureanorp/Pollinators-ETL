from typing import List, Dict, Set

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class Pipeline:
    """ Class that includes all the functions of the ETL pipeline """

    def __init__(self, path_to_csv: str):
        self.path_to_csv = path_to_csv
        self.max_visit_duration = None
        self.filter_start_datetime = None
        self.filter_end_datetime = None
        self.round_or_truncate = None
        self.all_antennas_visited = None
        self.antennas_dfs = None
        self.df = None

    def _csv_to_dataframe(self, path_to_csv) -> pd.DataFrame:
        """ Imports the CSV file containing all the data from BioMark """
        return pd.read_csv(path_to_csv, sep=";")

    def _list_of_tags_with_all_antennas_visited(self, tag_id_list: List[str],
                                                dict_of_dataframes: Dict[str, pd.DataFrame]) -> set:
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

    def _delete_unused_columns(self, data_frame: pd.DataFrame, columns_to_delete: list) -> pd.DataFrame:
        """ Deletes columns that won't be used anywhere """
        return data_frame.drop(columns=columns_to_delete)

    def _round_milliseconds(self, data_frame: pd.DataFrame, column: str):
        """ Rounds milliseconds on the desired column """
        data_frame[column] = data_frame[column].dt.round('1s')

    def _truncate_milliseconds(self, data_frame: pd.DataFrame, column: str):
        """ Truncates milliseconds on the desired column """
        data_frame[column] = data_frame[column].astype('datetime64[s]')

    def _remove_duplicated_rows(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """ Removes duplicated rows (where every column has the same value) """
        return data_frame.drop_duplicates()

    def _create_dict_of_antennas_dfs(self, data_frame: pd.DataFrame) -> Dict[str, pd.DataFrame]:
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

    def _calculate_visit_duration(self, antenna_df: pd.DataFrame) -> pd.DataFrame:
        """ Calculates the duration of the visits of pollinators in each antenna """

        # Sort using DEC Tag ID so time delta is correctly calculated
        antenna_df = antenna_df.sort_values(by=['DEC Tag ID', 'Scan Date and Time'])

        # Calculate time delta by subtracting "Scan Time" rows
        antenna_df['Time Delta'] = (antenna_df['Scan Date and Time'] -
                                    antenna_df['Scan Date and Time'].shift(1)).astype('timedelta64[s]')

        # Calculate which individual visits are valid and their durations
        # It has to be the same Tag ID and a visit between 1 and 7 seconds
        antenna_df['Valid Visits'] = 0
        antenna_df['Valid Visits'] = np.where((antenna_df['Time Delta'] > 0) &
                                              (antenna_df['Time Delta'] <= self.max_visit_duration) &
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
        # Drop unnecessary columns used for the calculations only
        antenna_df = antenna_df.drop(columns=['Valid Visits', 'Visit Stopper'])

        return antenna_df

    def plot_avg_visit_duration(self):
        """
        Calculates the mean of no null visit durations for each antenna
        Then plots that average duration for each antenna using a bar plot
        """
        list_of_means = []
        for antenna_key, antenna_df in self.antennas_dfs.items():
            no_null = antenna_df[antenna_df["Visit Duration"] != 0]
            list_of_means.append(no_null["Visit Duration"].mean())
        plt.figure()
        plt.bar(self.antennas_dfs.keys(), list_of_means)
        plt.title("Average visit duration for each antenna")
        plt.xlabel("Antennas")
        plt.ylabel("Seconds")
        plt.xticks(rotation=45)
        plt.show()

    def _process_all_antennas_dfs(self, dict_of_dataframes: Dict[str, pd.DataFrame], filter_start_datetime: str,
                                  filter_end_datetime: str, round_or_truncate: str, all_antennas_visited: str,
                                  list_of_good_visitors: Set[str]) -> Dict[str, pd.DataFrame]:
        """ Apply all the different functions to each antenna dataframe """

        # TODO fix "copy of a slice" error without using df.copy() to avoid memory peaks
        for antenna_key, antenna_df in dict_of_dataframes.items():

            # Filter dataframe values by removing those "not good" tag IDs
            if all_antennas_visited == "2":
                antenna_df = antenna_df[antenna_df['DEC Tag ID'].isin(list_of_good_visitors)]
            # Parse scan dates and times manually after reading the CSV
            antenna_df['Scan Date and Time'] = pd.to_datetime(antenna_df['Scan Date'] + ' ' +
                                                              antenna_df['Scan Time'], format="%d/%m/%Y %H:%M:%S.%f")
            if round_or_truncate == "1":
                self._round_milliseconds(antenna_df, "Scan Date and Time")
            elif round_or_truncate == "2":
                self._truncate_milliseconds(antenna_df, "Scan Date and Time")
            # Filter all data by date (start and end)
            if filter_start_datetime != "" and filter_end_datetime != "":
                antenna_df = antenna_df[(antenna_df["Scan Date and Time"] >= filter_start_datetime) &
                                        (antenna_df["Scan Date and Time"] <= filter_end_datetime)]
            # Remove unused columns before removing duplicates
            antenna_df = antenna_df.drop(columns=['Scan Date', 'Scan Time'])
            antenna_df = self._remove_duplicated_rows(antenna_df)
            antenna_df = self._calculate_visit_duration(antenna_df)
            dict_of_dataframes[antenna_key] = antenna_df
        return dict_of_dataframes

    def run_pipeline(self, min_visit_time: int, filter_start_datetime: str, filter_end_datetime: str,
                     round_or_truncate: str, all_antennas_visited: str):
        """ Main function of the class, runs all the pipeline steps and returns a dict of dataframes """

        self.max_visit_duration = min_visit_time
        self.filter_start_datetime = filter_start_datetime
        self.filter_end_datetime = filter_end_datetime
        self.round_or_truncate = round_or_truncate
        self.all_antennas_visited = all_antennas_visited

        self.df = self._csv_to_dataframe(self.path_to_csv)
        self.df = self._delete_unused_columns(self.df, ['Download Date', 'Download Time', 'Reader ID', 'HEX Tag ID',
                                              'Temperature,C', 'Signal,mV', 'Is Duplicate'])
        # Create a list of unique Tag IDs to use in other functions
        all_tag_ids = self.df['DEC Tag ID'].unique().tolist()
        # Create dataframes for each antenna
        self.antennas_dfs = self._create_dict_of_antennas_dfs(self.df)
        # Create list of good visitors (Tag IDs with all antennas are visited)
        list_of_good_visitors = self._list_of_tags_with_all_antennas_visited(all_tag_ids, self.antennas_dfs)
        # Apply all the necessary functions to the antennas data frames
        self.antennas_dfs = self._process_all_antennas_dfs(self.antennas_dfs, self.filter_start_datetime,
                                                           self.filter_end_datetime,
                                                           self.round_or_truncate, self.all_antennas_visited,
                                                           list_of_good_visitors)

    # TODO what happens if antennas_dfs is empty
    def concatenate_antennas_dfs(self, antennas_names: List[str]):
        """
        Concatenates two or more dataframes
        Removes the originals from the antennas_dfs dictionary and adds the new one
        """
        antennas_to_concat = []
        for antenna_name in antennas_names:
            antennas_to_concat.append(self.antennas_dfs[antenna_name])
            del self.antennas_dfs[antenna_name]  # delete original antenna dataframe
        new_antenna = pd.concat(antennas_to_concat)
        self.antennas_dfs['_'.join(antennas_names)] = new_antenna

    def simplify_dataframes(self):
        """
        Removes Time Delta column and leaves only the final rows where Visit duration is > 0
        The final structure of each dataframe is:
        Antenna ID | Tag ID | Scan Date and time | Visit Duration
        """
        # TODO solve problem: scan time should be the first or the last signal?
        for antenna_key in self.antennas_dfs:
            self.antennas_dfs[antenna_key] = self.antennas_dfs[antenna_key].drop(columns='Time Delta')
            self.antennas_dfs[antenna_key] = self.antennas_dfs[antenna_key][
                self.antennas_dfs[antenna_key]['Visit Duration'] != 0]

    # TODO fix: not working because self.df is defined inside run_pipeline()
    def remove_pollinators_manually(self, pollinators_to_remove: List[str]):
        """
        Given a list of pollinators, removes them completely from the main dataset
        Requires running Pipeline.run_pipeline() after
        """
        self.df = self.df[~self.df['DEC Tag ID'].isin(pollinators_to_remove)]

    def export_dataframes_to_excel(self):
        """ Exports the current antenna_dfs to an excel file with a sheet for each dataframe """
        with pd.ExcelWriter('exports/Antennas_dfs.xlsx') as writer:
            for antenna_key in self.antennas_dfs:
                self.antennas_dfs[antenna_key].to_excel(writer, sheet_name=antenna_key)
