import os
from shutil import copy
from typing import List, Dict

from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

from pipeline_utilities import download_and_deserialize_pipeline_from_gcs, is_pipeline_present, are_plots_files_present, \
    serialize_and_upload_pipeline_to_gcs, delete_pipeline_file
from rfid_pollinators_pipeline import Pipeline, Plot

UPLOAD_FOLDER = "/tmp/server_uploads"


def create_tmp_folders_for_templates():
    """ Copies the original templates to /tmp so results can be written to that folder in production"""
    try:
        os.mkdir('/tmp/templates')  # Creates the new templates folder
    except FileExistsError:
        pass
    for file in os.listdir('templates'):  # Copies the templates one by one
        try:
            copy(f'templates/{file}', '/tmp/templates')
        except FileExistsError:
            pass
    try:
        os.mkdir('/tmp/server_uploads')  # Creates the folder for uploading files
    except FileExistsError:
        pass


create_tmp_folders_for_templates()

app = Flask(__name__, template_folder='/tmp/templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMPLATES_AUTO_RELOAD'] = True


def genotypes_form_to_list(form_dict: Dict[str, str]) -> List[Dict[int, str]]:
    """ Transforms the dict coming from the input_genotypes HTML form into a list of dicts """
    nested_genotypes = {}
    for key in form_dict:  # form_dict = request.form
        split_key = key.split(".xlsx ")  # ["file1", "1"]
        nested_genotypes[split_key[0]] = {}  # 1st loop creates the necessary dictionaries
    for key in form_dict:
        split_key = key.split(".xlsx ")
        nested_genotypes[split_key[0]][int(split_key[1])] = form_dict[key]  # 2nd loop assigns the values to each dict
    genotypes_of_each_experiment = []
    for key in nested_genotypes:
        genotypes_of_each_experiment.append(nested_genotypes[key])  # ignore the dict keys, just add to a list in order
    return genotypes_of_each_experiment


@app.route('/')
def home():
    """
    Main home screen for the web app.
    Returns the HTMl template where the Excel files are uploaded.
    Resets the pipeline by deleting the pkl file form Google Cloud Storage.
    """
    if is_pipeline_present():
        delete_pipeline_file()
    return render_template('home.html')


@app.route('/input-genotypes', methods=['POST', 'GET'])
def upload_files():
    """
    File uploader that supports multiple files.
    Initializes the pipeline Class and executes some pre-processing functions.
    Returns the next screen of the app: Input Parameters.
    """
    if request.method == 'POST':
        file_names = []
        excel_files = request.files.getlist('excel_files')
        for file in excel_files:
            secure_file_name = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_file_name))
            file_names.append(secure_file_name)
        pipeline = Pipeline(file_names)
        pipeline.preprocessing_of_data()
        serialize_and_upload_pipeline_to_gcs(pipeline)
        return render_template('input_genotypes.html',
                               file_names=file_names,
                               dates=pipeline.dates_of_dfs,
                               antennas_info=pipeline.antennas_info)
    elif request.method == 'GET' and is_pipeline_present():
        pipeline = download_and_deserialize_pipeline_from_gcs()
        file_names = pipeline.excel_files
        antennas_info = pipeline.antennas_info
        dates = pipeline.dates_of_dfs
        return render_template('input_genotypes.html', file_names=file_names, dates=dates,
                               antennas_info=antennas_info)
    else:
        return render_template('error_input_genotypes.html')


@app.route('/input-parameters', methods=['POST', 'GET'])
def send_genotypes():
    """ Posts the data for the genotypes and returns the template for Input Parameters """
    if request.method == 'POST' and is_pipeline_present():
        pipeline = download_and_deserialize_pipeline_from_gcs()
        genotypes = genotypes_form_to_list(request.form)
        pipeline.input_genotypes_data(genotypes)
        serialize_and_upload_pipeline_to_gcs(pipeline)
        return render_template('input_parameters.html')
    elif request.method == 'GET' and is_pipeline_present():
        return render_template('input_parameters.html')
    else:
        return render_template('error_input_parameters.html')


@app.route('/view-results', methods=['POST', 'GET'])
def send_parameters_and_run():
    """ Posts the parameters data, runs the main pipeline functions and returns the pipeline results """
    if request.method == 'POST' and is_pipeline_present():
        # Introduce the parameters of the pipeline
        parameters = [request.form["max_time_between_signals"], request.form["round_or_truncate"],
                      request.form["pollinators_to_remove"].split(', '),
                      request.form["filter_tags_by_visited_genotypes"],
                      request.form["visited_genotypes_required"].split(', '),
                      request.form["start_date_filter"], request.form["end_date_filter"]]
        pipeline = download_and_deserialize_pipeline_from_gcs()
        pipeline.input_parameters_of_run(*parameters)
        # Run the main process of the pipeline
        pipeline.run_pipeline()
        plots = Plot(pipeline.genotypes_dfs)
        plots.lay_out_plots_to_html()
        serialize_and_upload_pipeline_to_gcs(pipeline)
        return render_template('pipeline_results.html',
                               stats=pipeline.statistics,
                               file_names=pipeline.excel_files,
                               pollinators_alias=pipeline.pollinators_aliases,
                               tables_names=pipeline.genotypes_names)
    elif request.method == 'GET' and is_pipeline_present() and are_plots_files_present():
        pipeline = download_and_deserialize_pipeline_from_gcs()
        return render_template('pipeline_results.html',
                               stats=pipeline.statistics,
                               file_names=pipeline.excel_files,
                               pollinators_alias=pipeline.pollinators_aliases,
                               tables_names=pipeline.genotypes_names)
    else:
        return render_template('error_pipeline_results.html')


@app.route('/view-table/<name>')
def open_html_table(name):
    """ When called from a button on view-results, returns the corresponding HTML table file """
    path = f'/tmp/exports/{name}_table.html'
    return send_file(path)


@app.route('/download-data-excel')
def download_excel_file():
    """ When called from a button on view-results, returns the excel file containing the dataframes """
    try:
        return send_file('/tmp/exports/genotypes.xlsx')
    except Exception as e:
        return str(e)


@app.errorhandler(404)
def not_found(error):
    """ Returns a custom error 404 page """
    return render_template("404.html", error=error)


# import login
@app.errorhandler(500)
def internal_server_error(error):
    """ Returns a custom error 500 page """
    return render_template("500.html", error=error)


if __name__ == '__main__':
    app.run()
