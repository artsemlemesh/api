from django.conf import settings
import jwt


class EventTypes:
    # constants for event types
    Shipment_Label_Created = "shipment.label.created"
    Shipment_Tracking_Checkpoints_Created = "shipment.tracking.checkpoints.created"
    Shipment_Cancelled = "shipment.cancelled"
    Shipment_Tracking_Status_Changed = "shipment.tracking.status.changed"
    Shipment_Label_Failed = "shipment.label.failed"
    Shipment_Warehouse_State_Updated = "shipment.warehouse.state.updated"

"""
Function to validate easyship request
"""


def is_valid_request(request):
    try:
        eship_request_signature = request.META['HTTP_X_EASYSHIP_SIGNATURE']
        decodedObj = jwt.decode(eship_request_signature, settings.EASY_SHIP_SECRET_KEY)
        if decodedObj is not None and decodedObj['easyship_company_id'] is not None:
            return True
        else:
            return False
    except:
        return False


"""
Function to handle easyship shipment.label.created event 
"""


def handle_label_created_event(request):
    print("label created flow")


"""
Function to handle easyship shipment.tracking.checkpoints.created 
"""


def handle_tracking_checkpoints_created_event(request):
    print("tracking checkpoints flow")


"""
Function to handle easyship shipment.cancelled
"""


def handle_shipment_cancelled_event(request):
    print("shipments cancelled flow")


"""
Function to handle easyship shipment.tracking.status.changed
"""


def handle_tracking_status_changed_event(request):
    print("tracking status changed flow")


"""
Function to handle easyship shipment.label.failed
"""


def handle_label_failed_event(request):
    print("label failed event")


"""
Function to handle easyship shipment.warehouse.state.updated
"""


def handle_warehouse_state_updated_event(request):
    print("warehouse state changed")
