import os
from pathlib import Path

from application.application_acknowledgements import create_service_agreement
from application.tasks import add_acknowledgements

from rest_framework.test import APITestCase
from parameterized import parameterized

from application.models.acknowledgement import Acknowledgement
from application.models.address import Address
from application.models.application import Application, ApplicationStage, ProductOffering
from application.models.current_home import CurrentHome
from application.models.customer import Customer
from application.models.disclosure import Disclosure, DisclosureType
from application.models.brokerage import Brokerage
from application.models.real_estate_agent import RealEstateAgent
from application.tests import random_objects


E_CONSENT = 'homeward e-consent'
TITLE_TEXAS = 'homeward title (texas)'
SERVICE_AGREEMENT_TX = 'service agreement (texas)'
SERVICE_AGREEMENT_TX_BUY_ONLY = "service agreement (texas - buy only)"
NEW_SERVICE_AGREEMENT_TX = "service agreement (tx - buy-sell) v4"
MORTGAGE_TEXAS = 'homeward mortgage (texas)'
MORTGAGE_COLORADO = 'homeward mortgage (colorado)'
SERVICE_AGREEMENT_CO = 'service agreement (colorado)'
SERVICE_AGREEMENT_TX_RA = 'service agreement (texas realty austin)'
SERVICE_AGREEMENT_GA = 'service agreement (georgia)'
NEW_RA_SERVICE_AGREEMENT = 'service agreement (tx realty austin - buy-sell) v4'

def setup():
    Disclosure.objects.all().delete()


class ApplicationAcknowledgementsTests(APITestCase):
    module_dir = str(Path(__file__).parent)
    fixtures = [os.path.join(module_dir, "../static/disclosure.json")]

    @parameterized.expand([
        ('adds when buying in texas', "TX", "WA", "Not Realty Austin",
         [E_CONSENT, TITLE_TEXAS, SERVICE_AGREEMENT_TX, MORTGAGE_TEXAS], False),
        ('adds when offer on property in tx', "TX", "WA", "Not Realty Austin",
         [E_CONSENT, TITLE_TEXAS, SERVICE_AGREEMENT_TX, MORTGAGE_TEXAS], True),
        ('adds when selling in texas', "WA", "TX", "Not Realty Austin", [E_CONSENT, TITLE_TEXAS], False),
        ('adds when selling + buying in texas', "TX", "TX", "Not Realty Austin",
         [E_CONSENT, TITLE_TEXAS, SERVICE_AGREEMENT_TX, MORTGAGE_TEXAS], False),

        ('adds co when buying in co', "CO", "WA", "Not Realty Austin",
         [E_CONSENT, MORTGAGE_COLORADO, SERVICE_AGREEMENT_CO], False),
        ('adds 2 when buying in co and selling in tx', "CO", "TX", "Not Realty Austin",
         [E_CONSENT, TITLE_TEXAS, MORTGAGE_COLORADO, SERVICE_AGREEMENT_CO], False),
        ('does not add when selling in colorado', "WA", "CO", "Not Realty Austin", [E_CONSENT], False),
        ('only texas when selling in co buying in texas', "TX", "CO", "Not Realty Austin",
         [E_CONSENT, TITLE_TEXAS, SERVICE_AGREEMENT_TX, MORTGAGE_TEXAS], False),

        ('does not add when not buying or selling in texas', "WA", "CA", "Not Realty Austin", [E_CONSENT], False),
        ('only buy', "TX", None, "Not Realty Austin",
         [E_CONSENT, TITLE_TEXAS, SERVICE_AGREEMENT_TX, MORTGAGE_TEXAS], False),
        ('only list', None, "tx", "Not Realty Austin", [E_CONSENT, TITLE_TEXAS], False),
        ('no buy no list', None, None, "Not Realty Austin", [E_CONSENT], False),

        ('assigns RA tx service agreement', "TX", "TX", "Realty Austin",
         [E_CONSENT, TITLE_TEXAS, SERVICE_AGREEMENT_TX_RA, MORTGAGE_TEXAS], False),
        ('assigns RA tx service agreement when brokerage is None', "TX", "TX", None,
         [E_CONSENT, TITLE_TEXAS, SERVICE_AGREEMENT_TX, MORTGAGE_TEXAS], False),
        ('does not assign RA tx service agreement buying other states', "GA", "TX", "Realty Austin",
         [E_CONSENT, TITLE_TEXAS, SERVICE_AGREEMENT_GA], False)
    ])
    def test_add_acknowledgements(self, name, buying_state, selling_state, buying_agent_brokerage,
                                  expected_document_names, use_existing_property):
        buying_location = None
        current_home = None
        if buying_state:
            buying_location = Address.objects.create(street='101 Test St.', city='some city', state=buying_state,
                                                     zip='01010')

        if selling_state:
            selling_location = Address.objects.create(street='101 Test St.', city='some city', state=selling_state,
                                                      zip='01010')
            current_home = CurrentHome.objects.create(address=selling_location)

        brokerage = Brokerage.objects.create(name=buying_agent_brokerage) if buying_agent_brokerage else None

        buying_agent = RealEstateAgent.objects.create(brokerage=brokerage)

        user_email = 'disclosure_user@gmail.com'

        customer = Customer.objects.create(name='Test User', email=user_email)

        if use_existing_property:
            application = Application.objects.create(current_home=current_home, offer_property_address=buying_location,
                                                     customer=customer, listing_agent=None, buying_agent=buying_agent,
                                                     product_offering=ProductOffering.BUY_SELL)
        else:
            application = Application.objects.create(current_home=current_home, home_buying_location=buying_location,
                                                     customer=customer, listing_agent=None, buying_agent=buying_agent,
                                                     product_offering=ProductOffering.BUY_SELL)

        add_acknowledgements(application)

        acknowledgements = Acknowledgement.objects.filter(application=application)

        num_docs = len(expected_document_names)

        self.assertEqual(acknowledgements.count(), num_docs)

        if num_docs > 0:
            for name in expected_document_names:
                self.assertTrue(acknowledgements.filter(disclosure__name=name).exists())

    @parameterized.expand([
        ('service agreement disabled', MORTGAGE_TEXAS),
        ('mortgage disabled', SERVICE_AGREEMENT_TX),
        ('title disabled', TITLE_TEXAS)
    ])
    def test_inactive_disclosures(self, name, disclosure_name):
        disclosure = Disclosure.objects.get(name=disclosure_name)
        disclosure.active = False
        disclosure.save()

        buying_location = Address.objects.create(street='101 Test St.', city='some city', state="TX", zip='01010')

        selling_location = Address.objects.create(street='101 Test St.', city='some city', state="TX", zip='01010')
        current_home = CurrentHome.objects.create(address=selling_location)

        customer = Customer.objects.create(email='someemail@homeward.com')
        application = Application.objects.create(current_home=current_home, offer_property_address=buying_location,
                                                 customer=customer)

        add_acknowledgements(application)
        acknowledgements = Acknowledgement.objects.filter(application=application)
        self.assertFalse(acknowledgements.filter(disclosure__name=disclosure_name).exists())

    def test_product_offering_specific_disclosures(self):
        app = random_objects.random_application(product_offering=ProductOffering.BUY_ONLY)
        create_service_agreement(app, 'tx')

        self.assertIsNotNone(Acknowledgement.objects.get(application=app,
                                                         disclosure__name=SERVICE_AGREEMENT_TX_BUY_ONLY))

    def test_new_service_agreement_field_is_set_when_acknowledged(self):
        new_disclosure = Disclosure.objects.get(name=NEW_SERVICE_AGREEMENT_TX)
        old_disclosure = Disclosure.objects.get(name=SERVICE_AGREEMENT_TX)

        buying_location = Address.objects.create(street='101 Test St.', city='some city', state="TX", zip='01010')

        selling_location = Address.objects.create(street='101 Test St.', city='some city', state="TX", zip='01010')
        current_home = CurrentHome.objects.create(address=selling_location)

        customer = Customer.objects.create(email='someemail@homeward.com')
        application = Application.objects.create(current_home=current_home, offer_property_address=buying_location,
                                                 customer=customer)

        application.product_offering = 'buy-sell'
        application.save()

        add_acknowledgements(application)
        acknowledgements = Acknowledgement.objects.filter(application=application)

        self.assertFalse(acknowledgements.filter(disclosure=new_disclosure).exists())
        self.assertTrue(acknowledgements.filter(disclosure=old_disclosure).exists())
        self.assertIsNone(application.new_service_agreement_acknowledged_date)

        old_disclosure.active = False
        old_disclosure.save()
        new_disclosure.active = True
        new_disclosure.save()

        add_acknowledgements(application)
        acknowledgements = Acknowledgement.objects.filter(application=application)

        self.assertTrue(acknowledgements.filter(disclosure=new_disclosure).exists())
        self.assertIsNone(application.new_service_agreement_acknowledged_date)

        service_agreement_acknowledgement = acknowledgements.get(disclosure=new_disclosure)
        service_agreement_acknowledgement.is_acknowledged = True
        service_agreement_acknowledgement.save()

        self.assertIsNotNone(application.new_service_agreement_acknowledged_date)

    def test_new_service_agreement_signal_when_app_stage_changes(self):
        new_disclosure = Disclosure.objects.get(name=NEW_SERVICE_AGREEMENT_TX)
        old_disclosure = Disclosure.objects.get(name=SERVICE_AGREEMENT_TX)

        buying_location = Address.objects.create(street='101 Test St.', city='some city', state="TX", zip='01010')
        application = random_objects.random_application(stage=ApplicationStage.OPTION_PERIOD,
                                                        product_offering=ProductOffering.BUY_SELL,
                                                        offer_property_address=buying_location)
        application.save()

        acknowledgements = Acknowledgement.objects.filter(application=application)

        self.assertFalse(acknowledgements.filter(disclosure=new_disclosure).exists())

        old_disclosure.active = False
        old_disclosure.save()
        new_disclosure.active = True
        new_disclosure.save()

        application.stage = ApplicationStage.INCOMPLETE
        application.save()

        acknowledgements = Acknowledgement.objects.filter(application=application)

        self.assertTrue(acknowledgements.filter(disclosure=new_disclosure).exists())

    def test_ensure_only_one_service_agreement_added_for_ra(self): 
        old_ra_disclosure = Disclosure.objects.get(name=SERVICE_AGREEMENT_TX_RA)
        old_disclosure = Disclosure.objects.get(name=SERVICE_AGREEMENT_TX)
            
        buying_location = Address.objects.create(street='101 Test St.', city='some city', state="TX", zip='01010')

        application = random_objects.random_application(stage=ApplicationStage.OPTION_PERIOD,
                                                        product_offering=ProductOffering.BUY_SELL,
                                                        offer_property_address=buying_location)                                               

        application.save()
        add_acknowledgements(application)
    
        acknowledgements = Acknowledgement.objects.filter(application=application)
        self.assertTrue(acknowledgements.filter(disclosure=old_disclosure).exists())
        self.assertFalse(acknowledgements.filter(disclosure=old_ra_disclosure).exists())

        agent = random_objects.random_agent()
        brokerage = Brokerage.objects.create(name='Realty Austin')
        agent.brokerage = brokerage
        agent.save()
        application.buying_agent = agent  
        application.save()
        add_acknowledgements(application)

        acknowledgements = Acknowledgement.objects.filter(application=application)
        self.assertTrue(acknowledgements.filter(disclosure=old_ra_disclosure).exists())
        self.assertTrue(acknowledgements.filter(disclosure=old_disclosure).exists())