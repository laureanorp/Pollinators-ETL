from typing import List, Dict

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
        self.list_of_good_visitors = None
        self.filter_tags_by_visited_antennas = None
        self.antennas_dfs = None
        self.df = None
        self.antennas_to_concat = None
        self.pollinators_to_remove = None
        self.visited_antennas_required = None
        self.flowers_per_antenna = None

    def input_parameters_of_run(self, max_visit_duration: int, filter_start_datetime: str, filter_end_datetime: str,
                                round_or_truncate: str, filter_tags_by_visited_antennas: bool,
                                antennas_to_concat: List[str], pollinators_to_remove: List[str],
                                visited_antennas_required: List[str], flowers_per_antenna: int):
        """ Method for introducing all the necessary parameters for the pipeline run """
        self.max_visit_duration = max_visit_duration
        self.filter_start_datetime = filter_start_datetime
        self.filter_end_datetime = filter_end_datetime
        self.round_or_truncate = round_or_truncate
        self.filter_tags_by_visited_antennas = filter_tags_by_visited_antennas
        self.visited_antennas_required = visited_antennas_required
        self.antennas_to_concat = antennas_to_concat
        self.pollinators_to_remove = pollinators_to_remove
        self.flowers_per_antenna = flowers_per_antenna

    def run_pipeline(self):
        """ Main function of the class, runs all the pipeline steps and returns a dict of dataframes """
        pd.options.mode.chained_assignment = None  # Temporary fix for SettingCopyWarning
        self.df = self._csv_to_dataframe()
        self._remove_pollinators_manually(self.pollinators_to_remove)
        self._remove_unused_columns()
        # Create a list of unique Tag IDs to use in other functions
        all_tag_ids = self.df['DEC Tag ID'].unique().tolist()
        # Create dataframes for each antenna
        self.antennas_dfs = self._create_dict_of_antennas_dfs()
        # Create list of good visitors (Tag IDs with all the required antennas visited)
        if self.filter_tags_by_visited_antennas:
            self.list_of_good_visitors = self._obtain_good_visitors(all_tag_ids, self.visited_antennas_required)
        # Apply all the necessary functions to the antennas data frames
        self.antennas_dfs = self._process_all_antennas_dfs()
        self._simplify_dataframes()
        self._concatenate_antennas_dfs(self.antennas_to_concat)

    def _remove_unused_columns(self):
        """ Removes the unused columns if present in the dataframe """
        try:
            self.df.drop(columns=['Download Date', 'Download Time', 'Reader ID', 'HEX Tag ID',
                                  'Temperature,C', 'Signal,mV', 'Is Duplicate'], inplace=True)
        except KeyError:
            pass

    def export_dataframes_to_excel(self):
        """ Exports the current antenna_dfs to an excel file with a sheet for each dataframe """
        with pd.ExcelWriter('exports/Antennas_dfs.xlsx') as writer:
            for antenna_key in self.antennas_dfs:
                self.antennas_dfs[antenna_key].to_excel(writer, sheet_name=antenna_key, index=False)

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
        plt.savefig('plot.pdf')
        plt.show()

    def _csv_to_dataframe(self) -> pd.DataFrame:
        """ Transforms the CSV file containing all the data from BioMark into a Pandas dataframe """
        return pd.read_csv(self.path_to_csv, sep=";",
                           dtype={"Scan Date": "object", "Scan Time": "object", "Antenna ID": "int64",
                                  "DEC Tag ID": "object"}, low_memory=False)

    def _obtain_good_visitors(self, all_tag_ids: List[str], antennas_required: List[str]) -> set:
        """
        Creates and returns a set that includes only those Tag IDs that have visited the desired antennas
        Takes the list of Tag IDs and the list of antennas dataframes as arguments,
        and iterates over the Tag IDs list, checking if each Tag ID is present on each dataframe
        """
        good_visitors = set()
        for tag_id in all_tag_ids:
            is_visitor_in_df = []
            for antenna_name in antennas_required:
                is_visitor_in_df.append(tag_id in self.antennas_dfs[antenna_name]["DEC Tag ID"].values)
            if all(is_visitor_in_df):  # if all elements are True, it's a "good" visitor
                good_visitors.add(tag_id)
        return good_visitors

    def _create_dict_of_antennas_dfs(self) -> Dict[str, pd.DataFrame]:
        """
        Create a dictionary with "n" dataframes, being "n" the number of different antennas on the data
        Each dataframe is named after the number of its antenna
        Structure of the returned dict is "antenna_n":pd.DataFrame
        """
        antennas_ids = sorted(self.df['Antenna ID'].unique().tolist())
        antennas_data_frames = {}
        for antenna_number in antennas_ids:
            antenna_data_frame = self.df['Antenna ID'] == antenna_number
            key_name = "antenna_" + str(antenna_number)
            antennas_data_frames[key_name] = self.df[antenna_data_frame]
        return antennas_data_frames

    @staticmethod
    def _round_milliseconds(column: str, dataframe: pd.DataFrame) -> pd.DataFrame:
        """ Rounds milliseconds on the desired column """
        dataframe[column] = dataframe[column].dt.round('1s')
        return dataframe[column]

    @staticmethod
    def _truncate_milliseconds(column: str, dataframe: pd.DataFrame) -> pd.DataFrame:
        """ Truncates milliseconds on the desired column """
        dataframe[column] = dataframe[column].astype('datetime64[s]')
        return dataframe[column]

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
                                              (antenna_df['Time Delta'] <= int(self.max_visit_duration)) &
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
        antenna_df.drop(columns=['Valid Visits', 'Visit Stopper'], inplace=True)

        return antenna_df

    def _process_all_antennas_dfs(self) -> Dict[str, pd.DataFrame]:
        """ Apply all the different functions to each antenna dataframe """
        for antenna_key, antenna_df in self.antennas_dfs.items():

            # Filter dataframe values by removing those "not good" tag IDs
            if self.filter_tags_by_visited_antennas:
                antenna_df = antenna_df[antenna_df['DEC Tag ID'].isin(self.list_of_good_visitors)]
            # Parse scan dates and times manually after reading the CSV
            antenna_df['Scan Date and Time'] = pd.to_datetime(antenna_df['Scan Date'] + ' ' +
                                                              antenna_df['Scan Time'],
                                                              format="%d/%m/%Y %H:%M:%S.%f")
            if self.round_or_truncate == "round":
                antenna_df["Scan Date and Time"] = self._round_milliseconds("Scan Date and Time", antenna_df)
            elif self.round_or_truncate == "truncate":
                antenna_df["Scan Date and Time"] = self._truncate_milliseconds("Scan Date and Time", antenna_df)
            # Filter all data by date (start and end)
            if self.filter_start_datetime != "" and self.filter_end_datetime != "":
                antenna_df = antenna_df[(antenna_df["Scan Date and Time"] >= self.filter_start_datetime) &
                                        (antenna_df["Scan Date and Time"] <= self.filter_end_datetime)]
            # Remove unused columns before removing duplicates
            antenna_df = antenna_df.drop(columns=['Scan Date', 'Scan Time'])
            antenna_df = antenna_df.drop_duplicates()
            antenna_df = self._calculate_visit_duration(antenna_df)
            self.antennas_dfs[antenna_key] = antenna_df

        return self.antennas_dfs

    def _concatenate_antennas_dfs(self, antennas_names: List[str]):
        """
        Concatenates two or more dataframes
        Removes the originals from the antennas_dfs dictionary and adds the new one
        """
        if antennas_names:  # if list is not empty
            antennas_to_concat = []
            for antenna_name in antennas_names:
                antennas_to_concat.append(self.antennas_dfs[antenna_name])
                del self.antennas_dfs[antenna_name]  # delete original antenna dataframe
            new_antenna = pd.concat(antennas_to_concat)
            self.antennas_dfs['_'.join(antennas_names)] = new_antenna

    def _simplify_dataframes(self):
        """
        Removes Time Delta column and leaves only the final rows where Visit duration is > 0
        The final structure of each dataframe is:
        Antenna ID | Tag ID | Scan Date and time | Visit Duration
        """
        # TODO solve problem: scan time should be the first or the last signal?
        for antenna_key in self.antennas_dfs:
            self.antennas_dfs[antenna_key].drop(columns='Time Delta', inplace=True)
            self.antennas_dfs[antenna_key] = self.antennas_dfs[antenna_key][
                self.antennas_dfs[antenna_key]['Visit Duration'] != 0]

    def _remove_pollinators_manually(self, pollinators_to_remove: List[str]):
        """
        Given a list of pollinators, removes them completely from the main dataset
        Requires running Pipeline.run_pipeline() after
        """
        if pollinators_to_remove:
            self.df = self.df[~self.df['DEC Tag ID'].isin(pollinators_to_remove)]
