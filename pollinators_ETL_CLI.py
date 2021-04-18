from pollinators_ETL import Pipeline

# Input variables that will be frontend UI elements (textbox, checkboxes, etc)
# Default values are here temporary, should be default values in each function or other workarounds
filter_start_datetime = input("Start date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                              "\nLeave this input blank if you don't want to filter by date: ")

filter_end_datetime = input("End date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                            "\nLeave this input blank if you don't want to filter by date: ")

max_visit_duration = int(input(
    "Choose them maximum time in seconds that is considered to be the same visit between a signal and the next: ") or 7)

round_or_truncate = input("Choose to round (1, default), truncate (2) or leave (3) ms of the timestamps: ") or "1"

all_antennas_visited = input("Choose to include all pollinators (1, default) or only those that have "
                             "visited all antennas of the experiment (2): ") or "1"

# Instance the Pipeline class
pipeline_1 = Pipeline("imports/Rawdata_enero.csv")


# Run the main process of the pipeline
pipeline_1.run_pipeline(max_visit_duration, filter_start_datetime, filter_end_datetime, round_or_truncate,
                        all_antennas_visited)

# Remove unnecessary columns and rows
pipeline_1.simplify_dataframes()

print(pipeline_1.antennas_dfs["antenna_1"])

# Export antennas_dfs to an excel file
pipeline_1.export_dataframes_to_excel()

pipeline_1.plot_avg_visit_duration()

# pipeline_1.concatenate_antennas_dfs(["antenna_1", "antenna_2"])
# print(pipeline_1.antennas_dfs["antenna_1_antenna_2"])
