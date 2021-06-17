import itertools
import os
from datetime import timedelta
from typing import List, Dict

import numpy as np
import pandas as pd
from bokeh.embed import file_html
from bokeh.layouts import layout
from bokeh.models import (ColumnDataSource, HoverTool, DatetimeTickFormatter,
                          )
from bokeh.palettes import viridis
from bokeh.plotting import figure
from bokeh.resources import CDN
from math import pi
from numpy.lib import math
from scipy.stats import ttest_ind


class Pipeline:
    """ Class that includes all the functions of the ETL pipeline """

    def __init__(self, excel_files: List[str]):
        # Input involved in creating the initial dataframe
        self.excel_files = excel_files
        self.parsed_dataframes = None
        self.antennas_info = None
        self.dates_of_dfs = None
        self.genotypes_of_each_experiment = None
        # Parameters for pipeline run
        self.max_time_between_signals = None
        self.round_or_truncate = None
        self.list_of_good_visitors = None
        self.filter_tags_by_visited_genotypes = None
        self.visited_genotypes_required = None
        self.pollinators_to_remove = None
        self.filter_start_datetime = None
        self.filter_end_datetime = None
        # Pipeline attributes
        self.pollinators_aliases = None
        self.df_with_genotypes = None
        self.genotypes_dfs = None
        self.df = None
        # Parameters for results and statistics
        self.final_joined_df = None
        self.statistics = None
        self.genotypes_names = None

    def preprocessing_of_data(self):
        """Calls the excel parser function and exports the antennas of each dataframe"""
        self.parsed_dataframes = self._excel_files_to_dataframe()
        self.antennas_info = self._export_antennas_info()
        self.dates_of_dfs = self._export_dates_info()

    def input_genotypes_data(self, genotypes_of_each_experiment: List[Dict[int, str]]):
        """Method for introducing the genotypes of each antenna"""
        self.genotypes_of_each_experiment = genotypes_of_each_experiment

    def input_parameters_of_run(self, max_time_between_signals: str, round_or_truncate: str,
                                pollinators_to_remove: List[str], filter_tags_by_visited_genotypes: str,
                                visited_genotypes_required=None, filter_start_datetime: str = "",
                                filter_end_datetime: str = ""):
        """Method for introducing all the necessary parameters for the pipeline run"""
        if visited_genotypes_required is None:
            visited_genotypes_required = []
        self.max_time_between_signals = int(max_time_between_signals)
        self.filter_start_datetime = filter_start_datetime
        self.filter_end_datetime = filter_end_datetime
        self.round_or_truncate = round_or_truncate
        self.filter_tags_by_visited_genotypes = filter_tags_by_visited_genotypes
        self.visited_genotypes_required = visited_genotypes_required
        self.pollinators_to_remove = pollinators_to_remove

    def run_pipeline(self):
        """Main function of the class, runs all the pipeline steps"""
        pd.options.mode.chained_assignment = None  # Temporary fix for SettingCopyWarning

        self._clean_up_cached_files()
        self._add_genotypes_and_join_df()
        self._assign_aliases_for_pollinators()
        self.df = self.df_with_genotypes.copy()
        self._remove_pollinators_manually(self.pollinators_to_remove)
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
        self._compute_descriptive_statistics()
        self._export_dataframes_to_excel()
        self._dataframes_to_html_tables()
        self._update_pollinator_aliases()

    def _excel_files_to_dataframe(self) -> Dict[str, pd.DataFrame]:
        """ Given a list of excel files, creates a dict with the parsed dataframes """
        parsed_dataframes = {}
        for excel_file in self.excel_files:
            file_name = str(excel_file)
            excel_path = "".join(["/tmp/server_uploads/", excel_file])
            parsed_dataframes[file_name] = pd.read_excel(excel_path,
                                                         usecols=["Scan Date", "Scan Time", "Antenna ID", "DEC Tag ID"],
                                                         dtype={"Scan Date": "object", "Scan Time": "object",
                                                                "Antenna ID": "int64", "DEC Tag ID": "object"})
        return parsed_dataframes

    def _clean_up_cached_files(self):
        """Removes old files that are not going to be used on this pipeline run"""
        if os.path.exists('/tmp/exports'):
            for entry in os.listdir('/tmp/exports'):  # removes old html/excel files
                os.remove(os.path.join('/tmp/exports', entry))
        if os.path.exists('/tmp/server_uploads'):
            for entry in os.listdir('/tmp/server_uploads'):  # removes input excel files
                if entry not in self.excel_files:
                    os.remove(os.path.join('/tmp/server_uploads', entry))

    def _export_antennas_info(self) -> Dict[str, List[str]]:
        """ Exports a dict with lists of the antennas present in each dataframe """
        antennas_of_each_dataframe = {}
        for file_name in self.parsed_dataframes:
            antennas = sorted(self.parsed_dataframes[file_name]['Antenna ID'].unique().tolist())
            antennas_of_each_dataframe[file_name] = antennas
        return antennas_of_each_dataframe

    def _export_dates_info(self) -> Dict[str, List[str]]:
        """ Exports a dict with the start and end date of each experiment """
        dates_of_dfs = {}
        for file_name in self.parsed_dataframes:
            dates_of_dfs[file_name] = [self.parsed_dataframes[file_name]['Scan Date'].iloc[0],
                                       self.parsed_dataframes[file_name]['Scan Date'].iloc[-1]]
        return dates_of_dfs

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
            name = "df_" + str(count)
            new_dict_of_dfs[name] = df
        return new_dict_of_dfs

    def _add_genotypes_and_join_df(self):
        """Add genotypes column to each df and joins them into one"""
        dataframes = list(self._add_genotypes_column(self.parsed_dataframes).values())
        self.df_with_genotypes = pd.concat(dataframes)

    def _assign_aliases_for_pollinators(self):
        """
        Creates a dictionary for easier identification of the pollinators.
        Each pollinator (key) has its own integer.
        """
        self.pollinators_aliases = {}
        pollinators = self.df_with_genotypes['DEC Tag ID'].unique().tolist()
        for count, pollinator in enumerate(pollinators, start=1):
            self.pollinators_aliases[pollinator] = str(count)
        self.df_with_genotypes["Tag Alias"] = self.df_with_genotypes["DEC Tag ID"].map(self.pollinators_aliases)

    def _remove_pollinators_manually(self, pollinators_to_remove: List[str]):
        """ Given a list of pollinators (aliases), removes them completely from the main dataset """
        if pollinators_to_remove:
            self.df = self.df[~self.df['DEC Tag ID'].isin(pollinators_to_remove)]

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
            genotype_name = str(genotype)
            genotypes_data_frames[genotype_name] = self.df[genotype_data_frame]
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

    def _process_all_genotypes_dfs(self) -> Dict[str, pd.DataFrame]:
        """ Apply all the different functions to each genotype dataframe """
        for genotype_key, genotype_df in self.genotypes_dfs.items():

            # Filter dataframe values by removing those "not good" tag IDs
            if self.filter_tags_by_visited_genotypes == "True":
                genotype_df = genotype_df[genotype_df['DEC Tag ID'].isin(self.list_of_good_visitors)]
            # Parse scan dates and times manually after reading the Excel file
            genotype_df['Scan Date and Time'] = pd.to_datetime(genotype_df['Scan Date'] + ' '
                                                               + genotype_df['Scan Time'],
                                                               format="%d/%m/%Y %H:%M:%S.%f")
            if self.round_or_truncate == "round":
                genotype_df["Scan Date and Time"] = self._round_milliseconds("Scan Date and Time", genotype_df)
            elif self.round_or_truncate == "truncate":
                genotype_df["Scan Date and Time"] = self._truncate_milliseconds("Scan Date and Time", genotype_df)
            # Filter all data by date (start and end)
            if self.filter_start_datetime != "" and self.filter_end_datetime != "":
                genotype_df = genotype_df[(genotype_df["Scan Date and Time"] >= self.filter_start_datetime)
                                          & (genotype_df["Scan Date and Time"] <= self.filter_end_datetime)]
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
            self.genotypes_dfs[genotype_key].dropna(inplace=True)
            self.genotypes_dfs[genotype_key].drop(columns='Time Delta', inplace=True)
            self.genotypes_dfs[genotype_key] = self.genotypes_dfs[genotype_key][
                self.genotypes_dfs[genotype_key]['Visit Duration'] != 0]

    def _calculate_visit_duration(self, genotype_df: pd.DataFrame) -> pd.DataFrame:
        """ Calculates the duration of the visits of pollinators in each genotype """
        # Sort using DEC Tag ID so time delta is correctly calculated
        genotype_df = genotype_df.sort_values(by=['DEC Tag ID', 'Scan Date and Time'])
        # Calculate time delta by subtracting "Scan Time" rows
        genotype_df['Time Delta'] = (genotype_df['Scan Date and Time'] -
                                     genotype_df['Scan Date and Time'].shift(1)).astype('timedelta64[s]')
        # Calculate which individual visits are valid and their durations
        # It has to be the same Tag ID and a visit between 1 and the desired number of seconds
        genotype_df['Valid Visits'] = 0
        genotype_df['Valid Visits'] = np.where((genotype_df['Time Delta'] > 0) &
                                               (genotype_df['Time Delta'] <= self.max_time_between_signals) &
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

    def _compute_descriptive_statistics(self):
        """ Returns a list of descriptive stats about the data frames """
        dataframes = list(self.genotypes_dfs.values())
        self.final_joined_df = pd.concat(dataframes)
        self.statistics = {"genotypes_count": len(self.genotypes_dfs),
                           "pollinators_count": len(self.final_joined_df['DEC Tag ID'].unique()),
                           "visits_count": len(self.final_joined_df),
                           "visits_mean": round(self.final_joined_df["Visit Duration"].mean(), 2),
                           "visits_median": self.final_joined_df["Visit Duration"].median(),
                           "visits_mode": self.final_joined_df["Visit Duration"].mode().values.tolist(),
                           "visits_std": round(self.final_joined_df["Visit Duration"].std(), 2),
                           "ttest_genotypes": self._test_difference_means(),
                           "outliers": self._detect_outliers()}

    def _export_dataframes_to_excel(self):
        """ Exports the current genotypes_dfs to an excel file with a sheet for each dataframe """
        if not os.path.exists('/tmp/exports'):
            os.mkdir('/tmp/exports')
        with pd.ExcelWriter('/tmp/exports/genotypes.xlsx') as writer:
            for genotype_key in self.genotypes_dfs:
                self.genotypes_dfs[genotype_key].to_excel(writer, sheet_name=genotype_key, index=False)

    def _dataframes_to_html_tables(self):
        """ Exports each dataframe to a simple HTML table """
        self.genotypes_names = []
        for name in self.genotypes_dfs:
            html = self.genotypes_dfs[name].to_html(index=False)
            self.genotypes_names.append(name)
            with open("/tmp/exports/" + name + "_table.html", "w+") as file_handler:
                file_handler.write(html)

    def _detect_outliers(self) -> Dict[str, int]:
        """
        Detects outliers in the whole dat by using the IQR method.
        Computes the Q1 and Q3 and extracts those visits out of that range.
        Then fetches the pollinators accountable for those visits and returns them as a dict.
        """
        q1 = self.final_joined_df['Visit Duration'].quantile(0.25)
        q3 = self.final_joined_df['Visit Duration'].quantile(0.75)
        iqr = q3 - q1
        outliers_series = (self.final_joined_df['Visit Duration'] < (q1 - 1.5 * iqr)) | (
                self.final_joined_df['Visit Duration'] > (q3 + 1.5 * iqr))

        pollinators_series = self.final_joined_df.loc[outliers_series.values]["Tag Alias"]
        outlier_pollinators = pollinators_series.value_counts().to_dict()
        return outlier_pollinators

    def _test_difference_means(self) -> Dict[str, List[float]]:
        """
        Computes a t-test (difference between means) between each possible pair of genotypes,
        using the average visit duration of the df.
        """
        ttest_results = {}
        for genotype, genotype2 in itertools.combinations(self.genotypes_dfs.keys(), 2):
            result = [round(num, 3) for num in list(  # round t-test results
                ttest_ind(self.genotypes_dfs[genotype]["Visit Duration"],
                          self.genotypes_dfs[genotype2]["Visit Duration"]))]  # genotype is compared with the rest
            if not math.isnan(result[0]):  # save the result only if not NaN
                ttest_results[genotype + " and " + genotype2] = result
        return ttest_results

    def _update_pollinator_aliases(self):
        final_pollinators = self.final_joined_df["DEC Tag ID"].unique().tolist()
        new_dict = {alias: self.pollinators_aliases[alias] for alias in final_pollinators}
        self.pollinators_aliases = new_dict

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


class Plot:
    """
    Class that includes methods for generating plots using the class Pipeline results.
    Is this collection of methods, Bokeh is used to generate HTML plots that are later included in the Flask app.
    """

    def __init__(self, genotypes_dfs: Dict[str, pd.DataFrame]):
        # Input for creating the initial dataframe
        self.genotypes_dfs = genotypes_dfs
        dataframes = list(self.genotypes_dfs.values())
        self.final_joined_df = pd.concat(dataframes)

    def lay_out_plots_to_html(self):
        """ Saves all the plots generated in this Class to different HTML file with a certain layout"""
        html = file_html(layout([
            [self._plot_visit_count_per_genotype()],
            [self._plot_visit_duration_cumsum_per_genotype()],
            [self._plot_average_visit_duration_per_genotype()]
        ]), CDN)
        with open("/tmp/templates/charts_per_genotype.html", "w+") as file_handler:
            file_handler.write("{% raw %}")  # avoid Jinja2 having problems with bokeh date formatters as "{%H"
            file_handler.write(html)
            file_handler.write("{% endraw %}")
        html = file_html(layout([
            [self._plot_visit_count_per_pollinator()],
            [self._plot_visit_duration_cumsum_per_pollinator()],
            [self._plot_average_visit_duration_per_pollinator()]
        ]), CDN)
        with open("/tmp/templates/charts_per_pollinator.html", "w+") as file_handler:
            file_handler.write("{% raw %}")
            file_handler.write(html)
            file_handler.write("{% endraw %}")
        html = file_html(layout([
            [self._plot_visit_evolution_per_hour()],
            [self._plot_visit_evolution_per_day()]
        ]), CDN)
        with open("/tmp/templates/evolution_charts.html", "w+") as file_handler:
            file_handler.write("{% raw %}")
            file_handler.write(html)
            file_handler.write("{% endraw %}")

    def _plot_visit_count_per_genotype(self):
        """ Returns a plot with the total number visits for each genotype """
        genotypes = []
        visits = []
        for name in self.genotypes_dfs:
            genotypes.append(name)
            visits.append(len(self.genotypes_dfs[name]))
        data = {'genotypes': genotypes,
                'visits': visits,
                'color': viridis(len(genotypes))}  # TODO palette limited to 256 colors. Need to cycle
        source = ColumnDataSource(data=data)
        sorted_genotypes = sorted(genotypes, key=lambda x: visits[genotypes.index(x)])
        plot = figure(x_range=sorted_genotypes, plot_height=400, title="Number of visits per genotype",
                      tools="pan, wheel_zoom, box_zoom, reset, save",
                      tooltips=[("Genotype", "@genotypes"), ("Total visits", "@visits")], toolbar_sticky=False,
                      margin=(30, 0, 30, 0))
        plot.vbar(x="genotypes", top="visits", width=0.9, source=source, color="color")
        plot.xgrid.grid_line_color = None
        plot.y_range.start = 0
        plot.xaxis.major_label_orientation = pi / 4
        plot.toolbar.logo = None
        plot.xaxis.axis_label = "Genotype"
        plot.yaxis.axis_label = "Number of visits"
        return plot

    def _plot_visit_duration_cumsum_per_genotype(self):
        """ Returns a plot with the total duration of all visits for each genotype """
        pollinators = self.final_joined_df['Tag Alias'].unique().tolist()
        genotypes = self.final_joined_df['Genotype'].unique().tolist()
        data = {"genotypes": genotypes}
        colors = list(viridis(len(pollinators)))
        for pollinator in pollinators:
            list_of_data = []
            for genotype in genotypes:
                series_for_sum = self.final_joined_df[
                    self.final_joined_df['Tag Alias'] == pollinator]  # filter by pollinator
                series_for_sum = series_for_sum[series_for_sum["Genotype"] == genotype]  # filter by genotype
                list_of_data.append(series_for_sum["Visit Duration"].sum())  # sum all the values of that set
            data[pollinator] = list_of_data
        plot = figure(x_range=genotypes, plot_height=400, title="Total duration (sum) of all visits per genotype",
                      tools="pan, wheel_zoom, box_zoom, reset, save", tooltips="Pollinator $name: @$name sec",
                      toolbar_sticky=False, margin=(15, 0, 15, 0))
        plot.vbar_stack(pollinators, x='genotypes', width=0.9, color=colors, source=data)
        plot.y_range.start = 0
        plot.x_range.range_padding = 0.1
        plot.xgrid.grid_line_color = None
        plot.axis.minor_tick_line_color = None
        plot.outline_line_color = None
        plot.xaxis.major_label_orientation = pi / 4
        plot.toolbar.logo = None
        plot.xaxis.axis_label = "Genotype"
        plot.yaxis.axis_label = "Total time of visits"
        return plot

    def _plot_average_visit_duration_per_genotype(self):
        """ Returns a plot with the average visit duration for each genotype """
        genotypes = []
        means = []
        for name in self.genotypes_dfs:
            genotypes.append(name)
            means.append(round(self.genotypes_dfs[name]["Visit Duration"].mean(), 2))
        data = {'genotypes': genotypes,
                'means': means,
                'color': viridis(len(genotypes))}
        source = ColumnDataSource(data=data)
        sorted_genotypes = sorted(genotypes, key=lambda x: means[genotypes.index(x)])
        plot = figure(x_range=sorted_genotypes, plot_height=400, title="Average duration of visits per genotype",
                      tools="pan, wheel_zoom, box_zoom, reset, save",
                      tooltips=[("Genotype", "@genotypes"), ("Average visit (sec)", "@means")], toolbar_sticky=False,
                      margin=(30, 0, 30, 0))
        plot.vbar(x="genotypes", top="means", width=0.9, source=source, color="color")
        plot.xgrid.grid_line_color = None
        plot.y_range.start = 0
        plot.xaxis.major_label_orientation = pi / 4
        plot.toolbar.logo = None
        plot.xaxis.axis_label = "Genotype"
        plot.yaxis.axis_label = "Average visit duration"
        return plot

    def _plot_visit_count_per_pollinator(self):
        """Returns a plot with the total number visits of each pollinator"""
        pollinators = self.final_joined_df['Tag Alias'].unique().tolist()
        visits = []
        for pollinator in pollinators:
            series_for_count = self.final_joined_df[self.final_joined_df['Tag Alias'] == pollinator]
            visits.append(len(series_for_count["Visit Duration"]))
        data = {'pollinators': pollinators,
                'visits': visits,
                'color': viridis(len(pollinators))}
        source = ColumnDataSource(data=data)
        sorted_pollinators = sorted(pollinators, key=lambda x: visits[pollinators.index(x)])
        plot = figure(x_range=sorted_pollinators, plot_height=400, title="Number of visits of each pollinator",
                      tools="pan, wheel_zoom, box_zoom, reset, save",
                      tooltips=[("Pollinator", "@pollinators"), ("Total visits", "@visits")], toolbar_sticky=False,
                      margin=(30, 0, 30, 0))
        plot.vbar(x="pollinators", top="visits", width=0.9, source=source, color="color")
        plot.xgrid.grid_line_color = None
        plot.y_range.start = 0
        plot.xaxis.major_label_orientation = pi / 4
        plot.toolbar.logo = None
        plot.xaxis.axis_label = "Pollinator"
        plot.yaxis.axis_label = "Number of visits"
        return plot

    def _plot_average_visit_duration_per_pollinator(self):
        """ Returns a plot with the average visit duration for each pollinator """
        pollinators = self.final_joined_df['Tag Alias'].unique().tolist()
        means = []
        for pollinator in pollinators:
            series_for_mean = self.final_joined_df[self.final_joined_df['Tag Alias'] == pollinator]
            means.append(round(series_for_mean["Visit Duration"].mean(), 2))
        data = {'pollinators': pollinators,
                'means': means,
                'color': viridis(len(pollinators))}
        source = ColumnDataSource(data=data)
        plot = figure(x_range=pollinators, plot_height=400, title="Average duration of visits per pollinator",
                      tools="pan, wheel_zoom, box_zoom, reset, save",
                      tooltips=[("Pollinator", "@pollinators"), ("Average visit (sec)", "@means")],
                      toolbar_sticky=False, margin=(15, 0, 15, 0))
        plot.vbar(x="pollinators", top="means", width=0.9, source=source, color="color")
        plot.xgrid.grid_line_color = None
        plot.y_range.start = 0
        plot.xaxis.major_label_orientation = pi / 4
        plot.toolbar.logo = None
        plot.xaxis.axis_label = "Pollinator"
        plot.yaxis.axis_label = "Average visit duration"
        return plot

    def _plot_visit_duration_cumsum_per_pollinator(self):
        """ Returns a plot with the sum of all visit durations for each pollinator """
        pollinators = self.final_joined_df['Tag Alias'].unique().tolist()
        genotypes = self.final_joined_df['Genotype'].unique().tolist()
        data = {"pollinators": pollinators}
        colors = list(viridis(len(genotypes)))
        for genotype in genotypes:
            list_of_data = []
            for pollinator in pollinators:
                series_for_sum = self.final_joined_df[
                    self.final_joined_df['Tag Alias'] == pollinator]  # filter by pollinator
                series_for_sum = series_for_sum[series_for_sum["Genotype"] == genotype]  # filter by genotype
                list_of_data.append(series_for_sum["Visit Duration"].sum())  # sum all the values of that  set
            data[genotype] = list_of_data
        plot = figure(x_range=pollinators, plot_height=400, title="Total duration (sum) of all visits per pollinator",
                      tools="pan, wheel_zoom, box_zoom, reset, save", tooltips="@pollinators on $name: @$name sec",
                      toolbar_sticky=False, margin=(15, 0, 15, 0))
        plot.vbar_stack(genotypes, x='pollinators', width=0.9, color=colors, source=data,
                        legend_label=genotypes)
        plot.y_range.start = 0
        plot.x_range.range_padding = 0.1
        plot.xgrid.grid_line_color = None
        plot.axis.minor_tick_line_color = None
        plot.outline_line_color = None
        plot.legend.location = "top_right"
        plot.legend.background_fill_alpha = 0.8
        plot.xaxis.major_label_orientation = pi / 4
        plot.toolbar.logo = None
        plot.xaxis.axis_label = "Pollinator"
        plot.yaxis.axis_label = "Total time visiting"
        return plot

    def _plot_visit_evolution_per_hour(self):
        """ Returns a plot with the evolution of number of visits per hour """
        sorted_df = self.final_joined_df.sort_values(by=['Scan Date and Time'])
        datetime_df = sorted_df.resample('H', on='Scan Date and Time').count()
        datetime_df["visits_count"] = datetime_df["Visit Duration"]
        datetime_df = datetime_df[['visits_count']]
        x = datetime_df.index
        y = datetime_df["visits_count"]
        data = {'dates': x,
                'visits_count': y}
        source = ColumnDataSource(data=data)
        custom_tooltips = HoverTool(
            tooltips=[('Date', '@dates{%d/%m/%Y}'), ('Time', '@dates{%H:00 - %H:59}'),
                      ('Visits this hour', '@visits_count')],
            formatters={'@dates': 'datetime'},
            mode='vline',
        )
        plot = figure(plot_height=400, x_axis_type="datetime", title="Evolution of visits grouped by hour",
                      tools=[custom_tooltips, "pan, wheel_zoom, box_zoom, reset, save"], toolbar_sticky=False,
                      margin=(30, 0, 30, 0))
        plot.line(x='dates', y='visits_count', line_width=2, line_color="#168756", source=source)
        plot.xaxis.axis_label = "Date & time"
        plot.yaxis.axis_label = "Number of visits"
        plot.xaxis.formatter = DatetimeTickFormatter(days="%e/%m")
        plot.toolbar.logo = None
        return plot

    def _plot_visit_evolution_per_day(self):
        """ Returns a plot with the evolution of number of visits per day """
        sorted_df = self.final_joined_df.sort_values(by=['Scan Date and Time'])
        datetime_df = sorted_df.resample('D', on='Scan Date and Time').count()
        datetime_df["visits_count"] = datetime_df["Visit Duration"]
        datetime_df = datetime_df[['visits_count']]
        x = datetime_df.index
        y = datetime_df["visits_count"]
        data = {'dates': x,
                'visits_count': y}
        source = ColumnDataSource(data=data)
        plot = figure(plot_height=400, x_axis_type="datetime", title="Evolution of visits grouped by day",
                      tools="pan, wheel_zoom, box_zoom, reset, save", toolbar_sticky=False, margin=(15, 0, 15, 0))
        plot.vbar(x='dates', top='visits_count', color="#168756", line_alpha=0.25, fill_alpha=0.25,
                  width=timedelta(days=0.5), source=source)
        lines = plot.line(x='dates', y='visits_count', line_width=2, line_color="#168756", source=source)
        custom_tooltips = HoverTool(
            tooltips=[('Date', '@dates{%d/%m/%Y}'), ('Visits this day', '@visits_count')],
            formatters={'@dates': 'datetime'},
            mode='vline',
            renderers=[lines]
        )
        plot.add_tools(custom_tooltips)
        plot.xaxis.axis_label = "Date & time"
        plot.yaxis.axis_label = "Number of visits"
        plot.xaxis.formatter = DatetimeTickFormatter(days="%e/%m")
        plot.toolbar.logo = None
        return plot
