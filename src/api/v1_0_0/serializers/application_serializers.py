"""
Application app serializers.
"""

import re

from django.db import models
from expander import ExpanderSerializerMixin
from rest_framework import serializers
from rest_framework.fields import BooleanField

from application.models.builder import Builder
from application.models.customer import Customer
from application.models.models import (Address, Application, Note, NoteType)
from application.models.mortgage_lender import MortgageLender
from application.models.task import Task
from application.models.task_status import TaskStatus
from .agent_serializers import RealEstateAgentSerializer
from .current_home_serializers import AddressSerializer, CurrentHomeSerializer
from .fields import PhoneNumberField
from .user_serializers import UserSerializer


class CustomerSerializer(serializers.ModelSerializer):
    """
    Customer model serializer.
    """
    phone = PhoneNumberField()

    def validate_name(self, validate_data):
        """
        validates customer name
        """
        if not re.match(r'^[a-zA-Z]', validate_data):
            raise serializers.ValidationError({'name': "First character should be alphabet."})
        return validate_data

    class Meta:
        model = Customer
        fields = '__all__'


class MortgageLenderSerializer(serializers.ModelSerializer):
    """
    Model serializer for MortgageLender.
    """
    phone = PhoneNumberField(allow_blank=True)

    class Meta:
        model = MortgageLender
        fields = "__all__"
        read_only_fields = ('id', )


class BuilderSerializer(ExpanderSerializerMixin, serializers.ModelSerializer):
    """
    Model serializer for model Builder.
    """
    address = AddressSerializer(required=False, allow_null=True)

    def create(self, validated_data):
        address = validated_data.pop('address', None)
        if address:
            address = Address.objects.create(**address)
            validated_data.update({'address': address})
        return Builder.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Custom update method.
        """
        address = validated_data.pop('address', None)
        if address:
            address_serializer = AddressSerializer(instance=instance.address, data=address, partial=True)
            if not address_serializer.is_valid():
                raise serializers.ValidationError({'address': address_serializer.errors})
            else:
                validated_data.update({'address': address_serializer.save()})
        return super(BuilderSerializer, self).update(instance, validated_data)

    class Meta:
        model = Builder
        fields = "__all__"
        read_only_fields = ('id', )
        expandable_fields = {
            'address': AddressSerializer
        }


class ApplicationSerializer(ExpanderSerializerMixin, serializers.ModelSerializer):
    """
    Application model serializer.
    """

    comment = serializers.CharField(required=False, allow_null=True, write_only=True)
    customer = CustomerSerializer()
    current_home = CurrentHomeSerializer(required=False, allow_null=True)
    builder = BuilderSerializer(required=False, allow_null=True)
    mortgage_lender = MortgageLenderSerializer(required=False, allow_null=True)
    real_estate_agent = RealEstateAgentSerializer(required=False, allow_null=True)
    offer_property_address = AddressSerializer(required=False, allow_null=True)

    needs_listing_agent = models.NullBooleanField()
    needs_buying_agent = models.NullBooleanField()

    class Meta:
        model = Application
        fields = "__all__"
        read_only_fields = ('id', )

    def validate(self, data):
        """
        Validate min_price field
        """
        error = {}
        if ('min_price' in data and 'max_price' in data and not data['min_price'] and not data['max_price']):
            return data
        if 'min_price' in data and 'max_price' not in data and self.instance is None:
            error["max_price"] = "This field should not be null"
        elif 'max_price' in data and 'min_price' not in data and self.instance is None:
            error["min_price"] = "This field should not be null"
        elif (('min_price' in data and 'max_price' in data and data['min_price'] == data['max_price'])
              or ('min_price' in data and 'max_price' not in data and data['min_price'] == self.instance.max_price)
              or ('min_price' not in data and 'max_price' in data and self.instance.min_price == data['max_price'])):
            error["min_price"] = "Values must be different"
        elif 'min_price' in data and 'max_price' not in data and data['min_price'] > self.instance.max_price:
            error["min_price"] = "Min value must be lower than max value"
        elif (('min_price' in data and 'max_price' in data and data['min_price'] > data['max_price'])
              or ('min_price' not in data and 'max_price' in data and self.instance.min_price > data['max_price'])):
            error["max_price"] = "Max value must be higher than min value"
        if error:
            raise serializers.ValidationError(error)
        return data

    def update(self, instance, validated_data):  # pylint: disable=too-many-branches
        customer = validated_data.pop('customer', None)
        if customer:
            customer_serializer = CustomerSerializer(instance=instance.customer, data=customer, partial=True)
            customer_serializer.is_valid(raise_exception=True)
            customer_serializer.save()
        if 'current_home' in validated_data:
            current_home = validated_data.pop('current_home', None)
            if current_home is None and instance.current_home:
                instance.current_home.delete()
                validated_data.update({'current_home': None})
            else:
                current_home_serializer = CurrentHomeSerializer(instance=instance.current_home, data=current_home, partial=True)
                current_home_serializer.is_valid(raise_exception=True)
                validated_data.update({'current_home': current_home_serializer.save()})
        if 'builder' in validated_data:
            builder = validated_data.pop('builder', None)
            if builder is None and instance.builder:
                instance.builder.delete()
                validated_data.update({'builder': None})
            elif builder is not None:
                builder_serializer = BuilderSerializer(instance=instance.builder, data=builder, partial=True)
                builder_serializer.is_valid(raise_exception=True)
                validated_data.update({'builder': builder_serializer.save()})
        if 'real_estate_agent' in validated_data:
            real_estate_agent = validated_data.pop('real_estate_agent', None)
            if real_estate_agent is None and instance.real_estate_agent:
                instance.real_estate_agent.delete()
                validated_data.update({'real_estate_agent': None})
            elif real_estate_agent is not None:
                real_estate_agent_serializer = RealEstateAgentSerializer(instance=instance.real_estate_agent, data=real_estate_agent, partial=True)
                real_estate_agent_serializer.is_valid(raise_exception=True)
                validated_data.update({'real_estate_agent': real_estate_agent_serializer.save()})
        if 'mortgage_lender' in validated_data:
            mortgage_lender = validated_data.pop('mortgage_lender', None)
            if mortgage_lender is None and instance.mortgage_lender:
                instance.mortgage_lender.delete()
                validated_data.update({'mortgage_lender': None})
            elif mortgage_lender is not None:
                mortgage_lender_serializer = MortgageLenderSerializer(instance=instance.mortgage_lender, data=mortgage_lender, partial=True)
                mortgage_lender_serializer.is_valid(raise_exception=True)
                validated_data.update({'mortgage_lender': mortgage_lender_serializer.save()})
        if 'offer_property_address' in validated_data:
            offer_property_address = validated_data.pop('offer_property_address', None)
            if offer_property_address is None and instance.offer_property_address:
                instance.offer_property_address.delete()
                validated_data.update({'offer_property_address': None})
            elif offer_property_address is not None:
                offer_property_address_serializer = AddressSerializer(
                    instance=instance.offer_property_address, data=offer_property_address, partial=True)
                offer_property_address_serializer.is_valid(raise_exception=True)
                validated_data.update({'offer_property_address': offer_property_address_serializer.save()})

        if validated_data.get('stage') and instance.stage and validated_data.get('stage') != instance.stage:
            user = getattr(getattr(self, 'context', {}).get('request', object), 'user', None)
            title = "{} to {}".format(instance.stage, validated_data.get('stage'))
            Note.objects.create(title=title, note=validated_data.get('comment', '<p></p>'),
                                type=NoteType.APPLICATION_STAGE, application=instance, author=user)
        return super().update(instance, validated_data)


class NoteSerializer(ExpanderSerializerMixin, serializers.ModelSerializer):
    """
    Note model serializer
    """
    author = UserSerializer(read_only=True)

    class Meta:
        model = Note
        fields = "__all__"


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "id", "name", "category", "options", "is_editable"


class TaskStatusSerializer(serializers.ModelSerializer):
    task_obj = TaskSerializer(read_only=True)
    is_actionable = BooleanField()

    class Meta:
        model = TaskStatus
        fields = "__all__"
