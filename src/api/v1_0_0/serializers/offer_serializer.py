import logging

import datetime

from django.conf import settings

from utils import date_restrictor
from rest_framework import serializers

from api.v1_0_0.serializers.current_home_serializers import AddressSerializer
from api.v1_0_0.serializers.new_home_purchase_serializer import NewHomePurchaseSerializer
from application.models.address import Address
from application.models.application import Application, ApplicationStage, ProductOffering
from application.models.offer import Offer

logger = logging.getLogger(__name__)


class OfferSerializer(serializers.ModelSerializer):
    application_id = serializers.PrimaryKeyRelatedField(required=True,
                                                        queryset=Application.objects.all())
    offer_property_address = AddressSerializer(required=False)
    new_home_purchase = NewHomePurchaseSerializer(read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "year_built",
            "home_square_footage",
            "property_type",
            "less_than_one_acre",
            "home_list_price",
            "offer_price",
            "contract_type",
            "other_offers",
            "offer_deadline",
            "plan_to_lease_back_to_seller",
            "waive_appraisal",
            "already_under_contract",
            "comments",
            "application_id",
            "offer_property_address",
            "status",
            "pda_listing_uuid",
            'mls_listing_id',
            "preferred_closing_date",
            "photo_url",
            "bathrooms",
            "bedrooms",
            "offer_source",
            "created_at",
            "updated_at",
            "new_home_purchase",
        ]

    def create(self, validated_data):
        logger.info("Creating offer", extra=dict(
            type="create_offer",
            data=validated_data
        ))
        if validated_data.get('offer_property_address'):
            validated_data['offer_property_address'] = Address.objects.create(**validated_data.pop('offer_property_address'))
        validated_data['offer_source'] = 'dashboard'
        if validated_data.get('application_id'):
            validated_data['application_id'] = validated_data['application_id'].id
        return super(OfferSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        logger.info("Updating offer", extra=dict(
            type="update_offer",
            data=validated_data
        ))
        if validated_data.get('offer_property_address'):
            validated_data['offer_property_address'] = Address.objects.create(**validated_data.pop('offer_property_address'))
            if not validated_data.get('pda_listing_uuid'):
                # manually entered offer property address, need to reset pda listing info
                validated_data['pda_listing_uuid'] = None
        if validated_data.get('application_id'):
            validated_data['application_id'] = validated_data['application_id'].id
        return super().update(instance, validated_data)

    def validate(self, attrs):
        application = attrs.get('application_id') or self.instance.application
        self.validate_offer_application(application)

        preferred_closing_date = attrs.get('preferred_closing_date')
        if preferred_closing_date and settings.VALIDATE_PREFERRED_CLOSING_DATE:
            if (not self.instance) or (preferred_closing_date != self.instance.preferred_closing_date):
                self.validate_preferred_closing_date_restrictions(attrs.get('created_at'), preferred_closing_date, application.product_offering)

        return super(OfferSerializer, self).validate(attrs)

    def validate_offer_application(self, application):
        if application is None:
            raise serializers.ValidationError("offer not affiliated to an application!")
        if application.stage not in [ApplicationStage.QUALIFIED_APPLICATION,
                                     ApplicationStage.APPROVED,
                                     ApplicationStage.OFFER_REQUESTED,
                                     ApplicationStage.OFFER_SUBMITTED]:
            raise serializers.ValidationError(f'application stage must be qualified, approved, offer requested or '
                                              f'offer submitted, is currently {application.stage}')

    def validate_preferred_closing_date_restrictions(self, offer_created_date: datetime.datetime,
                                                     preferred_closing_date: datetime.date, product_offering):
        product_offering = self.__get_product_offering(product_offering)
        offer_created_date = self.__get_offer_created_date(offer_created_date)
        earliest_close_date = date_restrictor.get_earliest_close_date(product_offering, offer_created_date)
        latest_close_date = date_restrictor.get_latest_close_date(offer_created_date)
        self.__validate_preferred_closing_date_too_early(preferred_closing_date, earliest_close_date)
        self.__validate_preferred_closing_date_too_late(preferred_closing_date, latest_close_date)
        self.__validate_preferred_closing_date_restricted(preferred_closing_date, earliest_close_date, latest_close_date)

    def __validate_preferred_closing_date_too_early(self, preferred_closing_date: datetime.date,
                                                    earliest_close_date: datetime.date):
        if preferred_closing_date < earliest_close_date:
            raise serializers.ValidationError({'preferred_closing_date': f'preferred closing date of {preferred_closing_date} cannot be before {earliest_close_date}'})

    def __validate_preferred_closing_date_too_late(self, preferred_closing_date: datetime.date, latest_close_date: datetime.date):
        if preferred_closing_date > latest_close_date:
            raise serializers.ValidationError({'preferred_closing_date': f'preferred closing date of {preferred_closing_date} cannot be after {latest_close_date}'})

    def __validate_preferred_closing_date_restricted(self, preferred_closing_date: datetime.date,
                                                     earliest_close_date: datetime.date,
                                                     latest_close_date: datetime.date):
        restricted_dates = date_restrictor.calculate_restricted_dates(earliest_close_date, latest_close_date)
        if preferred_closing_date in restricted_dates:
            raise serializers.ValidationError({'preferred_closing_date': f'preferred closing date of {preferred_closing_date} cannot be on a restricted date'})

    def __get_offer_created_date(self, offer_created_date: datetime.datetime):
        return offer_created_date or datetime.datetime.now()

    def __get_product_offering(self, product_offering):
        if not product_offering:
            raise serializers.ValidationError('application affiliated with offer does not define the product offering')
        return ProductOffering(product_offering)
