import os
import pickle

from rfid_pollinators_pipeline import Pipeline
from google.cloud import storage

PIPELINE_BLOB_NAME = 'pipeline.pkl'
GCS_BUCKET = 'rfid-pollinators.appspot.com'
PIPELINE_PKL_LOCAL_PATH = '/tmp/pipeline.pkl'

CREDENTIAL_PATH = "rfid-pollinators-d0c96f9c8ef9.json"
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIAL_PATH


def serialize_and_upload_pipeline_to_gcs(pipeline):
    """ Serializes and saves the Pipeline class to a blob on a GCS bucket """
    with open(PIPELINE_PKL_LOCAL_PATH, 'wb') as file:
        pickle.dump(pipeline, file)

    storage_client = storage.Client()
    bucket = storage_client.get_bucket(GCS_BUCKET)
    blob = bucket.blob(PIPELINE_BLOB_NAME)  # Name of the object to be stored in the bucket
    blob.upload_from_filename(PIPELINE_PKL_LOCAL_PATH)   # Name of the object in local file system


def download_and_deserialize_pipeline_from_gcs() -> Pipeline:
    """ Downloads the pipeline file form GCS bucket and returns the deserialized object """
    storage_client = storage.Client()
    bucket = storage_client.bucket('rfid-pollinators.appspot.com')
    blob = bucket.blob(PIPELINE_BLOB_NAME)
    blob.download_to_filename(PIPELINE_PKL_LOCAL_PATH)

    with open(PIPELINE_PKL_LOCAL_PATH, 'rb') as file:
        pipeline = pickle.load(file)
    return pipeline


def is_pipeline_present():  # TODO test
    """ Checks if the serialized file for the Pipeline is present on GCS bucket """
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)
    exists = storage.Blob(bucket=bucket, name=PIPELINE_BLOB_NAME).exists(storage_client)
    return exists


def are_plots_files_present():  # TODO test
    """ Checks if the Plot files are already present """
    return os.path.isfile("/tmp/templates/charts_per_genotype.html") and os.path.isfile(
        "/tmp/templates/charts_per_pollinator.html") and os.path.isfile("/tmp/templates/evolution_charts.html")


def delete_pipeline_file():
    """ Deletes the pipeline blob from GCS bucket """
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)
    blob = bucket.blob(PIPELINE_BLOB_NAME)
    blob.delete()
