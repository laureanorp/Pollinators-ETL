from pollinators_ETL import Pipeline, Plot

# Input variables that will be frontend UI elements (textbox, checkboxes, etc)
csv_file_path = input("Enter path for csv file (relative to current dir): ") or ["12-13.05CSV.csv",
                                                                                 "14-17.05.21CSV.csv"]

# Parameters
filter_start_datetime = input("Start date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                              "\nLeave this input blank if you don't want to filter by date: ")

filter_end_datetime = input("End date and time for filtering the dataset. Use YYYY-MM-DD hh:mm:ss format."
                            "\nLeave this input blank if you don't want to filter by date: ")

max_time_between_signals = input(
    "Choose the maximum time in seconds that is considered to be the same visit between a signal and the next."
    "\nDefault is 7: ") or 7

round_or_truncate = input("Choose to round (default), truncate: ") or "round"

filter_tags_by_visited_genotypes = input("Filter tags by visited antennas? (True/False): ") or "False"

pollinators_to_remove = input("Pollinators to remove from the data: ") or []

visited_genotypes_required = input("Which antennas are required required? (python list format): ") or ["Genotype A",
                                                                                                       "Genotype B",
                                                                                                       "Genotype C"]

flowers_per_antenna = input("Flowers per antenna: ") or 1

# Instance the Pipeline class
pipeline_1 = Pipeline(csv_file_path)

pipeline_1.preprocessing_of_data()

# Input genotypes
pipeline_1.input_genotypes_data([{1: "Genotype A", 3: "Genotype A", 4: "Genotype A", 6: "Genotype B", 9: "Genotype B",
                                  10: "Genotype B", 12: "Genotype B", 13: "Genotype C", 14: "Genotype C",
                                  15: "Genotype C", 16: "Genotype C"},
                                 {2: "Genotype A", 5: "Genotype A", 6: "Genotype A", 9: "Genotype B", 14: "Genotype B",
                                  15: "Genotype C", 16: "Genotype C"}])

pipeline_1.add_genotypes_and_join_df()

# Input parameters
pipeline_1.input_parameters_of_run(filter_start_datetime, filter_end_datetime, max_time_between_signals,
                                   round_or_truncate, filter_tags_by_visited_genotypes, visited_genotypes_required,
                                   pollinators_to_remove, flowers_per_antenna)

# Run the main process of the pipeline
pipeline_1.run_pipeline()

# Some outputs for testing
print(pipeline_1.genotypes_dfs["Genotype A"])
# Export antennas_dfs to an excel file
# pipeline_1.export_dataframes_to_excel()
# pipeline_1.plot_avg_visit_duration()

plots_1 = Plot(pipeline_1.genotypes_dfs)
plots_1.lay_out_plots_to_html()
