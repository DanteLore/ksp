import json
import urllib.parse
import uuid
from datetime import datetime
from aws_helpers import load_file_to_s3, download_file_from_s3, get_download_link, get_upload_link
from ksp_utils import fix_ports

S3_BUCKET = "dantelore.ksp"


def convert_file_and_prepare_download(s3_input_key):
    start = datetime.now()
    s3_output_key = s3_input_key.replace("input/", "output/")

    uid = str(uuid.uuid4())[:8]
    local_input_filename = f"/tmp/input-{uid}.sfs"
    local_output_filename = f"/tmp/output-{uid}.sfs"

    download_file_from_s3(S3_BUCKET, s3_input_key, local_input_filename)

    fix_ports(local_input_filename, local_output_filename)

    load_file_to_s3(local_output_filename, S3_BUCKET, s3_output_key)

    return {
        "status": "Success",
        "output_bucket": S3_BUCKET,
        "input_file": s3_input_key,
        "output_file": s3_output_key,
        "download_link": get_download_link(S3_BUCKET, s3_output_key),
        "duration_seconds": (datetime.now() - start).seconds
    }


def prepare_upload():
    uid = str(uuid.uuid4())[:8]
    key = f"input/{uid}.sfs"
    link = get_upload_link(S3_BUCKET, key)

    return {
        "status": "Upload",
        "upload_link": link,
        "s3_key": key
    }


def handler(event, context):
    key = event.get('s3_key')

    print("No key found in request params.  Checking body...")
    if not key:
        body = event.get("body")
        if body:
            try:
                data = urllib.parse.unquote(body)
                print(data)
                if data.startswith('s3_key'):
                    key = data.split('=')[-1]
            except:
                print("It wasn't the format I expected: ")
                print(body)
                urllib.parse.unquote(body)

    if key:
        print(f"Invoked with s3_key {key}")
        result = convert_file_and_prepare_download(key)
    else:
        print(f"Invoked with no s3_key, preparing upload")
        result = prepare_upload()

    print(json.dumps(result))

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(result)
    }
