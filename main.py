import os
from typing import List, Dict

from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from pollinators_ETL import Pipeline

UPLOAD_FOLDER = "server_uploads"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def genotypes_form_to_list(form_dict: Dict[str, str]) -> List[Dict[int, str]]:
    """ Transforms the dict coming from the input_genotypes HTML form into a list of dicts """
    nested_genotypes = {}
    for key in form_dict:  # form_dict = request.form
        split_key = key.split(".csv ")  # ["file1", "1"]
        nested_genotypes[split_key[0]] = {}  # 1st loop creates the necessary dictionaries
    for key in form_dict:  # form_dict = request.form
        split_key = key.split(".csv ")  # ["file1", "1"]
        nested_genotypes[split_key[0]][int(split_key[1])] = form_dict[key]  # 2nd loop assigns the values to each dict
    genotypes_of_each_experiment = []
    for key in nested_genotypes:
        genotypes_of_each_experiment.append(nested_genotypes[key])  # ignore the dict keys, just add to a list in order
    return genotypes_of_each_experiment


@app.route('/home')
def home():
    """
    Main home screen for the web app.
    Returns the HTMl template where the CSV files are uploaded.
    """
    return render_template('home.html')


@app.route('/upload', methods=['POST', 'GET'])
def upload():
    """ File uploader that supports multiple files """
    file_names = []
    if request.method == 'POST':
        csv_files = request.files.getlist('csv_files')
        for file in csv_files:
            secure_file_name = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_file_name))
            file_names.append(secure_file_name)
        global pipeline
        pipeline = Pipeline(file_names)
        pipeline.preprocessing_of_data()
        antennas_info = pipeline.antennas_info
        return render_template('input_genotypes.html', file_names=file_names,
                               antennas_info=antennas_info)  # TODO extract date from df
    if request.method == 'GET':  # TODO what goes here?
        csv_files = request.files.getlist('csv_files')
        for file in csv_files:
            secure_file_name = secure_filename(file.filename)
            file_names.append(secure_file_name)
        return render_template('input_genotypes.html', file_name=file_names)


@app.route('/input-genotypes', methods=['POST', 'GET'])
def input_genotypes():
    if request.method == 'POST':
        genotypes = genotypes_form_to_list(request.form)
        pipeline.input_genotypes_data(
            [{1: "Genotype A", 3: "Genotype A", 4: "Genotype A", 6: "Genotype B", 9: "Genotype B",
              10: "Genotype B", 12: "Genotype B", 13: "Genotype C", 14: "Genotype C",
              15: "Genotype C", 16: "Genotype C"},
             {2: "Genotype A", 5: "Genotype A", 6: "Genotype A", 9: "Genotype B", 14: "Genotype B",
              15: "Genotype C", 16: "Genotype C"}])  # TODO parameters
        pipeline.add_genotypes_and_join_df()
        return render_template('input_parameters.html')
    elif request.method == 'GET':
        return render_template('input_parameters.html')


@app.route('/input-parameters', methods=['POST', 'GET'])
def input_parameters():
    if request.method == 'POST':
        # Introduce the parameters of the pipeline
        parameters = [request.form["start_date_filter"], request.form["end_date_filter"],
                      request.form["max_time_between_signals"], request.form["round_or_truncate"],
                      request.form["filter_tags_by_visited_genotypes"], request.form["visited_genotypes_required"],
                      request.form["pollinators_to_remove"], request.form["flowers_per_antenna"]]
        pipeline.input_parameters_of_run("", "", 7, "round", "True", [], [], 1)  # TODO parameters
        # Run the main process of the pipeline
        pipeline.run_pipeline()
        return render_template('pipeline_results.html')
    elif request.method == 'GET':
        return render_template('pipeline_results.html')


if __name__ == '__main__':
    app.run()
