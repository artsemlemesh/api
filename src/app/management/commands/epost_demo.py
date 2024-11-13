import stripe
import time
from django.core.management import BaseCommand
from app.utils.epost import EasyPostUtils
from app.models.product import Listing
from app.tasks.orders import create_shipments_in_batch
from datetime import datetime, timedelta

class Command(BaseCommand):
    @property
    def from_address(self):
        return EasyPostUtils.create_address(
            'Vinay Gode', street1='1014 Windermere Xing',
            city='Cumming', state='GA', postal_code='30041',
            phone='310-808-5256'
        )

    @property
    def to_address(self):
        return EasyPostUtils.create_address(
            name='Fake Buyer', street1='106 Fleming Ave',
            city='Newark', state='NJ', postal_code='07105',
            phone='310-808-5255'
        )

    @property
    def parcel(self):
        return EasyPostUtils.create_parcel(weight=21.2)

    @property
    def customs_item(self):
        return EasyPostUtils.create_customs_item(
            description="EasyPost t-shirts",
            quantity=2,
            value=96.27,
            weight=21.1
        )

    @property
    def customs_info(self):
        return EasyPostUtils.create_customs_info(
            'Bynde Admin', [self.customs_item]
        )

    def create_shipment(self):
        return EasyPostUtils.create_shipment(
            self.to_address, self.from_address,
            self.parcel, self.customs_info, True
        )

    @property
    def to_address_dict() -> dict:
        return dict(
            name='Fake Buyer', street1='106 Fleming Ave',
            city='Newark', state='NJ', postal_code='07105',
            phone='310-808-5255')

    def create_shipments_with_batch(self):
        parcel = EasyPostUtils.create_parcel(weight=12)
        data = [
            {
                'from_address': self.from_address,
                'to_address': {
                    'name': 'Stan Marsh',
                    'street1': '1014 Windermere Xing',
                    'city': 'Cumming',
                    'state': 'GA',
                    'zip': '30041'
                },
                'parcel': parcel,
                'carrier': 'USPS',
                'service': 'Priority',
            },
            {
                'from_address': self.from_address,
                'to_address': {
                    'name': 'Stan Marsh',
                    'street1': '1014 Windermere Xing',
                    'city': 'Cumming',
                    'state': 'GA',
                    'zip': '30041'
                },
                'parcel': parcel,
                'carrier': 'USPS',
                'service': 'Priority',
            },
            {
                'from_address': self.from_address,
                'to_address': {
                    'name': 'Stan Marsh',
                    'street1': '1014 Windermere Xing',
                    'city': 'Cumming',
                    'state': 'GA',
                    'zip': '30041'
                },
                'parcel': parcel,
                'carrier': 'USPS',
                'service': 'Priority',
            },
            {
                'from_address': self.from_address,
                'to_address': {
                    'name': 'Kyle Broflovski',
                    'street1': '1014 Windermere Xing',
                    'city': 'Cumming',
                    'state': 'GA',
                    'zip': '30041'
                },
                'parcel': parcel,
                'carrier': 'USPS',
                'service': 'Priority',
            }
        ]
        batch = EasyPostUtils.create_batch(data)

        # TODO: Purchase label
        return batch

    @property
    def batch_id(self) -> str:
        # return 'batch_e9d4cc25f067430e925817f56859a689'  # label purchase fail
        return 'batch_0abd70fb0d224a0c94c62ca5601c3663'

    def test_celery_task_to_create_shipments_in_batch(self, async_mode: bool = False):
        if async_mode:
            create_shipments_in_batch.delay()
        else:
            create_shipments_in_batch()

    
    def get_pickup_timmings(self):
        today = datetime.now()
        desired_time = today.replace(hour=10, minute=30, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        tomorrow_at_10_30 = datetime.combine(tomorrow.date(), desired_time.time())
        day_after_at_10_30 = datetime.combine((tomorrow + timedelta(days=1)).date(), desired_time.time())
        date_format = '%Y-%m-%d %H:%M:%S'

        return tomorrow_at_10_30.strftime(date_format), day_after_at_10_30.strftime(date_format)

    def demo_pickup(self):
        
        pickup_start_time,pickup_end_time = self.get_pickup_timmings()
        response = EasyPostUtils.create_and_buy_pickup(
            'shp_c3013764d5484816ac5b643c0ec9dcce',
            self.from_address,
            pickup_start_time,
            pickup_end_time,
            reference='PICK_DEMO',
            instructions='DO NOT COME HERE.'
        )
        response = EasyPostUtils.cancel_pickup(response.id)
        return response

    def handle(self, *args, **kwargs):
        self.test_celery_task_to_create_shipments_in_batch()

        batch = self.create_shipments_with_batch()
        time.sleep(3)
        EasyPostUtils.buy_batch(batch.id)
        shipment = self.create_shipment()
        print(shipment)
        # listing = self.__create_ship_from_model()
        # print(listing.shipments)

        self.demo_pickup()
