import json
import os
from decimal import Decimal
from datetime import datetime

from rest_framework.test import APITestCase
from django.utils.dateparse import parse_datetime
from application.models.address import Address
from application.models.application import ProductOffering
from application.models.brokerage import Brokerage
from application.models.pricing import Pricing
from application.tests import random_objects


class PricingTests(APITestCase):
    def test_get_pricing_no_brokerage(self):
        data = {
            "selling_location": {
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            },
            "buying_location": {
                "street": "123 Main Street",
                "city": "Atlanta",
                "state": "GA",
                "zip": "78701"
            },
            "min_price": 123456,
            "max_price": 654321
        }

        url = '/api/1.0.0/pricing/'

        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertAlmostEqual(float(resp.data['estimated_min_convenience_fee']), 1.4)
        self.assertAlmostEqual(float(resp.data['estimated_max_convenience_fee']), 2.9)
        self.assertAlmostEqual(float(resp.data['estimated_earnest_deposit_percentage']), 2.00)
        self.assertAlmostEqual(float(resp.data['estimated_min_rent_amount']), 28.67)
        self.assertAlmostEqual(float(resp.data['estimated_max_rent_amount']), 151.97)
        self.assertEqual(resp.data['product_offering'], "buy-sell")

    def test_buy_only_pricing(self):
        data = {
            "buying_location": {
                "street": "123 Main Street",
                "city": "Atlanta",
                "state": "GA",
                "zip": "78701"
            },
            "min_price": 123456,
            "max_price": 654321,
            "product_offering": "buy-only"
        }

        url = '/api/1.0.0/pricing/'

        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['product_offering'], "buy-only")

    def test_get_pricing_with_non_partner_company_name(self):
        data = open(os.path.join(os.path.dirname(__file__), '../static/non_partner_pricing_payload.json')).read()

        url = '/api/1.0.0/pricing/'

        resp = self.client.post(url, json.loads(data), format='json')
        self.assertEqual(resp.status_code, 201)

    def test_get_pricing_with_agent_partner_brokerage(self):
        brokerage = Brokerage.objects.create(name='Realty Austin')
        agent = random_objects.random_agent(brokerage=brokerage)

        data = {
            "selling_location": {
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            },
            "buying_location": {
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            },
            "min_price": 123456,
            "max_price": 654321,
            "agent_id": agent.id
        }

        url = '/api/1.0.0/pricing/'

        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertAlmostEqual(float(resp.data['estimated_min_convenience_fee']), 1.0)
        self.assertAlmostEqual(float(resp.data['estimated_max_convenience_fee']), 1.9)
        self.assertAlmostEqual(float(resp.data['estimated_earnest_deposit_percentage']), 2.00)
        self.assertAlmostEqual(float(resp.data['estimated_min_rent_amount']), 28.67)
        self.assertAlmostEqual(float(resp.data['estimated_max_rent_amount']), 151.97)

    def test_get_pricing_with_no_selling_location(self):
        brokerage = Brokerage.objects.create(name='Realty Austin')
        agent = random_objects.random_agent(brokerage=brokerage)

        data = {
            "buying_location": {
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            },
            "min_price": 123456,
            "max_price": 654321,
            "agent_id": agent.id,
            "agent_situation": "I have a client ready to make an offer"
        }

        url = '/api/1.0.0/pricing/'

        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertAlmostEqual(float(resp.data['estimated_min_convenience_fee']), 1.0)
        self.assertAlmostEqual(float(resp.data['estimated_max_convenience_fee']), 1.9)
        self.assertAlmostEqual(float(resp.data['estimated_earnest_deposit_percentage']), 2.00)
        self.assertAlmostEqual(float(resp.data['estimated_min_rent_amount']), 28.67)
        self.assertAlmostEqual(float(resp.data['estimated_max_rent_amount']), 151.97)

        pricing = Pricing.objects.latest('created_at')
        self.assertEqual(pricing.agent_situation, "I have a client ready to make an offer")

    def test_get_pricing(self):
        pricing = random_objects.random_pricing()

        url = f'/api/1.0.0/pricing/{pricing.id}/'
        resp = self.client.get(url, format='json')

        self.assertEqual(resp.status_code, 200)
        self.assertAlmostEqual(float(resp.data['estimated_min_convenience_fee']),
                               pricing.estimated_min_convenience_fee)
        self.assertAlmostEqual(float(resp.data['estimated_max_convenience_fee']),
                               pricing.estimated_max_convenience_fee)
        self.assertAlmostEqual(float(resp.data['estimated_earnest_deposit_percentage']),
                               pricing.estimated_earnest_deposit_percentage)
        self.assertAlmostEqual(float(resp.data['estimated_min_rent_amount']), pricing.estimated_min_rent_amount)
        self.assertAlmostEqual(float(resp.data['estimated_max_rent_amount']), pricing.estimated_max_rent_amount,
                               places=2)
        self.assertEqual(parse_datetime(resp.data['updated_at']), pricing.updated_at)
        self.assertEqual(resp.data['questionnaire_response_id'], str(pricing.questionnaire_response_id))

    def test_get_buy_only_pricing(self):
        pricing = random_objects.random_pricing(product_offering=ProductOffering.BUY_ONLY)

        url = f'/api/1.0.0/pricing/{pricing.id}/'
        resp = self.client.get(url, format='json')

        self.assertEqual(resp.status_code, 200)
        self.assertAlmostEqual(float(resp.data['estimated_min_convenience_fee']),
                               pricing.estimated_min_convenience_fee)
        self.assertAlmostEqual(float(resp.data['estimated_max_convenience_fee']),
                               pricing.estimated_max_convenience_fee)
        self.assertAlmostEqual(float(resp.data['estimated_earnest_deposit_percentage']),
                               pricing.estimated_earnest_deposit_percentage)
        self.assertEqual(float(resp.data['estimated_min_rent_amount']), pricing.estimated_min_rent_amount)
        self.assertEqual(float(resp.data['estimated_max_rent_amount']), pricing.estimated_max_rent_amount)
        self.assertEqual(resp.data['product_offering'], ProductOffering.BUY_ONLY)
    
    def test_get_pricing_with_application(self):
        application = random_objects.random_application()
        pricing = random_objects.random_pricing(application=application)
        
        url = f'/api/1.0.0/pricing/{pricing.id}/'
        resp = self.client.get(url, format='json')
        
        self.assertEqual(resp.data['customer_email'], application.customer.email)
        self.assertEqual(resp.data['created_at'].split('T')[0], pricing.created_at.strftime("%Y-%m-%d"))
        self.assertEqual(resp.data['shared_on_date'], pricing.shared_on_date)
    
    def test_get_pricing_without_application(self):
        pricing = random_objects.random_pricing()
        
        url = f'/api/1.0.0/pricing/{pricing.id}/'
        resp = self.client.get(url, format='json')
        
        self.assertEqual(resp.data['customer_email'], None)
        

    def test_put_pricing(self):
        pricing = random_objects.random_pricing()

        url = f'/api/1.0.0/pricing/{pricing.id}/'

        data = {
            "agent_remarks": "blah blah blah",
            "buying_location": {
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            },
            "min_price": 123456,
            "max_price": 876543
        }

        resp = self.client.put(url, data, format='json')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['agent_remarks'], "blah blah blah")

    def test_should_update_existing_pricing(self):
        brokerage = Brokerage.objects.create(name='Realty Austin')
        agent = random_objects.random_agent(brokerage=brokerage)
        data = {
            "buying_location": {
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            },
            "min_price": 123456,
            "max_price": 654321,
            "agent_id": agent.id,
            "agent_situation": "I have a client ready to make an offer"
        }

        url = '/api/1.0.0/pricing/'

        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertAlmostEqual(float(resp.data['estimated_min_convenience_fee']), 1.0)
        self.assertAlmostEqual(float(resp.data['estimated_max_convenience_fee']), 1.9)
        self.assertAlmostEqual(float(resp.data['estimated_earnest_deposit_percentage']), 2.00)
        self.assertAlmostEqual(float(resp.data['estimated_min_rent_amount']), 28.67)
        self.assertAlmostEqual(float(resp.data['estimated_max_rent_amount']), 151.97)

        data = {
            "buying_location": {
                "street": "123 Main Street",
                "city": "Atlanta",
                "state": "GA",
                "zip": "30301"
            },
            "min_price": 10321,
            "max_price": 200000
        }

        url = f'/api/1.0.0/pricing/{resp.data["id"]}/'
        resp = self.client.put(url, data, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertAlmostEqual(float(resp.data['estimated_min_convenience_fee']), 1.9)
        self.assertAlmostEqual(float(resp.data['estimated_max_convenience_fee']), 2.9)
        self.assertAlmostEqual(float(resp.data['estimated_earnest_deposit_percentage']), 2.00)
        self.assertAlmostEqual(float(resp.data['estimated_min_rent_amount']), 2.4)
        self.assertAlmostEqual(float(resp.data['estimated_max_rent_amount']), 46.45)

    def test_post_pricing_with_actions(self):
        pricing = random_objects.random_pricing()

        url = f'/api/1.0.0/pricing/{pricing.id}/actions/'

        data = {
            "actions": ["saved"]
        }

        resp = self.client.post(url, data, format='json')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['actions'], ["saved"])

        data = {
            "actions": ["shared"]
        }

        resp = self.client.post(url, data, format='json')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['actions'], ["saved", "shared"])
    
    def test_should_set_shared_on_date_when_pricing_shared(self):
        pricing = random_objects.random_pricing()

        url = f'/api/1.0.0/pricing/{pricing.id}/actions/'
        
        data = {
            "actions": ["shared"]
        }

        resp = self.client.post(url, data, format='json')
    
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['actions'], ["shared"])
        self.assertEqual(resp.data['shared_on_date'].split("T")[0], datetime.today().strftime("%Y-%m-%d"))
        
    def test_should_not_set_shared_on_date_when_pricing_saved(self):
        pricing = random_objects.random_pricing()

        url = f'/api/1.0.0/pricing/{pricing.id}/actions/'
        data = {
            "actions": ["saved"]
        }

        resp = self.client.post(url, data, format='json')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['actions'], ["saved"])
        self.assertEqual(resp.data['shared_on_date'], None)

    def test_should_preserve_application_on_update(self):
        application = random_objects.random_application()
        pricing = random_objects.random_pricing(application=application)

        url = f'/api/1.0.0/pricing/{str(pricing.id)}/'
        brokerage = Brokerage.objects.create(name='Realty Austin')
        agent = random_objects.random_agent(brokerage=brokerage)
        data = {
            "agent_remarks": "blah blah blah",
            "id": "13123123",
            "estimated_min_convenience_fee": 0.0,
            "estimated_max_convenience_fee": 0.1,
            "estimated_earnest_deposit_percentage": 0,
            "buying_location": {
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            },
            "agent_id": agent.id,
            "min_price": 123456,
            "max_price": 654321
        }

        resp = self.client.put(url, data, format='json')
        pricing_updated = Pricing.objects.get(pk=pricing.id)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(pricing_updated.agent_remarks, "blah blah blah")
        self.assertEqual(pricing_updated.application, application)

    def test_cant_update_all_fields(self):
        brokerage = Brokerage.objects.create(name='Realty Austin')
        agent = random_objects.random_agent(brokerage=brokerage)
        data = {
            "buying_location": {
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            },
            "min_price": 123456,
            "max_price": 654321,
            "agent_id": agent.id,
            "agent_situation": "I have a client ready to make an offer"
        }
        url = '/api/1.0.0/pricing/'
        initial_resp = self.client.post(url, data, format='json')

        url = f'/api/1.0.0/pricing/{initial_resp.data["id"]}/'

        data = {
            "agent_remarks": "blah blah blah",
            "estimated_min_convenience_fee": 0.0,
            "estimated_max_convenience_fee": 0.1,
            "estimated_earnest_deposit_percentage": 0,
            "buying_location": {
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            },
            "agent_id": agent.id,
            "min_price": 123456,
            "max_price": 654321
        }

        resp = self.client.put(url, data, format='json')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['agent_remarks'], "blah blah blah")
        self.assertAlmostEqual(Decimal(resp.data['estimated_min_convenience_fee']),
                               Decimal(initial_resp.data['estimated_min_convenience_fee']))
        self.assertAlmostEqual(Decimal(resp.data['estimated_max_convenience_fee']),
                               Decimal(initial_resp.data['estimated_max_convenience_fee']))
        self.assertAlmostEqual(Decimal(resp.data['estimated_earnest_deposit_percentage']),
                               Decimal(initial_resp.data['estimated_earnest_deposit_percentage']))
        self.assertAlmostEqual(Decimal(resp.data['estimated_min_rent_amount']),
                               Decimal(initial_resp.data['estimated_min_rent_amount']))
        self.assertAlmostEqual(Decimal(resp.data['estimated_max_rent_amount']),
                               Decimal(initial_resp.data['estimated_max_rent_amount']), places=2)

    def test_8z_pricing(self):
        colorado_address = Address.objects.create(street=random_objects.fake.street_address(),
                                                  city=random_objects.fake.city(),
                                                  state='CO', zip=random_objects.fake.zipcode())

        pricing = Pricing.objects.create(buying_location=colorado_address,
                                         selling_location=colorado_address,
                                         min_price=123456, max_price=654321, agents_company='8z')

        self.assertAlmostEqual(pricing.estimated_min_convenience_fee, 1.9)

    def test_emd_calculations(self):
        tier_one = Pricing.objects.create(buying_location=random_objects.random_address(),
                                          selling_location=random_objects.random_address(),
                                          min_price=0, max_price=999999)
        tier_two = Pricing.objects.create(buying_location=random_objects.random_address(),
                                          selling_location=random_objects.random_address(),
                                          min_price=0, max_price=1499999)

        self.assertAlmostEqual(tier_one.estimated_earnest_deposit_percentage, 2.0)
        self.assertAlmostEqual(tier_two.estimated_earnest_deposit_percentage, 4.0)


    def test_utm(self):
        # POST test
        data = {
            "selling_location": {
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            },
            "buying_location": {
                "street": "123 Main Street",
                "city": "Atlanta",
                "state": "GA",
                "zip": "78701"
            },
            "min_price": 123456,
            "max_price": 654321,
            "utm": {
                "utm_content": "buffer1234",
                "utm_medium": "social",
                "utm_source": "facebook.com",
                "utm_campaign": "quote"
            }
        }

        url = '/api/1.0.0/pricing/'

        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, 201)

        response_utm_expected = {'utm_campaign': 'quote',
                                 'utm_content': 'buffer1234',
                                 'utm_medium': 'social',
                                 'utm_source': 'facebook.com'}
        self.assertEqual(resp.data['utm'], response_utm_expected)

        # PUT Test - current behavior allows utm and other fields to be overwritten/updated.
        data = {
            "selling_location": {
                "street": "123 Main Street",
                "city": "Austin",
                "state": "TX",
                "zip": "78701"
            },
            "buying_location": {
                "street": "123 Main Street",
                "city": "Atlanta",
                "state": "GA",
                "zip": "78701"
            },
            "min_price": 123456,
            "max_price": 654321,
            "utm": {
                "updated": "true"
            }
        }

        url = '/api/1.0.0/pricing/'+resp.data["id"]+'/'

        resp = self.client.put(url, data, format='json')
        self.assertEqual(resp.status_code, 200)

        response_utm_update_expected = {'updated': 'true'}
        self.assertEqual(resp.data['utm'], response_utm_update_expected)
