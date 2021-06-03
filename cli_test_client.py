from rfid_pollinators_pipeline import Pipeline, Plot

# Input variables that will be frontend UI elements (textbox, checkboxes, etc)
excel_files = ["12-13.05.21.xlsx", "14-17.05.21.xlsx"]

# Instance the Pipeline class
pipeline = Pipeline(excel_files)
pipeline.preprocessing_of_data()

# Send Genotypes
pipeline.input_genotypes_data([
    {1: "Genotype A", 3: "Genotype A", 4: "Genotype B", 6: "Genotype C", 9: "Genotype C",
     10: "Genotype D", 12: "Genotype D", 13: "Genotype E", 14: "Genotype E",
     15: "Genotype F", 16: "Genotype F"},
    {2: "Genotype A", 5: "Genotype A", 6: "Genotype B", 9: "Genotype A", 14: "Genotype A",
     15: "Genotype D", 16: "Genotype F"}])

# Input Parameters
max_time_between_signals = "7"
round_or_truncate = "round"
filter_tags_by_visited_genotypes = "False"
pollinators_to_remove = []
visited_genotypes_required = ""
flowers_per_antenna = "7"
filter_start_datetime = ""
filter_end_datetime = ""

# Send parameters
pipeline.input_parameters_of_run(max_time_between_signals, round_or_truncate, pollinators_to_remove,
                                 flowers_per_antenna, filter_tags_by_visited_genotypes, visited_genotypes_required,
                                 filter_start_datetime, filter_end_datetime)

# Run the main process of the pipeline
pipeline.run_pipeline()
plots = Plot(pipeline.genotypes_dfs)
plots.lay_out_plots_to_html()

# Print some output for testing
print(pipeline.genotypes_dfs)
