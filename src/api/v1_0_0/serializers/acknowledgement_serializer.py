from rest_framework.serializers import ModelSerializer

from api.v1_0_0.serializers.disclosure_serializer import DisclosureSerializer
from application.models.acknowledgement import Acknowledgement


class AcknowledgementSerializer(ModelSerializer):
    disclosure = DisclosureSerializer(read_only=True)

    class Meta:
        model = Acknowledgement
        fields = "id", "disclosure", "is_acknowledged", "ip_address", "updated_at", "acknowledged_at"
        read_only_fields = ('acknowledged_at',)
