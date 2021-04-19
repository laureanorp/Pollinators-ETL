from pollinators_ETL import Pipeline

# Input variables that will be frontend UI elements (textbox, checkboxes, etc)
csv_file_path = input("Enter path for csv file (relative to current dir: ") or "imports/Rawdata_enero.csv"

# Parameters
filter_start_datetime = input("Start date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                              "\nLeave this input blank if you don't want to filter by date: ")

filter_end_datetime = input("End date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                            "\nLeave this input blank if you don't want to filter by date: ")

max_visit_duration = input(
    "Choose the maximum time in seconds that is considered to be the same visit between a signal and the next."
    "\nDefault is 7: ") or 7

round_or_truncate = input("Choose to round (1, default), truncate (2): ") or "1"

all_antennas_visited = input("Choose to include all pollinators (1, default) or only those that have "
                             "visited all antennas of the experiment (2): ") or "1"

# Instance the Pipeline class
pipeline_1 = Pipeline(csv_file_path)

# input parameters
pipeline_1.input_parameters_of_run(max_visit_duration, filter_start_datetime, filter_end_datetime, round_or_truncate,
                                   all_antennas_visited, [], [])

# Run the main process of the pipeline
pipeline_1.run_pipeline()

# Some outputs for testing
# print(pipeline_1.antennas_dfs["antenna_1"])
# Export antennas_dfs to an excel file
# pipeline_1.export_dataframes_to_excel()
pipeline_1.plot_avg_visit_duration()
