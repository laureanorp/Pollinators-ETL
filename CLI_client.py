from pollinators_ETL import Pipeline

# Input variables that will be frontend UI elements (textbox, checkboxes, etc)
csv_file_path = input("Enter path for csv file (relative to current dir): ") or "imports/Rawdata_enero.csv"

# Parameters
filter_start_datetime = input("Start date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                              "\nLeave this input blank if you don't want to filter by date: ")

filter_end_datetime = input("End date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                            "\nLeave this input blank if you don't want to filter by date: ")

max_visit_duration = input(
    "Choose the maximum time in seconds that is considered to be the same visit between a signal and the next."
    "\nDefault is 7: ") or 7

round_or_truncate = input("Choose to round (default), truncate: ") or "round"

# Bad: "True" string is not True bool
filter_tags_by_visited_antennas = input("Filter tags by visited antennas? (True/False): ") or False

antennas_to_concat = input("Antennas to concat (python list format): ") or []

pollinators_to_remove = input("Pollinators to remove from the data: ") or []

visited_antennas_required = input("Which antennas are required required? (python list format): ") or []

flowers_per_antenna = input("Flowers per antenna: ") or 1

# Instance the Pipeline class
pipeline_1 = Pipeline(csv_file_path)

# input parameters
pipeline_1.input_parameters_of_run(max_visit_duration, filter_start_datetime, filter_end_datetime, round_or_truncate,
                                   filter_tags_by_visited_antennas, antennas_to_concat, pollinators_to_remove,
                                   visited_antennas_required, flowers_per_antenna)

# Run the main process of the pipeline
pipeline_1.run_pipeline()

# Some outputs for testing
print(pipeline_1.antennas_dfs["antenna_1"])
# Export antennas_dfs to an excel file
pipeline_1.export_dataframes_to_excel()
pipeline_1.plot_avg_visit_duration()
