"""
Serializers for current home model.
"""
import os
import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from expander import ExpanderSerializerMixin
from rest_framework import serializers

from api.v1_0_0.serializers.floor_price_serializer import FloorPriceSerializer
from application.models.models import (Address, CurrentHome, CurrentHomeImage,
                                       CurrentHomeImageStatus)
from utils.aws import check_if_object_exists, generate_presigned_url


class AddressSerializer(serializers.ModelSerializer):
    """
    Address model serializer.
    """

    class Meta:
        model = Address
        exclude = ('created_at', 'updated_at')
        extra_kwargs = {
            "id": {
                "read_only": False,
                "required": False
            }
        }


class CurrentHomeImageSerializer(serializers.ModelSerializer):
    """
    Model serializer for model CurrentHomeImage.
    """

    name = serializers.CharField(max_length=255, write_only=True)
    size = serializers.IntegerField(write_only=True)
    presign_detail = serializers.JSONField(
        required=False, read_only=True, allow_null=True)

    def validate(self, data):
        """
        Custom validate method.
        """
        if self.instance and data.get('status', '') == CurrentHomeImageStatus.UPLOADED:
            """
            This is confirmation that image is uploaded to S3.
            """
            if not check_if_object_exists(self.instance.url):
                raise serializers.ValidationError({'url': 'No object found on S3.'})
        return data

    def create(self, validated_data):
        """
        Custom Create method to generate pre-signed url for S3.
        """

        uid = str(uuid.uuid4())
        extension = os.path.splitext(validated_data.pop('name'))[1]
        url = ('%s/%s/%s%s' % (uid[0], uid[1], uid[2:], extension))
        validated_data.update({
            'url': url
        })
        size = validated_data.pop('size', 0)
        current_home_image = CurrentHomeImage.objects.create(**validated_data)
        if getattr(settings, 'APP_ENV', 'default') != 'test':
            current_home_image.presign_detail = generate_presigned_url(
                {'url': current_home_image.url, 'size': size})
        else:
            current_home_image.presign_detail = {}
        return current_home_image

    class Meta:
        model = CurrentHomeImage
        exclude = ('created_at', 'updated_at', )
        read_only_fields = ('url', )
        extra_kwargs = {
            "id": {
                "read_only": False,
                "required": False
            }
        }


class CurrentHomeSerializerBase(ExpanderSerializerMixin, serializers.ModelSerializer):
    """
    CurrentHome model base serializer.
    """
    address = AddressSerializer()
    @transaction.atomic
    def create(self, validated_data):
        """
        Custom create method
        """
        images = validated_data.pop('images', [])
        address = validated_data.pop('address', None)
        if address:
            address = Address.objects.create(**address)
            validated_data.update({'address': address})
        current_home = CurrentHome.objects.create(**validated_data)
        if images:
            for image in images:
                CurrentHomeImage.objects.create(current_home=current_home, **image)
        return current_home

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Custom update method.
        """
        address = validated_data.pop('address', None)
        images = validated_data.pop('images', [])
        if address:
            if instance.address:
                Address.objects.filter(pk=instance.address.pk).update(**address)
            else:
                address = Address.objects.create(**address)
                validated_data.update({'address': address})
        for image in images:
            image_id = image.pop('id', None)
            CurrentHomeImage.objects.filter(id=image_id).update(**image, updated_at=timezone.now())
        current_home = super(CurrentHomeSerializerBase, self).update(instance, validated_data)
        current_home_images = CurrentHomeImage.objects.filter(status=CurrentHomeImageStatus.LABELED)
        return CurrentHome.objects.prefetch_related(Prefetch('images', current_home_images)).get(pk=current_home.pk)
    
    class Meta:
        model = CurrentHome
        abstract = True
        expandable_fields = {
            'address': AddressSerializer
        }

class CurrentHomeSerializer(CurrentHomeSerializerBase):
    application_id = serializers.CharField(max_length=255, read_only=True)
    images = CurrentHomeImageSerializer(many=True)
    floor_price = FloorPriceSerializer(required=False)
    
    def validate_attributes(self, attributes):
        """
        Validate attributes field.
        """
        if self.instance and self.instance.attributes and attributes:
            updated_attributes = dict(self.instance.attributes)
            for key, value in attributes.items():
                if key in updated_attributes:
                    for inner_key, inner_value in value.items():
                        updated_attributes[key].update({
                            inner_key: inner_value
                        })
                else:
                    updated_attributes.update({
                        key: value
                    })
            return updated_attributes
        return attributes
    
    def validate_images(self, images):
        errors = []
        has_errors = False
        for image in images:
            if 'id' not in image:
                has_errors = True
                errors.append({'id': 'This field is required.'})
            else:
                errors.append({})
        if has_errors:
            raise serializers.ValidationError(errors)
        return images
    class Meta:
        model = CurrentHome
        exclude = ['customer_value_opinion', 'outstanding_loan_amount', 'final_sales_price']


class ApplicationCurrentHomeSerializer(CurrentHomeSerializerBase):
    class Meta:
        model = CurrentHome
        exclude = ['outstanding_loan_amount', 'final_sales_price', 'salesforce_id']
        expandable_fields = {
            'address': AddressSerializer
        }

    def get_fields(self, *args, **kwargs):
        fields = super(ApplicationCurrentHomeSerializer, self).get_fields(*args, **kwargs)
        request = self.context.get('request', None)
        if request and getattr(request, 'method', None) == "POST":
            fields['address'].required = True
        else:
            fields['address'].required = False
        return fields
