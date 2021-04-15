from pollinators_ETL import Pipeline

# Input variables that will be frontend UI elements (textbox, checkboxes, etc)
# Default values are here temporary, should be default values in each function or other workarounds
filter_start_datetime = input("Start date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                              "\nLeave this input blank if you don't want to filter by date: ")

filter_end_datetime = input("End date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                            "\nLeave this input blank if you don't want to filter by date: ")

round_or_truncate = input("Choose to round (1, default), truncate (2) or leave (3) ms of the timestamps: ") or "1"

all_antennas_visited = input("Choose to include all pollinators (1, default) or only those that have "
                             "visited all antennas of the experiment (2): ") or "1"

pipeline_1 = Pipeline("data/Rawdata_enero.csv")

print(pipeline_1.run_pipeline(7, filter_start_datetime, filter_end_datetime, round_or_truncate,
                      all_antennas_visited)["antenna_1"])
