from rest_framework import serializers

class MessageSerializer(serializers.Serializer):
    body = serializers.CharField(required=True, max_length=1500)
