import time
import stripe
from celery import shared_task

from django.apps import apps
from django.db import transaction

from app.utils.epost import EasyPostUtils


@shared_task
def release_fund_manually(payment_intent_pk: str):
    stripe_obj = stripe.PaymentIntent.retrieve(payment_intent_pk)
    try:
        status = stripe_obj.confirm()
        return status
    except Exception:
        return False


@shared_task(name='shipment_purchase_shceduler')
@transaction.atomic()
def create_shipments_in_batch():
    OrderItemModelRef = apps.get_model('app', 'OrderItem')
    shipment_data = []
    order_items = []
    shipments_ids = []
    items = OrderItemModelRef.objects.get_items_ready_to_ship().all()
    for item in items:
        try:
            shipment_data.append(item.to_shipment_dict())
            item.wait_to_print_label()
            order_items.append(item)
            item.save()
        except Exception as e:
            item.failed_to_print_label(e)
            item.save()

            # TODO: Need to find a way to notify about the issue.
            print("Exception in Order::",e)
            # raise e
    if shipment_data:
        batch = EasyPostUtils.create_batch(shipments=shipment_data)
        # NOTE: I don't think it good but sometimes, a weird error happens
        # ERROR MESSAGE: Unable to modify batch while it is being created.
        # So we may need to give it a short break.
        time.sleep(3)
        # batch.buy()
        EasyPostUtils.buy_batch(batch.id)

        get_batch_id = batch.id
        for i in order_items:
            i.batch_id(get_batch_id)
        time.sleep(30)
        # SHIPMENTS ADDED IN DATABASE HERE
        new_batch = EasyPostUtils.retrieve_batch(batch_id=batch.id)
        shipment_model_ref = apps.get_model('app', 'Shipment')
        

        tracker_model_ref = apps.get_model('app', 'ShipmentTracker')

        for idx, shipment in enumerate(new_batch.shipments):
            item = EasyPostUtils.retrieve_shipment(shipment.id)
            _, order_item_id = item.reference.split('__')
            order_item = OrderItemModelRef.objects.get(pk=order_item_id)
            shipment, created = shipment_model_ref.objects.get_or_create_from_easypost_object(
                order_item, item)
            shipments_ids.append(shipment.id) #added the shipment id to the list
            order_item.label_printed()
            # email the seller that the bundle has been sold and their label is ready
            listing_title = order_item.listing.title
            seller = order_item.listing.created_by
            seller.send_bundle_sold(listing_title=listing_title, postage_url=shipment.label_url)
            tracker = item.tracker
            tracker_model_ref._update_or_create_from_easypost_object(tracker)
            order_item.shipmentID(shipment.id)

            shipment = shipment_model_ref.objects.get(order_item=order_item_id)
            if shipment.status == "label generated":
                order_item.status.print_label()
                order_item.save()
        return batch.id,shipments_ids
        # for i in order_items:
        #     i.shipmentID(shipments_id)

        # for idx, item in enumerate(batch['shipments']):
        #     _, order_item_id = item.reference.split('__')
            

        #     if shipment_id.status == "label generated":
        #         print("Shipment ID",shipment_id.status)
        #         for i in order_items:
        #             i.status = i.status.print_label()
        #             i.save()
        # return batch.id,shipments_id

    return None

@shared_task(name="update_data_in_databse")
@transaction.atomic()
def update_database():
    ShipmentModelRef = apps.get_model('app', 'Shipment')
    OrderItemModelRef = apps.get_model('app', 'OrderItem')
    shipment_item = ShipmentModelRef.objects.all()
    for i in shipment_item:
        if i.status == "label_generated":
            shipment_retrieve = EasyPostUtils.retrieve_shipment(i.easypost_shipment_id)
            _, order_id = shipment_retrieve.reference.split("__")
            try:
                order_item = OrderItemModelRef.objects.get(pk=order_id)
            except:
                continue
            shipment, created = ShipmentModelRef.objects.update_data_from_easypost(
                order_item, shipment_retrieve)
            TrackerModelRef = apps.get_model('app', 'ShipmentTracker')
            tracker = shipment_retrieve.tracker
            TrackerModelRef._update_or_create_from_easypost_object(tracker)
