from rest_framework import serializers

from api.v1_0_0.serializers.current_home_serializers import AddressSerializer
from api.v1_0_0.serializers.agent_serializers import RealEstateAgentSerializer
from application.models.address import Address
from application.models.pricing import Pricing


class PricingSerializer(serializers.ModelSerializer):
    agent = RealEstateAgentSerializer(required=False)
    agent_id = serializers.UUIDField(required=False)
    selling_location = AddressSerializer(required=False)
    buying_location = AddressSerializer()

    class Meta:
        model = Pricing
        read_only_fields = [
            'estimated_min_convenience_fee',
            'estimated_max_convenience_fee',
            'estimated_earnest_deposit_percentage',
            'estimated_min_rent_amount',
            'estimated_max_rent_amount',
            'created_at',
            'updated_at',
            'questionnaire_response_id',
            'customer_email'
        ]

        write_only_fields = [
            'buying_location',
            'selling_location',
            'min_price',
            'max_price',
            'agents_company',
            'agent_situation',
            'utm'
        ]

        fields = [
                     'id',
                     'actions',
                     'agent_remarks',
                     'agent',
                     'agent_id',
                     'product_offering',
                     'shared_on_date'
                 ] + read_only_fields + write_only_fields

    def create(self, validated_data):
        validated_data['buying_location'] = Address.objects.create(**validated_data.pop('buying_location'))
        if validated_data.get('selling_location'):
            validated_data['selling_location'] = Address.objects.create(**validated_data.pop('selling_location'))
        return Pricing.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('buying_location'):
            validated_data['buying_location'] = Address.objects.create(**validated_data.pop('buying_location'))
        if validated_data.get('selling_location'):
            validated_data['selling_location'] = Address.objects.create(**validated_data.pop('selling_location'))
        return super().update(instance, validated_data)
