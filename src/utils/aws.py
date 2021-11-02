"""
AWS related functions are implemented in this script.
"""

from datetime import datetime
import mimetypes
import boto3
from django.conf import settings
from rest_framework import status

_s3_client = boto3.client('s3', region_name="us-east-1",
                          aws_access_key_id=getattr(settings, 'AWS', {}).get('ACCESS_KEY', ''),
                          aws_secret_access_key=getattr(settings, 'AWS', {}).get('SECRET_KEY', ''))

_homeward_contracts_s3_client = boto3.client('s3', region_name="us-west-2",
                          aws_access_key_id=getattr(settings, 'AWS', {}).get('HOMEWARD_CONTRACTS_ACCESS_KEY', ''),
                          aws_secret_access_key=getattr(settings, 'AWS', {}).get('HOMEWARD_CONTRACTS_SECRET_KEY', ''))

HOMEWARD_CONTRACTS_BUCKET = "homeward-contracts"


def generate_presigned_url(data):
    """
    Function to generate presigned url which is used to upload document.
    """
    key = _s3_client.generate_presigned_post(
        Bucket=getattr(settings, 'AWS', {}).get('BUCKET', ''),
        Key=data.get('url', None),
        Fields={
            "acl": "public-read",
            "Content-Type": mimetypes.MimeTypes().guess_type(data.get('url', ''))[0]
        },
        Conditions=[
            {"acl": "public-read"},
            {"Content-Type": mimetypes.MimeTypes().guess_type(data.get('url', ''))[0]},
            ["content-length-range",
             int(data.get('size', 0)),
             int(data.get('size', 0))]
        ]
    )
    return key


def delete_object(key):
    """
    Function to delete object from S3.
    """
    if check_if_object_exists(key):
        try:
            response = _s3_client.delete_object(Bucket=getattr(settings, 'AWS', {}).get('BUCKET', ''), Key=key)
        except Exception as e:
            print('Exception: deleting as object from S3 : ', e)
            return False
        return response['ResponseMetadata']['HTTPStatusCode'] == status.HTTP_204_NO_CONTENT
    return False


def check_if_object_exists(key):
    """
    Function to check if an object exists on given key.
    """
    try:
        response = _s3_client.get_object(Bucket=getattr(settings, 'AWS', {}).get('BUCKET', ''), Key=key)
    except Exception as e:
        print('Exception: checking if object exists on S3 : ', e)
        return False
    return response['ResponseMetadata']['HTTPStatusCode'] == status.HTTP_200_OK

def upload_homeward_contract(file_path: str, s3_folder_name: str , s3_file_name: str, s3_client=_homeward_contracts_s3_client):
    """
    Function to upload pre-filled offer contract PDFs to S3
    Returns a pre-signed s3 url
    This function will throw FileNotFoundError if file_path is incorrect
    """
    expiration = 10 * 60 # 10 minutes
    environment = getattr(settings, 'APP_ENV', 'local')
    s3_upload_key = f'{environment}/{s3_folder_name}/{s3_file_name}'
    with open(file_path, 'rb') as reader:
        file = reader.read()
    s3_client.put_object(Bucket=HOMEWARD_CONTRACTS_BUCKET, Key=s3_upload_key, Body=file)

    # Generate an expiring pre-signed url
    url = s3_client.generate_presigned_url('get_object',Params={'Bucket': HOMEWARD_CONTRACTS_BUCKET, 'Key': s3_upload_key}, ExpiresIn=expiration)
    return url


def retrieve_contract_template(contract_template_name: str, s3_client=_homeward_contracts_s3_client):
    """Takes a contract template name and looks in the current
    contracts-templates 'folder' of the S3 bucket for the
    named item.

    Args:
        contract_template_name (str): The name of the template to
            retrieve.
        s3_client (boto3 client): The client to connect to AWS S3.
            Not straightforward to type-hint, so not doing that.

    Returns:
        StreamingBody: pdf as file-like object - works with PdfReader

    Raises:
        ValueError: that contract template isn't in the bucket
    """
    s3_download_key = f"contract-templates/{settings.APP_ENV if settings.APP_ENV != 'test' else 'dev'}/{contract_template_name}"
    try:
        s3_response = s3_client.get_object(Bucket=HOMEWARD_CONTRACTS_BUCKET, Key=s3_download_key)
    except s3_client.exceptions.NoSuchKey:
        raise ValueError(f"Template '{contract_template_name}' not found at {s3_download_key}") from None
    return s3_response['Body']
