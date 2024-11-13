from django.core.management import BaseCommand

from app.models.product import Product, BG_REMOVAL_STATUS


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        item = Product.objects.last()
        item.bg_removal_status = BG_REMOVAL_STATUS.to_do
        item.save()
        image = item.images.first()

        # self.__test_bg_removal_anyc_task(item)
        # self.__test_bg_removal_sync(item)
        self.__test_bg_removal_single_sync(image)

    def __test_bg_removal_anyc_task(self, item: Product):
        if item.bg_removal_status != BG_REMOVAL_STATUS.to_do:
            item.bg_removal_status = BG_REMOVAL_STATUS.to_do
            item.save()

        item.request_to_remove_background(raise_exception=True)
        item.save()
        print(item.bg_removal_task_uuid)

    # def __test_bg_removal_sync(self, item: Product):
    #     response = remove_background_from_product_images(
    #         item.pk, True)
    #     print(response)
    

    # def __test_bg_removal_single_sync(self, listing_image):
    #     response = remove_background_from_product_single_image(listing_image.pk, True)
    #     print(response)
