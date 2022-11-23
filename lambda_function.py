import json
from datetime import datetime
from aws_helpers import load_file_to_s3, download_file_from_s3
from ksp_utils import fix_ports

S3_BUCKET = "dantelore.ksp"


def handler(event, context):
    start = datetime.now()

    s3_input_key = "input/example_input.sfs"
    s3_output_key = "output/example_input fixed.sfs"
    local_input_filename = "/tmp/input.sfs"
    local_output_filename = "/tmp/output.sfs"

    download_file_from_s3(S3_BUCKET, s3_input_key, local_input_filename)

    fix_ports(local_input_filename, local_output_filename)

    load_file_to_s3(local_output_filename, S3_BUCKET, s3_output_key)

    duration = (datetime.now() - start).seconds
    print(f"File converted in {duration}s")

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*'
        },
        'body': s3_output_key
    }

