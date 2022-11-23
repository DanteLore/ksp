import boto3


def load_file_to_s3(filename, s3_bucket, s3_key):
    print("Uploading data to S3://{0}/{1}".format(s3_bucket, s3_key))

    s3 = boto3.resource('s3')
    s3.Bucket(s3_bucket).upload_file(
        filename,
        s3_key
    )


def download_file_from_s3(s3_bucket, s3_key, filename):
    print("Downloading data from S3://{0}/{1}".format(s3_bucket, s3_key))

    s3 = boto3.resource('s3')
    s3.Bucket(s3_bucket).download_file(
        s3_key,
        filename
    )


def get_download_link(bucket, key):
    url = boto3.client('s3').generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=3600)

    return url
