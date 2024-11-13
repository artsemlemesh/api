import os
import json
import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from djstripe import webhooks, models

from app.constants.status import ORDER_ITEM_STATUS
from app.utils.epost import EasyPostUtils, EVENT_TYPE
from app.models.shipment import ShipmentTracker, Shipment
from app.models.order import OrderItem


def save_to_file(data: dict, event_name: str = 'event'):
    filename = os.path.join(settings.PROJECT_ROOT, f'{event_name}.json')
    with open(filename, 'w+') as f:
        json.dump(data, f, indent=2)


@require_POST
@csrf_exempt
def stripe_webhook(request, **kwargs):
    try:
        stripe_data = json.loads(request.body)
        # print(stripe_data)
        # NOTE: When we need to get the event content for unittest mock
        # save_to_file(stripe_data, stripe_data['type'])
        stripe_event = models.Event.stripe_class.construct_from(
            stripe_data, key=settings.STRIPE_SECRET_KEY
        )
        event, _ = models.Event._get_or_create_from_stripe_object(stripe_event)
        if event:
            webhooks.call_handlers(event)
    except ValueError as e:
        print(e)
        return HttpResponseBadRequest(str(e))
    except stripe.error.InvalidRequestError as e:
        print(e)
        return HttpResponseBadRequest(str(e))
    
    return JsonResponse({"status": True})


@require_POST
@csrf_exempt
def easypost_webhook(request, **kwargs):
    try:
        event_object = json.loads(request.body)
        event = EasyPostUtils.process_event(event_object)


        if event['description'] in [
                EVENT_TYPE.tracker_created, EVENT_TYPE.tracker_updated]:
            shipment_id = event_object['result']['shipment_id']
            tracker = EasyPostUtils.retrive_tracer(event_object['result']['id'])
            if Shipment.objects.\
                    filter(easypost_shipment_id=shipment_id).count():
                obj_, created = ShipmentTracker.\
                    _update_or_create_from_easypost_object(tracker)
            else:
                print("Unknown shipment found.")
        elif event['description'] == EVENT_TYPE.batch_updated:
            # TODO: Process shipments
            if event['previous_attributes']['state'] == 'created':
                # Only when the batch was purchased label
                for shipment in event_object['result']['shipments']:
                    reference = shipment['reference']

                    if not reference or 'ORDER_ITEM__' not in reference:
                        continue

                    _, order_item_pk = reference.split('__')
                    if not OrderItem.objects.filter(pk=order_item_pk).count():
                        continue

                    order_item = OrderItem.objects.get(pk=order_item_pk)
                    if shipment['batch_status'] == 'postage_purchased_failed':
                        raise Exception(
                            "Shipment failed to purchase label"
                        )
                    shipment_instance, created = Shipment.objects\
                        .get_or_create(
                            order_item__pk=order_item_pk,
                            easypost_shipment_id=shipment['id']
                        )

                    if created:
                        shipment_instance.order_item = order_item
                        shipment_instance.save()

                    if shipment['batch_status'] == 'postage_purchased':
                        # NOTE: Shipments created via BATCH can be updated via
                        # webhook and we should not transit in this case
                        if order_item.status ==\
                                ORDER_ITEM_STATUS.label_pending:
                            order_item.label_printed()
                    else:
                        order_item.failed_to_print_label(Exception('Unexpected batch status.'))
                    order_item.save()

    except ValueError as e:
        print(e)
        return HttpResponseBadRequest(str(e))

    return JsonResponse({"status": True})
