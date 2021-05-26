from typing import List, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from bokeh.embed import file_html
from bokeh.io import output_file
from bokeh.layouts import layout
from bokeh.models import (BasicTicker, ColorBar, ColumnDataSource,
                          LinearColorMapper, PrintfTickFormatter, )
from bokeh.palettes import viridis
from bokeh.plotting import figure
from bokeh.resources import CDN
from bokeh.sampledata.unemployment1948 import data as data_heat_map
from bokeh.transform import transform
from math import pi


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

    def input_parameters_of_run(self, max_time_between_signals: int, round_or_truncate: str,
                                pollinators_to_remove: List[str], flowers_per_antenna: int,
                                filter_tags_by_visited_genotypes: str, visited_genotypes_required=None,
                                filter_start_datetime: str = "", filter_end_datetime: str = ""):
        """ Method for introducing all the necessary parameters for the pipeline run """
        if visited_genotypes_required is None:
            visited_genotypes_required = []
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

    def plot_avg_visit_duration(self):  # TODO remove on production
        """
        Calculates the mean of no null visit durations for each genotype.
        Then plots that average duration for each genotype using a bar plot.
        """
        list_of_means = []
        for genotype_key, genotype_df in self.genotypes_dfs.items():
            no_null = genotype_df[genotype_df["Visit Duration"] != 0]
            list_of_means.append(round(no_null["Visit Duration"].mean(), 2))
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
        self.stats = None

    def lay_out_plots_to_html(self):
        """ Saves all the plots generated in this Class to one HTML file with a certain layout"""
        output_file("templates/layout.html")
        html = file_html(layout([
            [self._plot_visits_per_genotype()],
            [self._plot_visits_cumsum_per_genotype()],
            [self._plot_visit_duration_per_genotype()],
            [self._plot_visit_duration_per_pollinator()],
            [self._plot_visit_cumsum_per_pollinator()],
        ]), CDN)
        with open("templates/layout.html", "w+") as file_handler:
            file_handler.write(html)

    def compute_statistics(self):
        """ Assigns different stats to a dictionary that is later returned to the client """
        self.stats = {"average_visit_duration": self._average_visit_duration()}

    def _plot_visits_per_genotype(self):
        """ Returns a plot with the total number visits for each genotype """
        genotypes = []
        visits = []
        for key in self.genotypes_dfs:
            genotypes.append(key)
            visits.append(self.genotypes_dfs[key].size)
        data = {'genotypes': genotypes,
                'visits': visits,
                'color': viridis(len(genotypes))}  # TODO palette limited to 256 colors. Need to cycle
        source = ColumnDataSource(data=data)
        sorted_genotypes = sorted(genotypes, key=lambda x: visits[genotypes.index(x)])
        plot = figure(x_range=sorted_genotypes, plot_height=400, title="Number of visits per genotype",
                      tools="pan, wheel_zoom, box_zoom, reset, save",
                      tooltips=[("Genotype", "@genotypes"), ("Total visits", "@visits")], toolbar_sticky=False)
        plot.vbar(x="genotypes", top="visits", width=0.9, source=source, color="color")
        plot.xgrid.grid_line_color = None
        plot.y_range.start = 0
        plot.xaxis.major_label_orientation = pi / 4
        plot.toolbar.logo = None
        return plot

    def _plot_visits_cumsum_per_genotype(self):
        """ Returns a plot with the total duration of all visits for each genotype """
        dataframes = list(self.genotypes_dfs.values())
        whole_dataframe = pd.concat(dataframes)
        pollinators = whole_dataframe['DEC Tag ID'].unique().tolist()
        genotypes = whole_dataframe['Genotype'].unique().tolist()
        data = {"genotypes": genotypes}
        colors = list(viridis(len(pollinators)))
        for pollinator in pollinators:
            list_of_data = []
            for genotype in genotypes:
                series_for_sum = whole_dataframe[whole_dataframe['DEC Tag ID'] == pollinator]  # filter by pollinator
                series_for_sum = series_for_sum[series_for_sum["Genotype"] == genotype]  # filter by genotype
                list_of_data.append(series_for_sum["Visit Duration"].sum())  # sum all the values of that  set
            data[pollinator] = list_of_data
        plot = figure(x_range=genotypes, plot_height=400, title="Total duration (sum) of all visits per genotype",
                      tools="pan, wheel_zoom, box_zoom, reset, save", tooltips="$name: @$name sec",
                      toolbar_sticky=False)
        plot.vbar_stack(pollinators, x='genotypes', width=0.9, color=colors, source=data)
        plot.y_range.start = 0
        plot.x_range.range_padding = 0.1
        plot.xgrid.grid_line_color = None
        plot.axis.minor_tick_line_color = None
        plot.outline_line_color = None
        plot.xaxis.major_label_orientation = pi / 4
        plot.toolbar.logo = None
        return plot

    def _plot_visit_duration_per_genotype(self):
        """ Returns a plot with the average visit duration for each genotype """
        genotypes = []
        means = []
        for key in self.genotypes_dfs:
            genotypes.append(key)
            means.append(round(self.genotypes_dfs[key]["Visit Duration"].mean(), 2))
        data = {'genotypes': genotypes,
                'means': means,
                'color': viridis(len(genotypes))}
        source = ColumnDataSource(data=data)
        sorted_genotypes = sorted(genotypes, key=lambda x: means[genotypes.index(x)])
        plot = figure(x_range=sorted_genotypes, plot_height=400, title="Average duration of visits per genotype",
                      tools="pan, wheel_zoom, box_zoom, reset, save",
                      tooltips=[("Genotype", "@genotypes"), ("Average visit (sec)", "@means")], toolbar_sticky=False)
        plot.vbar(x="genotypes", top="means", width=0.9, source=source, color="color")
        plot.xgrid.grid_line_color = None
        plot.y_range.start = 0
        plot.xaxis.major_label_orientation = pi / 4
        plot.toolbar.logo = None
        return plot

    def _plot_visit_duration_per_pollinator(self):
        """ Returns a plot with the average visit duration for each pollinator """
        dataframes = list(self.genotypes_dfs.values())
        whole_dataframe = pd.concat(dataframes)
        pollinators = whole_dataframe['DEC Tag ID'].unique().tolist()
        means = []
        for pollinator in pollinators:
            series_for_mean = whole_dataframe[whole_dataframe['DEC Tag ID'] == pollinator]
            means.append(round(series_for_mean["Visit Duration"].mean(), 2))
        data = {'pollinators': pollinators,
                'means': means,
                'color': viridis(len(pollinators))}
        source = ColumnDataSource(data=data)
        plot = figure(x_range=pollinators, plot_height=400, title="Average duration of visits per pollinator",
                      tools="pan, wheel_zoom, box_zoom, reset, save",
                      tooltips=[("Pollinator", "@pollinators"), ("Average visit (sec)", "@means")],
                      toolbar_sticky=False)
        plot.vbar(x="pollinators", top="means", width=0.9, source=source, color="color")
        plot.xgrid.grid_line_color = None
        plot.y_range.start = 0
        plot.xaxis.major_label_orientation = pi / 4
        plot.toolbar.logo = None
        return plot

    def _plot_visit_cumsum_per_pollinator(self):
        """ Returns a plot with the sum of all visit durations for each pollinator """
        dataframes = list(self.genotypes_dfs.values())
        whole_dataframe = pd.concat(dataframes)
        pollinators = whole_dataframe['DEC Tag ID'].unique().tolist()
        genotypes = whole_dataframe['Genotype'].unique().tolist()
        data = {"pollinators": pollinators}
        colors = list(viridis(len(genotypes)))
        for genotype in genotypes:
            list_of_data = []
            for pollinator in pollinators:
                series_for_sum = whole_dataframe[whole_dataframe['DEC Tag ID'] == pollinator]  # filter by pollinator
                series_for_sum = series_for_sum[series_for_sum["Genotype"] == genotype]  # filter by genotype
                list_of_data.append(series_for_sum["Visit Duration"].sum())  # sum all the values of that  set
            data[genotype] = list_of_data
        plot = figure(x_range=pollinators, plot_height=400, title="Total duration (sum) of all visits per pollinator",
                      tools="pan, wheel_zoom, box_zoom, reset, save", tooltips="@pollinators on $name: @$name sec",
                      toolbar_sticky=False)
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
        return plot

    def _average_visits_heat_map(self):
        """ WIP """
        dataframes = list(self.genotypes_dfs.values())
        whole_dataframe = pd.concat(dataframes)
        pollinators = whole_dataframe['DEC Tag ID'].unique().tolist()
        genotypes = whole_dataframe['Genotype'].unique().tolist()
        data = {"pollinators": pollinators}
        for genotype in genotypes:
            list_of_data = []
            for pollinator in pollinators:
                series_for_sum = whole_dataframe[whole_dataframe['DEC Tag ID'] == pollinator]  # filter by pollinator
                series_for_sum = series_for_sum[series_for_sum["Genotype"] == genotype]  # filter by genotype
                list_of_data.append(series_for_sum["Visit Duration"].sum())  # sum all the values of that  set
            data[genotype] = list_of_data

        data_heat_map.Year = data_heat_map.Year.astype(str)
        data = data_heat_map.set_index('Year')
        data.drop('Annual', axis=1, inplace=True)
        data.columns.name = 'Month'

        # reshape to 1D array or rates with a month and year for each row.
        df = pd.DataFrame(data.stack(), columns=['rate']).reset_index()

        source = ColumnDataSource(df)

        # this is the colormap from the original NYTimes plot
        colors = ["#75968f", "#a5bab7", "#c9d9d3", "#e2e2e2", "#dfccce", "#ddb7b1", "#cc7878", "#933b41", "#550b1d"]
        mapper = LinearColorMapper(palette=colors, low=df.rate.min(), high=df.rate.max())

        plot = figure(plot_width=800, plot_height=300, title="US unemployment 1948—2016",
                      x_range=list(data.index), y_range=list(reversed(data.columns)),
                      tools="", x_axis_location="above")

        plot.rect(x="Year", y="Month", width=1, height=1, source=source,
                  line_color=None, fill_color=transform('rate', mapper))

        color_bar = ColorBar(color_mapper=mapper,
                             ticker=BasicTicker(desired_num_ticks=len(colors)),
                             formatter=PrintfTickFormatter(format="%d%%"))

        plot.add_layout(color_bar, 'right')

        plot.axis.axis_line_color = None
        plot.axis.major_tick_line_color = None
        plot.axis.major_label_text_font_size = "7px"
        plot.axis.major_label_standoff = 0
        plot.xaxis.major_label_orientation = 1.0
        plot.toolbar.logo = None
        return plot

    def _average_visit_duration(self) -> int:
        # Not per genotype, avg of whole dataset
        dataframes = list(self.genotypes_dfs.values())
        whole_dataframe = pd.concat(dataframes)
        mean = round(whole_dataframe["Visit Duration"].mean(), 2)
        return mean
