from rest_framework import serializers

from application.models.loan import Loan


class LoanSerializer(serializers.ModelSerializer):
    net_convenience_fee = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = ('id', 'base_convenience_fee', 'estimated_broker_convenience_fee_credit',
                  'estimated_mortgage_convenience_fee_credit', 'estimated_daily_rent', 'estimated_monthly_rent',
                  'estimated_earnest_deposit_percentage', 'net_convenience_fee', 'created_at', 'updated_at')
        read_only_fields = ('id', 'base_convenience_fee', 'estimated_broker_convenience_fee_credit',
                            'estimated_mortgage_convenience_fee_credit', 'estimated_daily_rent',
                            'estimated_monthly_rent', 'estimated_earnest_deposit_percentage', 'net_convenience_fee',
                            'created_at', 'updated_at')

    def get_net_convenience_fee(self, obj):
        if not obj.base_convenience_fee \
                and not obj.estimated_broker_convenience_fee_credit \
                and not obj.estimated_mortgage_convenience_fee_credit:
            return None

        base_convenience_fee = obj.base_convenience_fee if obj.base_convenience_fee else 0
        estimated_broker_convenience_fee_credit = obj.estimated_broker_convenience_fee_credit if obj.estimated_broker_convenience_fee_credit else 0
        estimated_mortgage_convenience_fee_credit = obj.estimated_mortgage_convenience_fee_credit if obj.estimated_mortgage_convenience_fee_credit else 0

        return (base_convenience_fee - estimated_broker_convenience_fee_credit -
                estimated_mortgage_convenience_fee_credit)
