import os
from shutil import copy
from typing import List, Dict, Optional

from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

from rfid_pollinators_pipeline import Pipeline, Plot


def copy_templates_to_temp():
    """ Copies the original templates to /tmp so results can be written to that folder in production"""
    try:
        os.mkdir('/tmp/templates')
        for file in os.listdir('templates'):
            copy(f'templates/{file}', '/tmp/templates')
    except FileExistsError:
        pass


copy_templates_to_temp()

UPLOAD_FOLDER = "/tmp/server_uploads"

app = Flask(__name__, template_folder='/tmp/templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMPLATES_AUTO_RELOAD'] = True
pipeline: Optional[Pipeline] = None
plots: Optional[Plot] = None


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
    """
    return render_template('home.html')


@app.route('/input-genotypes', methods=['POST', 'GET'])
def upload_files():
    """
    File uploader that supports multiple files.
    Initializes the pipeline Class and executes some pre-processing functions.
    Returns the next screen of the app: Input Parameters.
    """
    if not os.path.exists('/tmp/server_uploads'):
        os.mkdir('/tmp/server_uploads')
    file_names = []
    global pipeline
    if request.method == 'POST':
        excel_files = request.files.getlist('excel_files')
        for file in excel_files:
            secure_file_name = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_file_name))
            file_names.append(secure_file_name)
        pipeline = Pipeline(file_names)
        pipeline.preprocessing_of_data()
        return render_template('input_genotypes.html',
                               file_names=file_names,
                               dates=pipeline.dates_of_dfs,
                               antennas_info=pipeline.antennas_info)
    elif request.method == 'GET' and pipeline is not None:
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
    if request.method == 'POST':
        genotypes = genotypes_form_to_list(request.form)
        pipeline.input_genotypes_data(genotypes)
        return render_template('input_parameters.html')
    elif request.method == 'GET' and pipeline is not None and pipeline.genotypes_of_each_experiment is not None:
        return render_template('input_parameters.html')
    else:
        return render_template('error_input_parameters.html')


@app.route('/view-results', methods=['POST', 'GET'])
def send_parameters_and_run():
    """ Posts the parameters data, runs the main pipeline functions and returns the pipeline results """
    global plots
    if request.method == 'POST':
        # Introduce the parameters of the pipeline
        parameters = [request.form["max_time_between_signals"], request.form["round_or_truncate"],
                      request.form["pollinators_to_remove"].split(', '),
                      request.form["filter_tags_by_visited_genotypes"],
                      request.form["visited_genotypes_required"].split(', '),
                      request.form["start_date_filter"], request.form["end_date_filter"]]
        pipeline.input_parameters_of_run(*parameters)
        # Run the main process of the pipeline
        pipeline.run_pipeline()
        plots = Plot(pipeline.genotypes_dfs)
        plots.lay_out_plots_to_html()
        return render_template('pipeline_results.html',
                               stats=pipeline.statistics,
                               file_names=pipeline.excel_files,
                               pollinators_alias=pipeline.pollinators_aliases,
                               tables_names=pipeline.genotypes_names)
    elif request.method == 'GET' and plots is not None:
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
def not_found(e):
    """ Returns a custom error 404 page """
    return render_template("404.html")


@app.errorhandler(500)
def internal_server_error(e):
    """ Returns a custom error 500 page """
    return render_template("500.html")


if __name__ == '__main__':
    app.run()
