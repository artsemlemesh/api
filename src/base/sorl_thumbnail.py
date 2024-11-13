from sorl.thumbnail.base import ThumbnailBackend
import os


class Thumbnail(ThumbnailBackend):
    def _get_thumbnail_filename(self, source, geometry_string, options):
        """
        Computes the destination filename for thumbnails.
        We want to keep each thumbnail along side original image
        """
        file_name = source.name.split('/')[-1]
        file_name, file_extension = file_name.split('.')
        file = f'{file_name}_{geometry_string}.{file_extension}'
        return os.path.join('listings', file)
