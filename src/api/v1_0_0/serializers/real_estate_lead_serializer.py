from typing import Any

from rest_framework import serializers

from api.v1_0_0.serializers.application_serializers import CustomerSerializer
from api.v1_0_0.serializers.current_home_serializers import AddressSerializer
from application.tasks import push_lead_to_salesforce
from application.models.address import Address
from application.models.customer import Customer
from application.models.real_estate_lead import RealEstateLead


class RealEstateLeadSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer()
    address = AddressSerializer()

    def to_internal_value(self, data: Any) -> Any:
        first_name = data.pop('first_name', None)
        last_name = data.pop('last_name', None)
        phone = data.pop('phone', None)
        email = data.pop('email', None)

        if first_name is None:
            raise serializers.ValidationError({'first_name': "First name must be set."})
        elif last_name is None:
            raise serializers.ValidationError({'last_name': "Last name must be set."})
        elif phone is None:
            raise serializers.ValidationError({'phone': "Phone must be set."})
        elif email is None:
            raise serializers.ValidationError({'email': "Email must be set."})

        customer = {
            'name': "{} {}".format(first_name, last_name),
            'phone': phone,
            'email': email
        }

        data['customer'] = customer

        return super().to_internal_value(data)

    class Meta:
        model = RealEstateLead
        fields = '__all__'

    def create(self, validated_data: Any) -> Any:
        customer = validated_data.get('customer')
        customer = Customer.objects.create(**customer)
        validated_data['customer'] = customer

        address = validated_data.get('address')
        address = Address.objects.create(**address)
        validated_data['address'] = address

        lead = RealEstateLead.objects.create(**validated_data)
        push_lead_to_salesforce.delay(lead.pk)
        return lead
