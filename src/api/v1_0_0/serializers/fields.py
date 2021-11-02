"""
Serializer custom fields.
"""

import re
from rest_framework import serializers


def validate_phone_number(value):
    """
    Custom validator for phone number field
    """
    if not re.match('(1-)?[0-9]{3}-[0-9]{3}-[0-9]{4}', value):
        raise serializers.ValidationError('Enter valid phone number.')


class PhoneNumberField(serializers.CharField, ):
    """
    Custom Phone Number field.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validators.append(validate_phone_number, )
