from rest_framework import serializers

from blend.models import Followup


class FollowupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Followup
        fields = '__all__'