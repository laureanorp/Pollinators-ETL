import os

from flask import Flask, render_template, request

from pollinators_ETL import Pipeline

# from werkzeug import secure_filename


UPLOAD_FOLDER = "server_uploads"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/home')
def home():
    return render_template('file_input.html')


@app.route('/success/<name>')
def success(name):
    return render_template('upload_successful.html', file_name=name)


@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        csv_file = request.files['csv_file']
        csv_file.save(os.path.join(app.config['UPLOAD_FOLDER'], csv_file.filename))
        # Instance the Pipeline class
        pipeline_1 = Pipeline("".join(["server_uploads/", csv_file.filename]))
        return render_template('upload_successful.html', file_name=csv_file.filename)


@app.route('/pipeline-results', methods=['POST', 'GET'])
def pipeline_results():
    max_visit_duration = request.args.get('max_visit_duration', 7)
    filter_start_datetime = request.args.get('filter_start_datetime', '')
    filter_end_datetime = request.args.get('filter_end_datetime', '')
    round_or_truncate = request.args.get('round_or_truncate', '1')
    all_antennas_visited = request.args.get('all_antennas_visited', '1')
    # Run the main process of the pipeline
    pipeline_1.run_pipeline(max_visit_duration=max_visit_duration, filter_start_datetime=filter_start_datetime,
                            filter_end_datetime=filter_end_datetime, round_or_truncate=round_or_truncate,
                            all_antennas_visited=all_antennas_visited, antennas_to_concat=[])
    return render_template('pipeline_results.html')


if __name__ == '__main__':
    app.run()
