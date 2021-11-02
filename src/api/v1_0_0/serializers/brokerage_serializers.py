from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from application.models.brokerage import Brokerage


class BrokerageSerializer(ModelSerializer):
    sf_id = serializers.CharField(write_only=True)

    class Meta:
        model = Brokerage
        fields = "id", "name", "partnership_status", "sf_id", "logo_url"
