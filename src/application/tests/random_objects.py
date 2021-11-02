import uuid
from decimal import Decimal

from faker import Faker

from application.models.address import Address
from application.models.application import Application, ProductOffering
from application.models.brokerage import Brokerage
from application.models.current_home import CurrentHome
from application.models.customer import Customer
from application.models.floor_price import FloorPrice, FloorPriceType
from application.models.new_home_purchase import NewHomePurchase
from application.models.preapproval import PreApproval
from application.models.pricing import Pricing
from application.models.real_estate_agent import RealEstateAgent
from application.models.rent import Rent
from application.models.internal_support_user import InternalSupportUser
from application.models.real_estate_lead import RealEstateLead
from application.models.application import HomeBuyingStage
from application.models.offer import Offer
from application.models.loan import Loan
from blend.models import Followup


fake = Faker()


def random_customer(**kwargs) -> Customer:
    customer_email = kwargs.pop('customer_email', None)
    email = customer_email if customer_email else fake.email()
    return Customer.objects.create(name=fake.name(), email=email, phone=fake.phone_number(), **kwargs)


def random_agent(**kwargs) -> RealEstateAgent:
    agent_email = kwargs.pop('agent_email', None)
    email = agent_email if agent_email else fake.email()
    return RealEstateAgent.objects.create(name=fake.name(), email=email, phone=fake.phone_number(),
                                          company=fake.company(), **kwargs)


def random_real_estate_lead(**kwargs) -> RealEstateLead:
    return RealEstateLead.objects.create(customer=random_customer(**kwargs), address=random_address(), needs_buying_agent=False,
                                         needs_listing_agent=False, home_buying_stage=HomeBuyingStage.VIEWING_LISTINGS)


def random_application(**kwargs) -> Application:
    customer_email = kwargs.pop('customer_email', None)
    listing_agent_email = kwargs.pop('listing_agent_email', None)
    buying_agent_email = kwargs.pop('buying_agent_email', None)
    return Application.objects.create(customer=random_customer(customer_email=customer_email),
                                      listing_agent=random_agent(agent_email=listing_agent_email),
                                      buying_agent=random_agent(agent_email=buying_agent_email),
                                      **kwargs)


def random_preapproval(**kwargs) -> PreApproval:
    return PreApproval.objects.create(amount=fake.pydecimal(right_digits=2, positive=True),
                                      estimated_down_payment=fake.pydecimal(right_digits=2, positive=True),
                                      vpal_approval_date=fake.date_this_month(),
                                      **kwargs)


def random_new_home_purchase(**kwargs) -> NewHomePurchase:
    return NewHomePurchase.objects.create(rent=random_rent(),
                                          option_period_end_date=fake.date_this_month(after_today=True),
                                          homeward_purchase_close_date=fake.date_this_month(after_today=True),
                                          homeward_purchase_status='Offer Won',
                                          contract_price=fake.pydecimal(right_digits=2, positive=True),
                                          earnest_deposit_percentage=fake.pydecimal(left_digits=1, right_digits=2,
                                                                                    positive=True),
                                          address=random_address(), **kwargs)


def random_rent() -> Rent:
    return Rent.objects.create(type='Deferred',
                               amount_months_one_and_two=fake.pydecimal(right_digits=2, positive=True,
                                                                        max_value=9999),
                               daily_rental_rate=fake.pydecimal(right_digits=2, positive=True,
                                                                max_value=9999))


def random_current_home(**kwargs) -> CurrentHome:
    return CurrentHome.objects.create(address=random_address(), **kwargs)


def random_address() -> Address:
    return Address.objects.create(street=fake.street_address(), city=fake.city(), state=fake.state_abbr(),
                                  zip=fake.zipcode())


def random_floor_price() -> FloorPrice:
    return FloorPrice.objects.create(type=FloorPriceType.REQUIRED,
                                     preliminary_amount=fake.pydecimal(right_digits=2, positive=True,
                                                                       max_value=9999999),
                                     amount=fake.pydecimal(right_digits=2, positive=True, max_value=9999999))


def random_brokerage(**kwargs) -> Brokerage:
    return Brokerage.objects.create(name=fake.company(), **kwargs)


def random_pricing(**kwargs) -> Pricing:
    min_price = fake.random_int(min=200000, max=3000000)
    max_price = fake.random_int(min=min_price, max=3000000)

    min_rent = fake.pydecimal(right_digits=2, positive=True, max_value=9999)
    max_rent = min_rent * Decimal(1.5)
    return Pricing.objects.create(buying_location=random_address(), selling_location=random_address(),
                                  min_price=min_price, max_price=max_price,
                                  estimated_min_convenience_fee=fake.pydecimal(left_digits=1, right_digits=2,
                                                                               positive=True),
                                  estimated_max_convenience_fee=fake.pydecimal(left_digits=1, right_digits=2,
                                                                               positive=True),
                                  estimated_earnest_deposit_percentage=fake.pydecimal(left_digits=1, right_digits=2,
                                                                                      positive=True),
                                  estimated_min_rent_amount=min_rent,
                                  estimated_max_rent_amount=max_rent,
                                  agent_remarks=fake.pystr(max_chars=500),
                                  questionnaire_response_id=uuid.uuid4(),
                                  **kwargs)


def random_internal_support_user(**kwargs) -> InternalSupportUser:
    return InternalSupportUser.objects.create(email=fake.email(),
                                              first_name=fake.first_name(),
                                              last_name=fake.last_name(),
                                              **kwargs)


def random_offer(**kwargs) -> Offer:
    return Offer.objects.create(property_type='Single Family',
                                contract_type='Resale',
                                other_offers='No',
                                plan_to_lease_back_to_seller='No',
                                less_than_one_acre=True,
                                waive_appraisal=True,
                                already_under_contract=True,
                                offer_price='500000',
                                offer_property_address=random_address(),
                                **kwargs)


def random_loan(**kwargs) -> Loan:
    return Loan.objects.create(status='Approved',
                                **kwargs)

def random_followup(**kwargs) -> Followup:
    return Followup.objects.create(requested_date=fake.date_time(),
                                    **kwargs)
