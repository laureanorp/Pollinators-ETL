import os

from flask import Flask, render_template, request

from pollinators_ETL import Pipeline

UPLOAD_FOLDER = "server_uploads"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/home')
def home():
    return render_template('file_input.html')


@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        csv_file = request.files['csv_file']
        csv_file.save(os.path.join(app.config['UPLOAD_FOLDER'], csv_file.filename))
        return render_template('upload_successful.html', file_name=csv_file.filename)


@app.route('/run-pipeline/<csv_file>', methods=['POST', 'GET'])
def run_pipeline(csv_file):
    max_visit_duration = request.args.get('max_visit_duration', 7)
    filter_start_datetime = request.args.get('filter_start_datetime', '')
    filter_end_datetime = request.args.get('filter_end_datetime', '')
    round_or_truncate = request.args.get('round_or_truncate', '1')
    all_antennas_visited = request.args.get('all_antennas_visited', '1')
    antennas_to_concat = []
    pollinators_to_remove = []
    # Instance the Pipeline class
    pipeline_1 = Pipeline("".join(["server_uploads/", csv_file]))
    # Run the main process of the pipeline
    pipeline_1.input_parameters_of_run(max_visit_duration, filter_start_datetime, filter_end_datetime,
                                       round_or_truncate,
                                       all_antennas_visited, antennas_to_concat, pollinators_to_remove)
    pipeline_1.run_pipeline()
    return render_template('pipeline_results.html')


if __name__ == '__main__':
    app.run()
