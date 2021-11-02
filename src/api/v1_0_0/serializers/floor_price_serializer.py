from rest_framework import serializers

from application.models.floor_price import FloorPrice


class FloorPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FloorPrice
        exclude = ['created_at', 'updated_at']
