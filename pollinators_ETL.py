from typing import List, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from bokeh.embed import file_html
from bokeh.io import output_file
from bokeh.layouts import layout
from bokeh.plotting import figure
from bokeh.resources import CDN


class Pipeline:
    """ Class that includes all the functions of the ETL pipeline """

    def __init__(self, csv_files: List[str]):
        # Input for creating the initial dataframe
        self.csv_files = csv_files
        self.parsed_dataframes = None
        self.antennas_info = None
        self.dates_of_dfs = None
        self.genotypes_of_each_experiment = None
        self.df_with_genotypes = None
        # Parameters for pipeline run
        self.max_time_between_signals = None
        self.filter_start_datetime = None
        self.filter_end_datetime = None
        self.round_or_truncate = None
        self.list_of_good_visitors = None
        self.filter_tags_by_visited_genotypes = None
        self.genotypes_dfs = None
        self.df = None
        self.pollinators_to_remove = None
        self.visited_genotypes_required = None
        # Parameters only for results and statistics
        self.flowers_per_antenna = None

    def preprocessing_of_data(self):
        """ Calls the csv parser function and exports the antennas of each dataframe """
        self.parsed_dataframes = self._csv_files_to_dataframe()
        self.antennas_info = self._export_antennas_info()
        self.dates_of_dfs = self._export_dates_info()

    def input_genotypes_data(self, genotypes_of_each_experiment):
        self.genotypes_of_each_experiment = genotypes_of_each_experiment

    def input_parameters_of_run(self, filter_start_datetime: str, filter_end_datetime: str,
                                max_time_between_signals: int, round_or_truncate: str,
                                filter_tags_by_visited_genotypes: str, visited_genotypes_required: List[str],
                                pollinators_to_remove: List[str], flowers_per_antenna: int):
        """ Method for introducing all the necessary parameters for the pipeline run """
        self.max_time_between_signals = max_time_between_signals
        self.filter_start_datetime = filter_start_datetime
        self.filter_end_datetime = filter_end_datetime
        self.round_or_truncate = round_or_truncate
        self.filter_tags_by_visited_genotypes = filter_tags_by_visited_genotypes
        self.visited_genotypes_required = visited_genotypes_required
        self.pollinators_to_remove = pollinators_to_remove
        self.flowers_per_antenna = flowers_per_antenna

    def add_genotypes_and_join_df(self):
        """ Add genotypes column to each df and joins them into one """
        new_dict_of_dfs = self._add_genotypes_column(self.parsed_dataframes)
        self._join_dataframes(new_dict_of_dfs)

    def run_pipeline(self):
        """ Main function of the class, runs all the pipeline steps and returns a dict of dataframes """
        pd.options.mode.chained_assignment = None  # Temporary fix for SettingCopyWarning

        self.df = self.df_with_genotypes.copy()
        self._remove_pollinators_manually(self.pollinators_to_remove)
        self._remove_unused_columns()
        # Create a list of unique Tag IDs to use in other functions
        all_tag_ids = self.df['DEC Tag ID'].unique().tolist()
        # Create dataframes for each genotype
        self.genotypes_dfs = self._create_dict_of_genotypes_dfs()
        # Create list of good visitors (Tag IDs with all the required genotypes visited)
        if self.filter_tags_by_visited_genotypes == "True":
            self.list_of_good_visitors = self._obtain_good_visitors(all_tag_ids, self.visited_genotypes_required)
        # Apply all the necessary functions to the genotypes data frames
        self.genotypes_dfs = self._process_all_genotypes_dfs()
        self._simplify_dataframes()

    def export_dataframes_to_excel(self):
        """ Exports the current genotypes_dfs to an excel file with a sheet for each dataframe """
        with pd.ExcelWriter('exports/Antennas_dfs.xlsx') as writer:
            for genotype_key in self.genotypes_dfs:
                self.genotypes_dfs[genotype_key].to_excel(writer, sheet_name=genotype_key, index=False)

    def plot_avg_visit_duration(self):
        """
        Calculates the mean of no null visit durations for each genotype.
        Then plots that average duration for each genotype using a bar plot.
        """
        list_of_means = []
        for genotype_key, genotype_df in self.genotypes_dfs.items():
            no_null = genotype_df[genotype_df["Visit Duration"] != 0]
            list_of_means.append(no_null["Visit Duration"].mean())
        plt.figure()
        plt.bar(self.genotypes_dfs.keys(), list_of_means)
        plt.title("Average visit duration for each genotype")
        plt.xlabel("Genotypes")
        plt.ylabel("Seconds")
        plt.xticks(rotation=45)
        # plt.savefig('plot.pdf')
        plt.show()

    def _csv_files_to_dataframe(self) -> Dict[str, pd.DataFrame]:
        """ Given a list of csv files, creates a dict with the parsed dataframes """
        parsed_dataframes = {}
        for csv_file in self.csv_files:
            key_name = str(csv_file)
            csv_path = "".join(["server_uploads/", csv_file])
            parsed_dataframes[key_name] = pd.read_csv(csv_path, sep=";",
                                                      dtype={"Scan Date": "object", "Scan Time": "object",
                                                             "Antenna ID": "int64", "DEC Tag ID": "object"},
                                                      low_memory=False)
        return parsed_dataframes

    def _export_antennas_info(self) -> Dict[str, List[str]]:
        """ Exports a dict with lists of the antennas present in each dataframe """
        antennas_of_each_dataframe = {}
        for key in self.parsed_dataframes:
            antennas = sorted(self.parsed_dataframes[key]['Antenna ID'].unique().tolist())
            antennas_of_each_dataframe[key] = antennas
        return antennas_of_each_dataframe

    def _export_dates_info(self) -> Dict[str, List[str]]:
        dates_of_dfs = {}
        for key in self.parsed_dataframes:
            dates_of_dfs[key] = [self.parsed_dataframes[key]['Scan Date'].iloc[0],
                                 self.parsed_dataframes[key]['Scan Date'].iloc[-1]]
        return dates_of_dfs

    # TODO fix parsed_dataframes is being modified (it has genotypes column and it shouldn't)
    def _add_genotypes_column(self, dict_of_dfs: Dict[str, pd.DataFrame]):
        """
        Adds the genotypes column to each dataframe.
        Uses a list of dicts which includes the relationships between each antenna and its genotype.
        Each element of the list is a different experiment (parsed df).
        """
        dataframes = list(dict_of_dfs.values())
        new_dict_of_dfs = {}
        for count, (df, genotypes) in enumerate(zip(dataframes, self.genotypes_of_each_experiment)):
            df["Genotype"] = df["Antenna ID"].map(genotypes)
            key_name = "df_" + str(count)
            new_dict_of_dfs[key_name] = df
        return new_dict_of_dfs

    def _join_dataframes(self, dict_of_dfs: Dict[str, pd.DataFrame]):
        """ Concatenates all the dataframes (already including genotypes) into one dataframe """
        dataframes = list(dict_of_dfs.values())
        self.df_with_genotypes = pd.concat(dataframes)

    def _remove_unused_columns(self):
        """ Removes the unused columns if present in the dataframe """
        try:
            self.df.drop(columns=['Download Date', 'Download Time', 'Reader ID', 'HEX Tag ID',
                                  'Temperature,C', 'Signal,mV', 'Is Duplicate'], inplace=True)
        except KeyError:
            pass

    def _create_dict_of_genotypes_dfs(self) -> Dict[str, pd.DataFrame]:
        """
        Create a dictionary with "n" dataframes, being "n" the number of different genotypes on the data.
        Each dataframe is named after the appropriate genotype.
        Structure of the returned dict is "df_genotype":pd.DataFrame
        """
        genotypes = self.df['Genotype'].unique().tolist()
        genotypes_data_frames = {}
        for genotype in genotypes:
            genotype_data_frame = self.df['Genotype'] == genotype
            key_name = str(genotype)
            genotypes_data_frames[key_name] = self.df[genotype_data_frame]
        return genotypes_data_frames

    def _obtain_good_visitors(self, all_tag_ids: List[str], genotypes_required: List[str]) -> set:
        """
        Creates and returns a set that includes only those Tag IDs that have visited the desired genotypes.
        Takes the list of Tag IDs and the list of genotypes dataframes as arguments,
        and iterates over the Tag IDs list, checking if each Tag ID is present on each dataframe.
        """
        good_visitors = set()
        for tag_id in all_tag_ids:
            is_visitor_in_df = []
            for genotype_name in genotypes_required:
                is_visitor_in_df.append(tag_id in self.genotypes_dfs[genotype_name]["DEC Tag ID"].values)
            if all(is_visitor_in_df):  # if all elements are True, it's a "good" visitor
                good_visitors.add(tag_id)
        return good_visitors

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

    def _calculate_visit_duration(self, genotype_df: pd.DataFrame) -> pd.DataFrame:
        """ Calculates the duration of the visits of pollinators in each genotype """

        # Sort using DEC Tag ID so time delta is correctly calculated
        genotype_df = genotype_df.sort_values(by=['DEC Tag ID', 'Scan Date and Time'])
        # Calculate time delta by subtracting "Scan Time" rows
        genotype_df['Time Delta'] = (genotype_df['Scan Date and Time'] -
                                     genotype_df['Scan Date and Time'].shift(1)).astype('timedelta64[s]')
        # Calculate which individual visits are valid and their durations
        # It has to be the same Tag ID and a visit between 1 and 7 seconds
        genotype_df['Valid Visits'] = 0
        genotype_df['Valid Visits'] = np.where((genotype_df['Time Delta'] > 0) &
                                               (genotype_df['Time Delta'] <= int(self.max_time_between_signals)) &
                                               (genotype_df['DEC Tag ID'] == genotype_df['DEC Tag ID'].shift(1)),
                                               genotype_df['Time Delta'], 0)
        # Stopper: 1 when the running summation has to stop
        genotype_df['Visit Stopper'] = np.where(genotype_df['Valid Visits'] == 0, 1, 0)

        # Sum the duration of the individual visits to find the total
        sum_duration = genotype_df.groupby(genotype_df['Visit Stopper'].shift(fill_value=0)
                                           .cumsum())['Valid Visits'].transform('sum')
        genotype_df['Visit Duration'] = np.where(genotype_df['Visit Stopper'] == 1, sum_duration, 0)

        # Shift up al rows so the visit duration is in line with the correct Tag ID
        genotype_df['Visit Duration'] = genotype_df['Visit Duration'].shift(-1)
        # Drop unnecessary columns used for the calculations only
        genotype_df.drop(columns=['Valid Visits', 'Visit Stopper'], inplace=True)

        return genotype_df

    def _process_all_genotypes_dfs(self) -> Dict[str, pd.DataFrame]:
        """ Apply all the different functions to each genotype dataframe """
        for genotype_key, genotype_df in self.genotypes_dfs.items():

            # Filter dataframe values by removing those "not good" tag IDs
            if self.filter_tags_by_visited_genotypes == "True":
                genotype_df = genotype_df[genotype_df['DEC Tag ID'].isin(self.list_of_good_visitors)]
            # Parse scan dates and times manually after reading the CSV
            genotype_df['Scan Date and Time'] = pd.to_datetime(genotype_df['Scan Date'] + ' ' +
                                                               genotype_df['Scan Time'],
                                                               format="%d/%m/%Y %H:%M:%S.%f")
            if self.round_or_truncate == "round":
                genotype_df["Scan Date and Time"] = self._round_milliseconds("Scan Date and Time", genotype_df)
            elif self.round_or_truncate == "truncate":
                genotype_df["Scan Date and Time"] = self._truncate_milliseconds("Scan Date and Time", genotype_df)
            # Filter all data by date (start and end)
            if self.filter_start_datetime != "" and self.filter_end_datetime != "":
                genotype_df = genotype_df[(genotype_df["Scan Date and Time"] >= self.filter_start_datetime) &
                                          (genotype_df["Scan Date and Time"] <= self.filter_end_datetime)]
            # Remove unused columns before removing duplicates
            genotype_df = genotype_df.drop(columns=['Scan Date', 'Scan Time'])
            genotype_df = genotype_df.drop_duplicates()
            genotype_df = self._calculate_visit_duration(genotype_df)
            self.genotypes_dfs[genotype_key] = genotype_df

        return self.genotypes_dfs

    def _simplify_dataframes(self):
        """
        Removes Time Delta column and leaves only the final rows where Visit duration is > 0
        The final structure of each dataframe is:
        Antenna ID | Tag ID | Scan Date and time | Visit Duration
        """
        # TODO solve problem: scan time should be the first or the last signal?
        for genotype_key in self.genotypes_dfs:
            self.genotypes_dfs[genotype_key].drop(columns='Time Delta', inplace=True)
            self.genotypes_dfs[genotype_key] = self.genotypes_dfs[genotype_key][
                self.genotypes_dfs[genotype_key]['Visit Duration'] != 0]

    def _remove_pollinators_manually(self, pollinators_to_remove: List[str]):
        """ Given a list of pollinators, removes them completely from the main dataset """
        if pollinators_to_remove:
            self.df = self.df[~self.df['DEC Tag ID'].isin(pollinators_to_remove)]


class Plot:
    """
    Class that includes methods for generating plots using the class Pipeline results.
    Is this collection of methods, Bokeh is used to generate HTML plots that are later included in the Flask app.
    """

    def __init__(self, genotypes_dfs: Dict[str, pd.DataFrame]):
        # Input for creating the initial dataframe
        self.genotypes_dfs = genotypes_dfs

    def lay_out_plots_to_html(self):
        # Save results to an HTML file
        output_file("templates/layout.html")

        html = file_html(layout([
            [self._plot_visits_per_genotype()],
            [self._plot_visits_per_genotype(), self._plot_visits_per_genotype()],
            [self._plot_visits_per_genotype()],
        ]), CDN)

        file = open("templates/layout.html", "w+")
        file.write(html)
        file.close()

    def _plot_visits_per_genotype(self):
        output_file("templates/visits_per_genotype.html")

        genotypes = []
        visits = []
        for key in self.genotypes_dfs:
            genotypes.append(key)
            visits.append(self.genotypes_dfs[key].size)

        plot = figure(x_range=genotypes, plot_height=250, title="Number of visits per genotype",
                      toolbar_location=None, tools="", sizing_mode="stretch_both")
        plot.vbar(x=genotypes, top=visits, width=0.9)
        plot.xgrid.grid_line_color = None
        plot.y_range.start = 0

        return plot

    def _plot_visit_duration_per_genotype(self):
        output_file("templates/visit_duration_per_genotype.html")

        genotypes = []
        means = []
        for key in self.genotypes_dfs:
            genotypes.append(key)
            means.append(self.genotypes_dfs[key]["Visit Duration"].mean())

        plot = figure(x_range=genotypes, plot_height=250, title="Average duration of visits per genotype",
                      toolbar_location=None, tools="")
        plot.vbar(x=genotypes, top=means, width=0.9)
        plot.xgrid.grid_line_color = None
        plot.y_range.start = 0

        # Save results to an HTML file
        html = file_html(plot, CDN)
        file = open("templates/visit_duration_per_genotype.html", "x")  # x = create file
        file.write(html)
        file.close()

    def _average_visit_duration(self) -> int:
        # Not per genotype, avg of whole dataset
        dataframes = list(self.genotypes_dfs.values())
        whole_dataframe = pd.concat(dataframes)
        mean = round(whole_dataframe["Visit Duration"].mean(), 2)
        return mean
