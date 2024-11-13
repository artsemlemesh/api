import os
import boto3
import tempfile
from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.core.management.commands import dumpdata


class Command(BaseCommand):
    __FILENAME_MAP = {
        'brands': ('ProductBrand', 'brands.json'),
        'categories': ('ProductCategory', 'categories.json'),
        'sizes': ('ProductSize', 'sizes.json'),
        'shipping_rates': ('ShippingRate', 'shipping_rates.json'),
    }
    __fixture_path = None

    @property
    def fixtures_path(self) -> str:
        if not self.__fixture_path:
            self.__fixture_path = tempfile.mkdtemp()
        return self.__fixture_path

    def handle(self, *args, **kwargs):
        self._write_files()
        self._upload_fixtures_to_s3()

    def _upload_fixtures_to_s3(self):
        client = boto3.client(
            's3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )

        for identifier, (_, filename) in self.__FILENAME_MAP.items():
            print(f"Uploading {identifier} to s3...")
            try:
                client.upload_file(
                    os.path.join(self.fixtures_path, filename),
                    settings.AWS_STORAGE_BUCKET_NAME,
                    os.path.join(
                        settings.S3_FIXTURE_DATA_FOLDER_NAME, filename)
                )
            except Exception as e:
                print(f'Failed to upload {filename} with error - {e}')

        print("Finished to upload files to s3!")

    def _write_files(self):
        for identifier, (model_name, filename) in self.__FILENAME_MAP.items():
            print(f"Writing {identifier}...")
            call_command(
                dumpdata.Command(), f'app.{model_name}', indent=4,
                output=os.path.join(self.fixtures_path, filename)
            )

        print("Complete writing files and ready to upload to S3!")
