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
        s3_error_key = s3_input_key.replace("input/", "error/")

        uid = str(uuid.uuid4())[:8]
        local_input_filename = f"/tmp/input-{uid}.sfs"
        local_output_filename = f"/tmp/output-{uid}.sfs"

        download_file_from_s3(S3_BUCKET, s3_input_key, local_input_filename)

        try:
            fix_ports(local_input_filename, local_output_filename)
        except Exception as ex:

            load_file_to_s3(local_input_filename, S3_BUCKET, s3_error_key)

            return {
                "status": "Failed",
                "error_message": f"{type(ex).__name__}:{str(ex)} {ex.args}"
            }

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


def find_the_key(event):
    # I hate this function.  I hate the way the data is encoded in the post body.  I just hate it!
    key = event.get('s3_key')

    if not key:
        body = event.get("body")
        if body:
            try:
                data = urllib.parse.unquote(body)
                if data.startswith('s3_key'):
                    key = data.split('=')[-1]
            except:
                print("Failed to parse request body")

    return key


def handler(event, context):
    key = find_the_key(event)

    if key:
        print(f"Invoked with s3_key {key}")
        result = convert_file_and_prepare_download(key)
    else:
        print(f"Invoked with no s3_key, preparing upload")
        result = prepare_upload()

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(result)
    }
