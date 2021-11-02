import logging
from utils.homeward_oauth import HomewardOauthClient
import uuid

from django.conf import settings


logger = logging.getLogger(__name__)


class PropertyDataAggregatorClientException(Exception):
    pass


class PropertyDataAggregatorClient(HomewardOauthClient):
    def __init__(self):
        super().__init__()
        self.property_data_aggregator_base_endpoint = settings.PROPERTY_DATA_AGGREGATOR_BASE_ENDPOINT

    def get_listing(self, pda_listing_uuid: uuid) -> dict:
        response = self.client.get(f'{self.property_data_aggregator_base_endpoint}listings/{pda_listing_uuid}')
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("Non-success response from property data aggregator", extra=dict(
                type="non_success_property_data_aggregator",
                status=response.status_code,
                reason=response.reason,
                pda_listing_uuid=pda_listing_uuid
            ))
            raise PropertyDataAggregatorClientException(f"unable to fetch listing")
