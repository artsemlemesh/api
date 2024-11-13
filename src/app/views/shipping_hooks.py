from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.renderers import JSONRenderer
from ..utils.notification import send_push_message
from django.contrib.auth import get_user_model
from ..services.easyship_webhook import *

@csrf_exempt
@api_view(('POST',))
def eship_hook(request):
    # request.data contains payload info that will be used for different events accordingly
    try:
        if is_valid_request(request):
            if request.data['event_type'] == EventTypes.Shipment_Label_Created:
                handle_label_created_event(request)
            elif request.data['event_type'] == EventTypes.Shipment_Label_Failed:
                handle_label_failed_event(request)
            elif request.data['event_type'] == EventTypes.Shipment_Cancelled:
                handle_shipment_cancelled_event(request)
            elif request.data['event_type'] == EventTypes.Shipment_Tracking_Checkpoints_Created:
                handle_tracking_checkpoints_created_event(request)
            elif request.data['event_type'] == EventTypes.Shipment_Tracking_Status_Changed:
                handle_tracking_status_changed_event(request)
            elif request.data['event_type'] == EventTypes.Shipment_Warehouse_State_Updated:
                handle_warehouse_state_updated_event(request)

            # TODO: do necessary work
            # save request data in db for logging purposes
            # save particular event data properly in separate table

            email = request.data.get("email")
            buyer_email = get_user_model().objects.get(email = email)
            buyer_token = buyer_email.expo_push_token
            send_push_message(buyer_token,'Your bundle has shipped!',{
                "purchased_by": buyer_email,
            })
            response = Response(
                {"data": "Success"},
                content_type="application/json",
                status=status.HTTP_200_OK,
            )
            response.accepted_renderer = JSONRenderer()
            response.accepted_media_type = "application/json"
            response.renderer_context = {}
            return response
        else:
            response = Response(
                {"data": "Failure"},
                content_type="application/json",
                status=status.HTTP_400_BAD_REQUEST,
            )
            response.accepted_renderer = JSONRenderer()
            response.accepted_media_type = "application/json"
            response.renderer_context = {}
            return response
    except:
        response = Response(
            {"data": "Internal Server Error"},
            content_type="application/json",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        response.accepted_renderer = JSONRenderer()
        response.accepted_media_type = "application/json"
        response.renderer_context = {}
        return response