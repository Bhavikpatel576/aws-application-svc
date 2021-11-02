from rest_framework import serializers

from api.v1_0_0.serializers.current_home_serializers import AddressSerializer
from api.v1_0_0.serializers.rent_serializer import RentSerializer
from application.models.new_home_purchase import NewHomePurchase


class NewHomePurchaseSerializer(serializers.ModelSerializer):
    address = AddressSerializer()
    rent = RentSerializer()

    class Meta:
        model = NewHomePurchase
        exclude = ('created_at', 'updated_at')
