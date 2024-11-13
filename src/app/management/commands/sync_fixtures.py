import requests
import os
from django.conf import settings
from django.core.management import BaseCommand
import boto3
import botocore
from botocore import UNSIGNED
from botocore.config import Config


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        bucket_name = settings.AWS_PRODUCTION_STORAGE_BUCKET_NAME
        s3 = boto3.resource('s3', config=Config(signature_version=UNSIGNED))

        fixtures = [
            'brands.json',
            'categories.json',
            'shipping_rates.json',
            'sizes.json'
        ]
        for fixture in fixtures:
            try:
                bucket_file_path = f'{settings.S3_FIXTURE_DATA_FOLDER_NAME}/{fixture}'
                file_path = os.path.join(settings.FIXTURES_ROOT, fixture)

                s3.Bucket(bucket_name).download_file(bucket_file_path, file_path)
            except botocore.exceptions.ClientError as e: 
                if e.response['Error']['Code'] == "403":
                    print("Forbidden file",file_path)
                if e.response['Error']['Code'] == "404":
                    print("File not found",file_path)
                else:
                    raise
