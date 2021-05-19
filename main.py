import os

from flask import Flask, render_template, request

from pollinators_ETL import Pipeline

UPLOAD_FOLDER = "server_uploads"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/home')
def home():
    """
    Main home screen for the web app
    Returns the HTMl template where the CSv file is uploaded
    """
    return render_template('home.html')


@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        csv_file = request.files['csv_file']
        csv_file.save(os.path.join(app.config['UPLOAD_FOLDER'], csv_file.filename))
        return render_template('input_parameters.html', file_name=csv_file.filename)
    if request.method == 'GET':
        csv_file = request.args.get('csv_file')
        return render_template('input_parameters.html', file_name=csv_file.filename)


@app.route('/run-pipeline/<csv_file>', methods=['POST', 'GET'])
def run_pipeline(csv_file):
    if request.method == 'POST':
        max_visit_duration = request.args.get('max_visit_duration')
        filter_start_datetime = request.args.get('filter_start_datetime')
        filter_end_datetime = request.args.get('filter_end_datetime')
        round_or_truncate = request.args.get('round_or_truncate')
        all_antennas_visited = request.args.get('all_antennas_visited')
        antennas_to_concat = request.args.get('antennas_to_concat')
        pollinators_to_remove = request.args.get('pollinators_to_remove')
        # Instance the Pipeline class
        pipeline_1 = Pipeline("".join(["server_uploads/", csv_file]))
        # Introduce the parameters of the pipeline
        pipeline_1.input_parameters_of_run(max_visit_duration, filter_start_datetime, filter_end_datetime,
                                           round_or_truncate, all_antennas_visited, antennas_to_concat,
                                           pollinators_to_remove, [], 1)
        # Run the main process of the pipeline
        pipeline_1.run_pipeline()
        return render_template('pipeline_results.html')
    elif request.method == 'GET':
        return render_template('pipeline_results.html')


if __name__ == '__main__':
    app.run()
