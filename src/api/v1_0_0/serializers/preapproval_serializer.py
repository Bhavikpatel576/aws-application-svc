from rest_framework import serializers

from application.models.preapproval import PreApproval


class PreApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreApproval
        exclude = ('created_at', 'updated_at')
