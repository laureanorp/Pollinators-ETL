import os

from flask import Flask, render_template, request

from pollinators_ETL import Pipeline

UPLOAD_FOLDER = "server_uploads"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


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
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            file_names.append(file.filename)
        global pipeline
        pipeline = Pipeline(file_names)
        pipeline.preprocessing_of_data()
        antennas_info = pipeline.antennas_info
        return render_template('input_genotypes.html', file_names=file_names,
                               antennas_info=antennas_info)  # TODO extract date from df
    if request.method == 'GET':  # TODO what goes here?
        csv_files = request.files.getlist('csv_files')
        for file in csv_files:
            file_names.append(file.filename)
        return render_template('input_genotypes.html', file_name=file_names)


@app.route('/input-genotypes', methods=['POST', 'GET'])
def input_genotypes():
    if request.method == 'POST':
        pipeline.input_genotypes_data(
            [{1: "Genotype A", 3: "Genotype A", 4: "Genotype A", 6: "Genotype B", 9: "Genotype B",
              10: "Genotype B", 12: "Genotype B", 13: "Genotype C", 14: "Genotype C",
              15: "Genotype C", 16: "Genotype C"},
             {2: "Genotype A", 5: "Genotype A", 6: "Genotype A", 9: "Genotype B", 14: "Genotype B",
              15: "Genotype C", 16: "Genotype C"}])  # TODO parameter
        pipeline.add_genotypes_and_join_df()
        return render_template('input_parameters.html')
    elif request.method == 'GET':
        return render_template('input_parameters.html')


@app.route('/input-parameters', methods=['POST', 'GET'])
def input_parameters():
    if request.method == 'POST':
        max_time_between_signals = request.args.get('max_visit_duration')
        filter_start_datetime = request.args.get('filter_start_datetime')
        filter_end_datetime = request.args.get('filter_end_datetime')
        round_or_truncate = request.args.get('round_or_truncate')
        filter_tags_by_visited_genotypes = False
        pollinators_to_remove = request.args.get('pollinators_to_remove')
        visited_genotypes_required = []
        flowers_per_antenna = 1

        # Introduce the parameters of the pipeline
        pipeline.input_parameters_of_run(7, "", "", "round", False, [], [], 1)
        # Run the main process of the pipeline
        pipeline.run_pipeline()
        return render_template('pipeline_results.html')
    elif request.method == 'GET':
        return render_template('pipeline_results.html')


if __name__ == '__main__':
    app.run()
