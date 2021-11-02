from rest_framework import serializers

from application.models.rent import Rent


class RentSerializer(serializers.ModelSerializer):
    accrued_rent = serializers.ReadOnlyField()
    future_rent_to_be_charged = serializers.ReadOnlyField()
    estimated_total_rent = serializers.ReadOnlyField()
    estimated_total_rent_before_credits = serializers.ReadOnlyField()

    class Meta:
        model = Rent
        exclude = ('created_at', 'updated_at')
