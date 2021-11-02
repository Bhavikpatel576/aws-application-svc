from application.models.internal_support_user import InternalSupportUser
from rest_framework import serializers

class InternalSupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalSupportUser
        fields = "first_name", "last_name", "phone", "email", "photo_url", "bio", "schedule_a_call_url"
