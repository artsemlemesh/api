from rest_framework import serializers
from app.models import Shipment, ShipmentTracker


class ShipmentTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentTracker
        fields = (
            'easypost_id', 'tracking_code', 'status', 'signed_by',
            'est_delivery_date', 'tracking_details' , 'tracking_url',
        )


class ShipmentSerializer(serializers.ModelSerializer):
    tracker = ShipmentTrackerSerializer(read_only=True)

    class Meta:
        model = Shipment
        fields = (
            'id', 'easypost_shipment_id', 'courier_id', 'label_url',
            'tracker', 'status')
