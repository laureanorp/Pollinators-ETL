import os
import pickle

from rfid_pollinators_pipeline import Pipeline

PIPELINE_PKL = '/tmp/pipeline.pkl'

def serialize_pipeline(pipeline):
    """ Serializes and saves the Pipeline class to a file """
    with open(PIPELINE_PKL, 'wb') as file:
        pickle.dump(pipeline, file)


def deserialize_pipeline() -> Pipeline:
    """ Deserializes the Pipeline class from a file to an object """
    with open(PIPELINE_PKL, 'rb') as file:
        pipeline = pickle.load(file)
    return pipeline


def is_pipeline_present():  # TODO test
    """ Checks if the serialized file for the Pipeline is present """
    return os.path.isfile(PIPELINE_PKL)


def are_plots_files_present():  # TODO test
    """ Checks if the Plot files are already present """
    return os.path.isfile("/tmp/templates/charts_per_genotype.html") and os.path.isfile(
        "/tmp/templates/charts_per_pollinator.html") and os.path.isfile("/tmp/templates/evolution_charts.html")
