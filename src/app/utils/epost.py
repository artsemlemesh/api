import json
import easypost as ep
from typing import List
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

if not settings.EASYPOST_API_KEY:
    ImproperlyConfigured('EASYPOST_API_KEY is required in settings.')
else:
    easypost = ep.EasyPostClient(settings.EASYPOST_API_KEY)


class EVENT_TYPE:
    batch_created = 'batch.created'
    batch_updated = 'batch.updated'
    tracker_created = 'tracker.created'
    tracker_updated = 'tracker.updated'


class EasyPostUtils:
    @staticmethod
    def get_rates():
        return easypost.shipment().get_rates()

    @staticmethod
    def create_address(
        name: str, street1: str, city: str, state: str,
        postal_code: str, phone: str, country: str = 'US', street2: str = '',
    ) -> easypost.address:
        return easypost.address.create(
            verify=["delivery"],
            name=name,
            street1=street1,
            street2=street2,
            city=city,
            state=state,
            zip=postal_code,
            country=country,
            phone=phone
        )

    @staticmethod
    def create_parcel(
        weight: float,
        predefined_package: str = 'LargeFlatRateBox'
    ) -> easypost.parcel:
        return easypost.parcel.create(
            weight=weight,
            predefined_package=predefined_package
        )

    @staticmethod
    def create_customs_item(
        description: str,
        quantity: int,
        value: float,
        weight: float,
        hs_tariff_number: int = 123456,
        origin_country: str = "US",
    ) -> easypost.customs_item:
        return easypost.customs_item.create(
            description=description,
            hs_tariff_number=hs_tariff_number,
            origin_country=origin_country,
            quantity=quantity,
            value=value,
            weight=weight,
        )

    @staticmethod
    def create_customs_info(
        customs_signer: str,
        customs_items: List[dict],
        customs_certify: int = 1,
        contents_type: str = "gift",
        contents_explanation: str = "",
        eel_pfc: str = "NOEEI 30.37(a)",
        non_delivery_option: str = "return",
        restriction_type: str = "none",
        restriction_comments: str = "",
    ) -> easypost.customs_info:
        return easypost.customs_info.create(
            customs_certify=customs_certify,
            customs_signer=customs_signer,
            contents_type=contents_type,
            contents_explanation=contents_explanation,
            eel_pfc=eel_pfc,
            non_delivery_option=non_delivery_option,
            restriction_type=restriction_type,
            restriction_comments=restriction_comments,
            customs_items=customs_items,
        )

    @staticmethod
    def create_shipment(
        to_address: easypost.address,
        from_address: easypost.address,
        parcel: easypost.parcel,
        customs_info: easypost.customs_info,
        buy_postage_label: bool = False
    ) -> easypost.shipment:
        shipment = easypost.shipment.create(
            to_address=to_address,
            from_address=from_address,
            parcel=parcel,
            customs_info=customs_info
        )

        # NOTE: choose USPS only
        if buy_postage_label and shipment.rates:
            cheapest_rate = sorted(shipment.rates, key=lambda x: x.rate)[0]
            easypost.shipment.buy(id=shipment.id, rate=cheapest_rate)
        print("-----Shipment in easypost------------------",shipment)
        return shipment

    @staticmethod
    def retrieve_shipment(easypost_shipment_id: str) -> easypost.shipment:
        return easypost.shipment.retrieve(easypost_shipment_id)

    @classmethod
    def refund_shipment(cls, easypost_shipment_id: str):
        # shipment = cls.retrieve_shipment(easypost_shipment_id)
        response = easypost.shipment.refund(easypost_shipment_id)
        # print(response)
        return response 



    @staticmethod
    def confirm_shipment(shipment_id: str, rate_id: str) -> easypost.shipment:
        shipment = easypost.shipment.retrieve(shipment_id)
        rate = easypost.rate.retrieve(rate_id)
        shipment.buy(rate=rate)
        return shipment

    @staticmethod
    def process_event(values):
        # if not settings.LOCAL_DEBUG:
        #     values = json.dumps(values)
        event_id = values['id']
        return easypost.event.retrieve(event_id)

    @staticmethod
    def create_batch(shipments=List[dict]) -> easypost.batch:
        return easypost.batch.create(shipment=shipments)

    @staticmethod
    def buy_batch(batch_id) -> easypost.batch:
        return easypost.batch.buy(batch_id)

    @staticmethod
    def retrieve_batch(batch_id: str) -> easypost.batch:
        return easypost.batch.retrieve(batch_id)

    @staticmethod
    def retrive_tracer(tracker_id:str) -> easypost.tracker:
        return easypost.tracker.retrieve(tracker_id)

    @classmethod
    def create_and_buy_pickup(
        cls,
        shipment_id: str,
        address: easypost.address,
        min_datetime: str,
        max_datetime: str,
        reference: str = None,
        instructions: str = None
    ):
        shipment = cls.retrieve_shipment(shipment_id)
        pickup = easypost.pickup.create(
            address=address,
            shipment=shipment,
            reference=reference,
            min_datetime=min_datetime,
            max_datetime=max_datetime,
            is_account_address=False,
            instructions=instructions
        )
        bought_pickup = easypost.pickup.buy(
            pickup.id,
            carrier=pickup.pickup_rates[0].carrier,
            service=pickup.pickup_rates[0].service
            )
        return bought_pickup

    @classmethod
    def cancel_pickup(cls, pickup_id: str):
        response = easypost.pickup.cancel(pickup_id)
        return response
