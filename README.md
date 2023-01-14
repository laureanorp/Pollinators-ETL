# RFID Pollinators Pipeline

<img width="200" alt="logo" src="https://user-images.githubusercontent.com/14150766/193466545-ec3239bc-d061-43ff-a9d4-fcce0bad55a8.png">

RFID Pollinators is a web application for processing certain experimental data from Biomark(R) RFID systems. MAde with Python, it consists on a data-processing pipeline made with `pandas` + `Bokeh` and a web app using Flask and Bootstrap. Right now this app is deployed to Google App Engine, available [on this link](https://rfid-pollinators.ew.r.appspot.com).

<img width="800" alt="image" src="https://user-images.githubusercontent.com/14150766/193462330-cfb027e1-0b3b-46e8-8eeb-859e4fe178b4.png">

## More background on the project

Inside a controlled environment, bumblebees (pollinators) marked with passive RFID tags interact with different plants. Those plants have RFID antennas that detect the bumblebees when they are close. Those signals are registered by Biomark(R) RFID reader, passed into the reader software, and saved into an Excel file.

![Invernadero](https://user-images.githubusercontent.com/14150766/193462279-e78cc507-4610-40a4-9f45-b8e7126d11d4.png)

Those excel files are the input of this application. Information of individual signals (one pollinator on one antenna on a timestamp) is converted to a "visit" with a certain duration. The user can control the different parameters which affect the results, as well as deciding which plants form different groups depending of its genotype. So, the final result is grouped by genotypes. Plenty of processing is made to the data, so the final result is a dictionary of pandas dataframes, where each dataframe corresponds to a different genotype and includes all the visits of those antennas.

![Pipeline ETL](https://user-images.githubusercontent.com/14150766/193462285-f50e3466-18f1-4031-ab43-b50be162ecdc.png)

## Run the project locally

1. Clone or download this repo
2. Create a venv and activate it
3. `pip install -r requirements`
4. `python main.py`
5. Visit http://localhost:5000 on your browser

Have in mind that this application will need to write files on /tmp folder.

## Using only the pipeline

If you want to use only the pipeline for making calculations, there are some useful public methods. But of course, it's better to use the full app. The process is pretty much summed up in `cli_test_client.py`. Some examples on how to interact with the pipeline:

```python
# Import the two classes
from rfid_pollinators_pipeline import Pipeline, Plot

# Instance the Pipeline class
pipeline = Pipeline(list of excel files)

# Preprocess the data to get some information...
pipeline.preprocessing_of_data()

# ...and retrieve that useful info about the preprocessed data
pipeline.excel_files  # list of names of each excel file (experiment) uploaded
pipeline.dates_of_dfs  # dates of experiment
pipeline.antennas_info  # which antennas are present in each experiment

# Send genotypes to pipeline
pipeline.input_genotypes_data([
    {antenna_number: "Genotype name", antenna_number: "Genotype name"}])

# Send parameters to pipeline
pipeline.input_parameters_of_run(max_time_between_signals, round_or_truncate, pollinators_to_remove,
                                 filter_tags_by_visited_genotypes, visited_genotypes_required, filter_start_datetime,
                                 filter_end_datetime)

# Run the main process of the pipeline
pipeline.run_pipeline()

# Create plots with Bokeh
plots = Plot(pipeline.genotypes_dfs)
# And save them to a HTML template
plots.lay_out_plots_to_html()

After running the pipeline, new info is available_
pipeline.statistics  # dict with several stats about the data
pipeline.pollinators_aliases  # alias (a number) assigned to each pollinator
pipeline.genotypes_names  # list of names of the final tables (the different genotypes)
pipeline.genotypes_dfs  # final dataframes with all the data
```

## License
[Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
