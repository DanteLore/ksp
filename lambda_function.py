import json
from datetime import datetime
from aws_helpers import load_file_to_s3, download_file_from_s3
from ksp_utils import fix_ports

S3_BUCKET = "dantelore.ksp"


def handler(event, context):
    start = datetime.now()

    filename = "/tmp/x.sfs"
    fixed_file = "/tmp/x fixed.sfs"
    download_file_from_s3("dantelore.ksp", "input/example_input.sfs", filename)

    fixed_data = fix_ports(filename)

    load_file_to_s3(fixed_file, "dantelore.ksp", "output/example_input fixed.sfs")

    duration = (datetime.now() - start).seconds
    print(f"File converted in {duration}s")

    return {
        'statusCode': 200,
        'body': json.dumps(fixed_data)
    }

