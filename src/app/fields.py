import os
from uuid import uuid4
from django.conf import settings
from django.db.models.fields.files import ImageFieldFile
from PIL import Image
from sorl.thumbnail import ImageField


class ProductImageField(ImageField):
    def __init__(self, *args, **kwargs):
        self.is_front = bool(kwargs.pop('is_front', False))
        super().__init__(*args, **kwargs)

    def save_form_data(self, instance, data):
        if data is not None:
            if not isinstance(data, ImageFieldFile):
                resized_file_pathname = os.path.join(
                    settings.DATA_BG_REMOVAL_SOURCE_PATH,
                    f"{uuid4()}--{data.name}"
                )
                image = Image.open(data)
                resized_image = image.resize((
                        settings.LISTING_ITEM_IMAGE_RESIZE_DEFAULT_WIDTH,
                        settings.LISTING_ITEM_IMAGE_RESIZE_DEFAULT_HEIGHT
                    ))
                resized_image.save(resized_file_pathname)
                details = instance.bg_removal_details or {}
                details.update({
                    'front_source' if self.is_front else 'back_source':
                    resized_file_pathname
                })
                instance.bg_removal_details = details
            setattr(instance, self.name, data or '')
