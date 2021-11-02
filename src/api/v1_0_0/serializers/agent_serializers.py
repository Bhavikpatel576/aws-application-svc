import logging

from rest_framework import serializers

from api.v1_0_0.serializers.brokerage_serializers import BrokerageSerializer
from application.models.agents import Agents
from application.models.brokerage import Brokerage
from application.models.real_estate_agent import RealEstateAgent
from utils.salesforce import homeward_salesforce

logger = logging.getLogger(__name__)


class CertifiedAgentSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()

    def get_phone(self, agent_obj):
        return agent_obj.get_formatted_phone()

    class Meta:
        model = RealEstateAgent
        fields = "id", "name", "phone", "email", "company"

    def create(self):
        pass

    def update(self):
        pass


class RealEstateAgentSerializer(serializers.ModelSerializer):
    """
    Model serializer for Real estate agent.
    """
    name = serializers.CharField(required=True, max_length=255)
    email = serializers.CharField(required=True, max_length=255)
    phone = serializers.CharField(required=True, max_length=255)
    brokerage = BrokerageSerializer(required=False)

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        if data.get('brokerage_sf_id'):
            try:
                ret['brokerage'] = Brokerage.objects.get(sf_id=data.get('brokerage_sf_id'))
            except Brokerage.DoesNotExist:
                sf_data = homeward_salesforce.get_account_by_id(data.get('brokerage_sf_id'))
                ret['brokerage'] = Brokerage.objects.create(name=sf_data.get(RealEstateAgent.NAME_FIELD),
                                                            partnership_status=sf_data.get(Brokerage.BROKER_PARTNERSHIP_STATUS_FIELD),
                                                            sf_id=data.get('brokerage_sf_id'))
        return ret

    class Meta:
        model = RealEstateAgent
        fields = "__all__"
        read_only_fields = ('id', )
        lookup_field = "sf_id"


class AgentsSerializer(serializers.Serializer):
    """
    Serializer for Agents.
    """
    buying_agent = RealEstateAgentSerializer(required=True, allow_null=True)
    listing_agent = RealEstateAgentSerializer(required=True, allow_null=True)
    needs_listing_agent = serializers.BooleanField()
    needs_buying_agent = serializers.BooleanField()

    class Meta:
        model = Agents
        fields = "__all__"

    def create(self, validated_data):
        return Agents(**validated_data)

    def update(self):
        pass
