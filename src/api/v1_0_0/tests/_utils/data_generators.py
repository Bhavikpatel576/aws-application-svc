"""
Fake data generator.
"""
import os
import uuid
from datetime import datetime
from requests import Response

from application.models.real_estate_agent import RealEstateAgent
from application.models.builder import Builder
from application.models.models import CurrentHome, Address
from application.models.mortgage_lender import MortgageLender
from application.models.application import ProductOffering


def get_fake_user(key):
    return {
        "first_name": "test fn {}".format(key),
        "last_name": "test ln {}".format(key),
        "email": "test_{0}@{0}mail.com".format(key),
        "username": "username{}".format(key)
    }


def get_fake_customer(key):
    return {
        "name": "testname {}".format(key),
        "email": "testemail_{}@testmail.com".format(key),
        "phone": "123-123-1231"
    }


def get_fake_address(key):
    return {
        "street": "teststreet {}".format(key),
        "city": "testcity {}".format(key),
        "state": "teststate {}".format(key),
        "zip": "12345"
    }


def get_fake_currenthome(address):
    return {
        "address": address,
    }


def get_fake_mortgage_lender(key):
    return {
        'name': '{} lender'.format(key),
        'email': '{0}@{0}mail.com'.format(key),
        'phone': '1-111-111-1111'
    }


def get_fake_real_estate_agent(key, email=None):
    return {
        'name': '{} agent'.format(key),
        'email': email or '{0}@{0}mail.com'.format(key),
        'phone': '1-111-111-1111'
    }


def get_fake_builder(key):
    return {
        'company_name': '{} builder'.format(key),
        'address': Address.objects.create(**get_fake_address(key))
    }


def get_fake_application(key, buying_agent=None):
    return {
        "shopping_location": "testloc {}".format(key),
        "home_buying_stage": "researching online",
        "stage": "complete",
        "move_in": "0-3 months",
        "mortgage_lender": MortgageLender.objects.create(**get_fake_mortgage_lender(key)),
        "builder": Builder.objects.create(**get_fake_builder(key)),
        "real_estate_agent": RealEstateAgent.objects.create(**get_fake_real_estate_agent(key)),
        "min_price": 100000.00,
        "max_price": 3000000.00,
        "move_by_date": datetime.strptime("2019-12-31", "%Y-%m-%d"),
        "offer_property_address": Address.objects.create(**get_fake_address('{}offeraddress'.format(key))),
        "buying_agent": buying_agent,
    }


def get_fake_market_value_opinion(**kwargs):
    defaults = {
        "suggested_list_price": 250000.00,
        "minimum_sales_price": 200000.00,
        "maximum_sales_price": 300000.00,
        "sales_price_confidence": "High",
        "estimated_days_on_market": "0-30",
        "type": "local_agent",
        "comments": [
            {
                "is_favorite": True,
                "comment": "some comment"
            }
        ]
    }
    defaults.update(kwargs)
    return defaults


def get_fake_primary_comparable(**kwargs):
    defaults = {
        "comparable_type": "Subject property",
        "comment": "Some comment",
        "address": {
            "street": "Test street",
            "city": "Pune",
            "state": "Maharashtra",
            "zip": 12345
        }
    }
    defaults.update(kwargs)
    return defaults


def get_fake_market_valuation(current_home_id, **kwargs):
    defaults = {
        "current_home": str(current_home_id),
        "property_condition": "Poor",
        "is_in_completed_neighborhood": True,
        "is_less_than_one_acre": True,
        "is_built_after_1960": True,
        "value_opinions": [get_fake_market_value_opinion()],
        "comparables": [get_fake_primary_comparable()]
    }
    defaults.update(kwargs)
    return defaults


def get_fake_note(application_id):
    return {
        "application": application_id,
        "title": "Fake Note Title",
        "note": "<p> created <strong>Fake</strong> note<p>"
    }


def get_fake_current_home_image(key, current_home=None):
    if current_home is None:
        address = Address.objects.create(**get_fake_address(key))
        current_home = CurrentHome.objects.create(**get_fake_currenthome(address))
    uid = str(uuid.uuid4())
    extension = os.path.splitext('key.jpg')[1]
    url = ('%s/%s/%s%s' % (uid[0], uid[1], uid[2:], extension))
    return {
        "label": "kitchen",
        "current_home": current_home,
        "url": url
    }


def get_custom_view(name, fields=[]):
    return {
        "name": name,
        "application_listing_fields": str(fields)
    }


def get_fake_real_estate_lead() -> dict:
    return {
        "first_name": "Bob",
        "last_name": "Beaver",
        "email": "bob.beaver@gmail.com",
        "phone": "512-555-1234",
        "address": {
            "street": "1234 Main St.",
            "city": "Minneapolis",
            "state": "MN",
            "zip": "12345"
        },
        "needs_buying_agent": True,
        "needs_listing_agent": False,
        "home_buying_stage": "researching online"
    }

def get_fake_real_estate_lead_with_bad_payload(field: str = None) -> dict:
    lead_payload = {
        "first_name": "Bob",
        "last_name": "Beaver",
        "email": "bob.beaver@gmail.com",
        "phone": "512-555-1234",
        "address": {
            "street": "1234 Main St.",
            "city": "Minneapolis",
            "state": "MN",
            "zip": "12345"
        },
        "needs_buying_agent": True,
        "needs_listing_agent": False,
        "home_buying_stage": "researching online"
    }

    del lead_payload[field]

    return lead_payload


def get_fake_pricing() -> dict:
    return {
        "min_price": 600000,
        "max_price": 650000,
        "product_offering": ProductOffering.BUY_SELL.value,
        "estimated_min_convenience_fee": .01,
        "estimated_max_convenience_fee": .02,
        "estimated_min_rent_amount": 1500.0,
        "estimated_max_rent_amount": 3000.0,
        "updated_at": datetime.utcnow(),
        "questionnaire_response_id": "68e65ad9-e314-42b5-8b64-c5e8b4c4a5dc"
    }


class BaseMockedOKRequestsResponse(Response):
    def __init__(self):
        super().__init__()
        self.status_code = 200

    def json(self):
        return {}


class MockedAgentUserResponse(BaseMockedOKRequestsResponse):
    def json(self):
        return {"groups": ["Verified Email", "Claimed Agent"]}


class MockedNoGroupsUserReponse(BaseMockedOKRequestsResponse):
    def json(self):
        return {}


class MockedAgentOnlyUserReponse(BaseMockedOKRequestsResponse):
    def json(self):
        return {"groups": ["Claimed Agent"]}


class MockedVerifiedEmailUserReponse(BaseMockedOKRequestsResponse):
    def json(self):
        return {"groups": ["Verified Email"]}


class MockedBadRequestResponse(Response):
    def __init__(self):
        super().__init__()
        self.status_code = 503
