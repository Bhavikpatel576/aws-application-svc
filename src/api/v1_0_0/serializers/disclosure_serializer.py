from rest_framework.serializers import ModelSerializer

from application.models.disclosure import Disclosure


class DisclosureSerializer(ModelSerializer):

    class Meta:
        model = Disclosure
        fields = "id", "name", "document_url"
