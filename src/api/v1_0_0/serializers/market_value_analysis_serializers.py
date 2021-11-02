"""
Serializers for Market value analysis of application.
"""
from django.db import transaction
from rest_framework import serializers

from application.models.models import (MarketValuation,
                                       MarketValueReport,
                                       MarketValueOpinion,
                                       MarketValueOpinionComment,
                                       Comparable, Address, User)
from .current_home_serializers import AddressSerializer
from .user_serializers import UserSerializer


class MarketValueReportSerializer(serializers.ModelSerializer):
    """
    Model serializer for model MarketValueReport
    """

    class Meta:
        model = MarketValueReport
        exclude = ('created_at', 'updated_at')
        read_only_fields = ('market_valuation',)
        extra_kwargs = {
            "id": {
                "read_only": False,
                "required": False
            }
        }


class MarketValueOpinionCommentSerializer(serializers.ModelSerializer):
    """
    Model serializer for model MarketValueAnalysisComment
    """

    class Meta:
        model = MarketValueOpinionComment
        exclude = ('created_at', 'updated_at')
        read_only_fields = ('market_value_opinion',)
        extra_kwargs = {
            "id": {
                "read_only": False,
                "required": False
            }
        }


class MarketValueOpinionSerializer(serializers.ModelSerializer):
    """
    Model serializer for model MarketValueOpinions
    """
    comments = MarketValueOpinionCommentSerializer(many=True, required=False)

    def validate(self, data):
        """
        Custom validate method.
        """
        error = {}
        self.instance = MarketValueOpinion.objects.get(
            id=data['id']) if data.get('id') else None
        if ('minimum_sales_price' in data and 'maximum_sales_price' in data and not data['minimum_sales_price'] and not data['maximum_sales_price']):
            return data
        if self.instance and data.get('minimum_sales_price') and self.instance.minimum_sales_price == data.get('minimum_sales_price') and data.get('maximum_sales_price') and data.get('minimum_sales_price') > data.get('maximum_sales_price'):
            error['maximum_sales_price'] = "Max value must be higher than min value"
        elif self.instance and data.get('maximum_sales_price') and self.instance.maximum_sales_price == data.get('maximum_sales_price') and data.get('minimum_sales_price') and self.instance.maximum_sales_price < data.get('minimum_sales_price'):
            error["minimum_sales_price"] = "Min value must be lower than max value"
        elif data.get('minimum_sales_price') and not data.get('maximum_sales_price'):
            error["maximum_sales_price"] = "This field should not be null"
        elif data.get('maximum_sales_price') and not data.get('minimum_sales_price'):
            error["minimum_sales_price"] = "This field should not be null"
        elif ((data.get('minimum_sales_price') and data.get('maximum_sales_price') and data['minimum_sales_price'] == data['maximum_sales_price'])
              or (data.get('minimum_sales_price') and not data.get('maximum_sales_price') and data['minimum_sales_price'] == self.instance.maximum_sales_price)
              or (not data.get('minimum_sales_price') and data.get('maximum_sales_price') and self.instance.minimum_sales_price == data['maximum_sales_price'])):
            error["minimum_sales_price"] = "Values must be different"
        elif (data.get('minimum_sales_price') and not data.get('maximum_sales_price')
              and self.instance.maximum_sales_price and data['minimum_sales_price'] > self.instance.maximum_sales_price):
            error["minimum_sales_price"] = "Min value must be lower than max value"
        elif ((data.get('minimum_sales_price') and data.get('maximum_sales_price') and data['minimum_sales_price'] > data['maximum_sales_price'])
              or ('minimum_sales_price' not in data and 'maximum_sales_price' in data and self.instance.minimum_sales_price > data['maximum_sales_price'])):
            error["maximum_sales_price"] = "Max value must be higher than min value"
        if error:
            raise serializers.ValidationError(error)
        return data

    class Meta:
        model = MarketValueOpinion
        exclude = ('created_at', 'updated_at')
        read_only_fields = ('market_valuation',)
        extra_kwargs = {
            "id": {
                "read_only": False,
                "required": False
            }
        }


class ComparableSerializer(serializers.ModelSerializer):
    """
    Model serializer for model Comparable.
    """

    address = AddressSerializer()
    verified_by = UserSerializer(required=False)
    is_verified = serializers.BooleanField(write_only=True, default=False)

    def validate(self, validated_data):
        if 'is_verified' in validated_data:
            is_verified = validated_data.pop('is_verified')
            if is_verified:
                verified_by = User.objects.get(
                    id=self.context['request'].user.id)
            else:
                verified_by = None
            validated_data.update({'verified_by': verified_by})
        return validated_data

    class Meta:
        model = Comparable
        exclude = ('created_at', 'updated_at')
        read_only_fields = ('market_valuation', 'verified_by')
        extra_kwargs = {
            "id": {
                "read_only": False,
                "required": False
            }
        }


class MarketValuationSerializer(serializers.ModelSerializer):
    """
    Model serializer for model MarketValueAnalysis.
    """

    avm = MarketValueReportSerializer(many=True, required=False)
    value_opinions = MarketValueOpinionSerializer(many=True, required=False)
    comparables = ComparableSerializer(many=True, required=False)

    @transaction.atomic
    def create(self, validated_data):
        """
        Custom create method to create market valuation.
        """
        comparables = validated_data.pop('comparables', [])
        value_opinions = validated_data.pop('value_opinions', [])
        avm_reports = validated_data.pop('avm', [])
        market_valuation, created = MarketValuation.objects.update_or_create(
            current_home=validated_data['current_home'], defaults=validated_data)
        comment_objs = []
        for report in avm_reports:
            report.update({
                'market_valuation': market_valuation
            })
            MarketValueReport.objects.create(**report)
        for value_opinion in value_opinions:
            comments = value_opinion.pop('comments', [])
            value_opinion.update({
                'market_valuation': market_valuation
            })
            market_value_opinion = MarketValueOpinion.objects.create(
                **value_opinion)
            for comment in comments:
                comment_objs.append(
                    MarketValueOpinionComment(
                        market_value_opinion=market_value_opinion, **comment)
                )
        MarketValueOpinionComment.objects.bulk_create(comment_objs)
        for comparable in comparables:
            address_data = comparable.pop('address', {})
            address = Address.objects.create(**address_data)
            comparable.update({
                'market_valuation': market_valuation,
                'address': address
            })
            Comparable.objects.create(**comparable)
        return market_valuation

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Custom update method to update market valuation
        """
        if 'avm' in validated_data:
            avm_reports = validated_data.pop('avm', [])
            for report in avm_reports:
                report_id = report.pop('id', None)
                MarketValueReport.objects.update_or_create(
                    id=report_id, market_valuation=instance, defaults=report)

        if 'value_opinions' in validated_data:
            value_opinions = validated_data.pop('value_opinions', [])
            for value_opinion in value_opinions:
                comments = value_opinion.pop('comments', [])
                value_opinion_id = value_opinion.pop('id', None)
                value_opinion_obj, created = MarketValueOpinion.objects.update_or_create(
                    id=value_opinion_id, market_valuation_id=instance.id, defaults=value_opinion)
                comment_ids = list(MarketValueOpinionComment.objects.filter(
                    market_value_opinion=value_opinion_obj).values_list('id', flat=True))
                for comment in comments:
                    comment_id = comment.pop('id', None)
                    if comment_id and comment_id in comment_ids:
                        comment_ids.remove(comment_id)
                    MarketValueOpinionComment.objects.update_or_create(
                        id=comment_id, market_value_opinion=value_opinion_obj, defaults=comment)
                MarketValueOpinionComment.objects.filter(
                    id__in=comment_ids).delete()
        if 'comparables' in validated_data:
            comparables = validated_data.pop('comparables', [])
            comparable_ids = list(Comparable.objects.filter(
                market_valuation=instance).values_list('id', flat=True))
            for comparable in comparables:
                address = comparable.pop('address', {})
                address_id = address.pop('id', None)
                address, _ = Address.objects.update_or_create(
                    id=address_id, defaults=address)
                comparable.update({'address': address})
                comparable_id = comparable.pop('id', None)
                if comparable_id and comparable_id in comparable_ids:
                    comparable_ids.remove(comparable_id)
                comparables_obj, created = Comparable.objects.update_or_create(
                    id=comparable_id, market_valuation=instance, defaults=comparable)
            Comparable.objects.filter(id__in=comparable_ids).delete()
        return super().update(instance, validated_data)

    class Meta:
        model = MarketValuation
        exclude = ('created_at', 'updated_at')
