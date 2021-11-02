import uuid
import pytz
from datetime import datetime, timedelta
from unittest.mock import ANY, Mock, patch

from django.conf import settings
from django.utils import timezone
from requests import Session
from rest_framework.test import APITestCase, APIClient

from api.v1_0_0.tests._utils import data_generators
from api.v1_0_0.tests.integration.mixins import AuthMixin

from application import constants
from application.email_trigger_tasks import (
    send_agent_pre_customer_close_email, send_expiring_approval_email,
    send_incomplete_agent_referral_reminders,
    send_incomplete_application_reminders, send_pre_customer_close_email,
    send_pre_homeward_close_email, send_registered_client_notification,
    send_vpal_ready_for_review_follow_up)
from application.models.application import (APEX_PARTNER_SITE,
                                            FAST_TRACK_REGISTRATION,
                                            REAL_ESTATE_AGENT,
                                            REGISTERED_CLIENT, Application,
                                            ApplicationStage, LeadStatus,
                                            MortgageStatus, ProductOffering)
from application.models.acknowledgement import Acknowledgement
from application.models.customer import Customer
from application.models.disclosure import Disclosure
from application.models.models import StageHistory
from application.models.notification_status import NotificationStatus
from application.models.offer import Offer, OfferStatus
from application.models.preapproval import PreApproval
from application.models.real_estate_agent import RealEstateAgent
from application.models.stakeholder import Stakeholder
from application.models.stakeholder_type import StakeholderType
from application.models.task import Task
from application.models.task_name import TaskName
from application.models.task_progress import TaskProgress
from application.models.task_status import TaskStatus
from application.tests import random_objects
from application.tests.random_objects import fake
from user.models import User
from utils.hubspot import Notification


class EmailTriggerTests(AuthMixin, APITestCase):
    mock_success_response = Mock()
    mock_success_response.status_code = 200

    server_error_response = Mock()
    server_error_response.status_code = 503

    @patch("utils.hubspot.send_application_under_review")
    def test_should_send_application_under_review_email(self, email_patch):
        email_patch.return_value = self.mock_success_response

        application = random_objects.random_application()

        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()

        # Should send email with no loan advisor data when no LA exists on app
        email_patch.assert_called_once_with(ANY, ANY, ANY, [application.get_buying_agent_email()], None, None, None, None)
        self.assertEquals(NotificationStatus.objects.filter(application=application).count(), 1)
        email_patch.reset_mock()

        application.stage = ApplicationStage.INCOMPLETE
        application.save()

        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()

        self.assertEquals(StageHistory.objects.filter(application=application).count(), 3)
        email_patch.assert_not_called()

        # reset application
        NotificationStatus.objects.filter(application=application).delete()
        StageHistory.objects.filter(application=application).delete()
        email_patch.reset_mock()

        # Should send with loan advisor data and co-borrower in cc'd emails when data present on app
        application.stage = ApplicationStage.INCOMPLETE
        application.save()
        application.customer.co_borrower_email = "co-borrower@homeward.com"
        application.customer.save()
        application.loan_advisor = random_objects.random_internal_support_user(sf_id='some-la-sf-id')
        # Should not cc cx_manager
        application.cx_manager = random_objects.random_internal_support_user(sf_id='some-cx-sf-id')
        application.save()
        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()
        email_patch.assert_called_once_with(ANY, ANY, str(application.id),
                                            [application.get_buying_agent_email(), "co-borrower@homeward.com"],
                                            application.loan_advisor.first_name,
                                            application.loan_advisor.last_name,
                                            application.loan_advisor.schedule_a_call_url, application.loan_advisor.phone)

    @patch("utils.hubspot.send_application_under_review")
    def test_should_send_application_under_review_email_when_no_agent_on_app(self, email_patch):
        email_patch.return_value = self.mock_success_response
        customer = random_objects.random_customer()
        application = Application.objects.create(customer=customer)

        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()

        email_patch.assert_called_once()

    @patch("utils.hubspot.send_non_hw_mortgage_candidate_approval")
    @patch("utils.hubspot.send_agent_instructions")
    def test_should_add_not_sent_notification_on_approval_with_missing_data(self, agent_instructions_email_patch,
                                                                            approval_email_patch):
        # should insert not sent notification when homeward owner
        approval_email_patch.return_value = self.mock_success_response
        agent_instructions_email_patch.return_value = self.mock_success_response

        approval_notification = Notification.objects.get(name=Notification.APPROVAL)
        application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                        product_offering=ProductOffering.BUY_ONLY,
                                                        hw_mortgage_candidate="Not Determined")

        application.stage = ApplicationStage.APPROVED
        application.save()

        self.assertEquals(NotificationStatus.objects.filter(application=application, status=NotificationStatus.NOT_SENT,
                                                            reason="Missing homeward_owner_email").count(), 1)
        approval_email_patch.assert_not_called()

        # reset notification
        application.stage = ApplicationStage.INCOMPLETE
        application.product_offering=ProductOffering.BUY_SELL
        application.save()

        # should insert not sent when address is missing
        application.stage=ApplicationStage.APPROVED
        application.homeward_owner_email = "test@homeward.com"
        application.save()

        approval_email_patch.assert_not_called()
        self.assertEquals(NotificationStatus.objects.filter(application=application, status=NotificationStatus.NOT_SENT,
                                                            reason="Missing homeward_owner_email").count(), 1)
        self.assertEquals(NotificationStatus.objects.filter(application=application, status=NotificationStatus.NOT_SENT,
                                                            reason="Missing street_address value").count(), 1)

        # reset notification, add home
        application.stage = ApplicationStage.INCOMPLETE
        application.current_home = random_objects.random_current_home()
        application.save()

        # Should still send approval email when not sent statues are in notification status table
        application.stage = ApplicationStage.APPROVED
        application.save()
        self.assertEquals(NotificationStatus.objects.filter(application=application, status=NotificationStatus.NOT_SENT,
                                                            reason="Missing homeward_owner_email").count(), 1)
        self.assertEquals(NotificationStatus.objects.filter(application=application, status=NotificationStatus.NOT_SENT,
                                                            reason="Missing street_address value").count(), 1)
        self.assertEquals(NotificationStatus.objects.filter(application=application, notification=approval_notification,
                                                            status=NotificationStatus.SENT).count(), 1)

    @patch("utils.hubspot.send_non_hw_mortgage_candidate_approval")
    @patch("utils.hubspot.send_agent_instructions")
    def test_should_send_default_values_for_approval_email_when_no_preapproval(self, agent_instructions_email_patch,
                                                                               approval_email_patch):
        # should send "Under Review" as default values when preapproval is missing
        approval_email_patch.return_value = self.mock_success_response
        agent_instructions_email_patch.return_value = self.mock_success_response

        application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                        product_offering=ProductOffering.BUY_ONLY,
                                                        homeward_owner_email='test@homward.com',
                                                        hw_mortgage_candidate='Not Determined')

        application.stage = ApplicationStage.APPROVED
        application.save()

        approval_email_patch.assert_called_once_with(ANY, ANY, "Under Review", "Under Review", "Not Applicable",
                                                     [application.get_buying_agent_email()], ANY, None, None, None,
                                                     None, None)
        agent_instructions_email_patch.assert_called_once_with(ANY, ANY, ANY, ANY, [], ANY, None, None, None)

        self.assertEquals(NotificationStatus.objects.filter(application=application).count(), 2)

        # reset notification

        NotificationStatus.objects.filter(application=application).delete()
        approval_email_patch.reset_mock()
        agent_instructions_email_patch.reset_mock()
        application.stage = ApplicationStage.INCOMPLETE
        application.save()

        # should send 'Under Review' as default if preapproval exists but values are missing
        application.preapproval = random_objects.random_preapproval()
        application.preapproval.amount = None
        application.preapproval.estimated_down_payment = None
        application.stage = ApplicationStage.APPROVED
        application.save()

        approval_email_patch.assert_called_once_with(ANY, ANY, "Under Review", "Under Review", "Not Applicable",
                                                     [application.get_buying_agent_email()], ANY, None, None, None,
                                                     None, None)
        agent_instructions_email_patch.assert_called_once_with(ANY, ANY, ANY, str(application.id), [], ANY, None, None,
                                                               None)

    @patch("utils.hubspot.send_non_hw_mortgage_candidate_approval")
    @patch("utils.hubspot.send_agent_instructions")
    def test_should_send_approval_emails(self, agent_instructions_email_patch, approval_email_patch):
        # should not send when incomplete
        approval_email_patch.return_value = self.mock_success_response
        agent_instructions_email_patch.return_value = self.mock_success_response

        application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                        product_offering=ProductOffering.BUY_ONLY)
        application.save()
        approval_email_patch.assert_not_called()
        agent_instructions_email_patch.assert_not_called()


        application.preapproval = random_objects.random_preapproval()
        application.homeward_owner_email = 'yeehaw@homeward.com'
        application.hw_mortgage_candidate = 'Not Determined'
        application.save()

        application.stage = ApplicationStage.APPROVED

        application.save()
        approval_email_patch.assert_called_once_with(ANY, ANY, f"${round(application.preapproval.amount):,}",
                                                     f"${round(application.preapproval.estimated_down_payment):,}",
                                                     "Not Applicable", [application.get_buying_agent_email()], ANY,
                                                     None, None, None, None, None)

        agent_instructions_email_patch.assert_called_once_with(ANY, ANY, ANY, ANY, [], ANY, None, None, None)

        self.assertEquals(NotificationStatus.objects.filter(application=application).count(), 2)


        # reset notificatoin
        NotificationStatus.objects.filter(application=application).delete()
        approval_email_patch.reset_mock()
        agent_instructions_email_patch.reset_mock()

        # should not send on qualified
        application.current_home = random_objects.random_current_home()
        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()
        approval_email_patch.assert_not_called()

        # should send when mortgage status not pre-qualified or approved
        application.mortgage_status = MortgageStatus.VPAL_STARTED
        application.stage = ApplicationStage.APPROVED
        application.save()
        approval_email_patch.called_once()
        agent_instructions_email_patch.called_once()
        self.assertEquals(NotificationStatus.objects.filter(application=application).count(), 2)

        # reset notification
        NotificationStatus.objects.filter(application=application).delete()
        approval_email_patch.reset_mock()
        agent_instructions_email_patch.reset_mock()

        # should not send agent instructions when no agent present
        application.buying_agent = None
        application.save()
        approval_email_patch.called_once()
        agent_instructions_email_patch.assert_not_called()

        # reset notification
        NotificationStatus.objects.filter(application=application).delete()

        # Ensure email is sent with cx_email as from_email and co borrower email, and works as expected as buy_sell app
        application.product_offering = ProductOffering.BUY_SELL
        application.mortgage_status = MortgageStatus.PREQUALIFIED
        application.stage = ApplicationStage.INCOMPLETE
        application.cx_manager = random_objects.random_internal_support_user()
        application.buying_agent = random_objects.random_agent()
        application.save()
        application.customer.co_borrower_email = "co-borrower@homeward.com"
        application.customer.save()
        approval_email_patch.reset_mock()
        application.stage = ApplicationStage.APPROVED
        application.save()
        approval_email_patch.assert_called_once_with(ANY, ANY, ANY, ANY, application.current_home.address.street,
                                                     [application.get_buying_agent_email(),
                                                      "co-borrower@homeward.com", application.cx_manager.email],
                                                     application.homeward_owner_email,
                                                     application.cx_manager.first_name, application.cx_manager.last_name,
                                                     application.cx_manager.schedule_a_call_url,
                                                     application.cx_manager.email, None)
        agent_instructions_email_patch.assert_called_once_with(ANY, ANY, ANY, str(application.id),
                                                               [application.cx_manager.email],
                                                               application.homeward_owner_email,
                                                               application.cx_manager.first_name,
                                                               application.cx_manager.last_name,
                                                               application.cx_manager.schedule_a_call_url)

    @patch("utils.hubspot.send_hw_mortgage_candidate_approval")
    def test_should_not_send_notification_on_hwm_candidate_on_approval_with_missing_data(self, hw_mortgage_candidate_approval_patch):
        # should insert not send notification when homeward owner
        hw_mortgage_candidate_approval_patch.return_value = self.mock_success_response
        approval_notification = Notification.objects.get(name=Notification.HW_MORTGAGE_CANDIDATE_APPROVAL)
        loan_advisor = random_objects.random_internal_support_user()
        application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                        product_offering=ProductOffering.BUY_ONLY,
                                                        hw_mortgage_candidate="Yes",
                                                        loan_advisor=loan_advisor)

        application.stage = ApplicationStage.APPROVED
        application.save()

        self.assertEquals(NotificationStatus.objects.filter(application=application, status=NotificationStatus.NOT_SENT,
                                                            reason="Missing homeward_owner_email").count(), 1)
        hw_mortgage_candidate_approval_patch.assert_not_called()

        # reset notification
        application.stage = ApplicationStage.INCOMPLETE
        application.product_offering=ProductOffering.BUY_SELL
        application.save()

        # should insert not sent when address is missing
        application.stage=ApplicationStage.APPROVED
        application.homeward_owner_email = "test@homeward.com"
        application.save()

        hw_mortgage_candidate_approval_patch.assert_not_called()

        self.assertEquals(NotificationStatus.objects.filter(application=application, status=NotificationStatus.NOT_SENT,
                                                            reason="Missing homeward_owner_email").count(), 1)
        self.assertEquals(NotificationStatus.objects.filter(application=application, status=NotificationStatus.NOT_SENT,
                                                            reason="Missing street_address value").count(), 1)

        # reset notification, add home
        application.stage = ApplicationStage.INCOMPLETE
        application.current_home = random_objects.random_current_home()
        application.save()

        # Should still send approval email when not sent statues are in notification status table
        application.stage = ApplicationStage.APPROVED
        application.save()
        self.assertEquals(NotificationStatus.objects.filter(application=application, status=NotificationStatus.NOT_SENT,
                                                            reason="Missing homeward_owner_email").count(), 1)
        self.assertEquals(NotificationStatus.objects.filter(application=application, status=NotificationStatus.NOT_SENT,
                                                            reason="Missing street_address value").count(), 1)
        self.assertEquals(NotificationStatus.objects.filter(application=application, notification=approval_notification,
                                                            status=NotificationStatus.SENT).count(), 1)

    @patch("utils.hubspot.send_hw_mortgage_candidate_approval")
    def test_should_not_send_notification_on_hwm_candidate_on_approval_when_no_preapproval(self, hw_mortgage_candidate_approval_patch):
        hw_mortgage_candidate_approval_patch.return_value = self.mock_success_response
        loan_advisor = random_objects.random_internal_support_user()

        application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                    product_offering=ProductOffering.BUY_ONLY,
                                                    homeward_owner_email='test@homward.com',
                                                    hw_mortgage_candidate='Yes',
                                                    loan_advisor=loan_advisor)

        application.stage = ApplicationStage.APPROVED
        application.save()

        hw_mortgage_candidate_approval_patch.assert_called_once_with(ANY, ANY, ANY, "Under Review", "Under Review", "Not Applicable",
                                                    [application.get_buying_agent_email(), loan_advisor.email], loan_advisor.first_name, loan_advisor.last_name, loan_advisor.phone, loan_advisor.email, loan_advisor.schedule_a_call_url)
        self.assertEquals(NotificationStatus.objects.filter(application=application).count(), 1)

        # reset notificatoin
        NotificationStatus.objects.filter(application=application).delete()
        hw_mortgage_candidate_approval_patch.reset_mock()
        application.stage = ApplicationStage.INCOMPLETE
        application.save()

        # should send 'Under Review' as default if preapproval exists but values are missing
        application.preapproval = random_objects.random_preapproval()
        application.preapproval.amount = None
        application.preapproval.estimated_down_payment = None
        application.stage = ApplicationStage.APPROVED
        application.save()

        hw_mortgage_candidate_approval_patch.assert_called_once_with(ANY, ANY, ANY, "Under Review", "Under Review", "Not Applicable",
                                                    [application.get_buying_agent_email(), loan_advisor.email], loan_advisor.first_name, loan_advisor.last_name, loan_advisor.phone, loan_advisor.email, loan_advisor.schedule_a_call_url)

    @patch("utils.hubspot.send_hw_mortgage_candidate_approval")
    def test_should_send_hw_mortgage_candidate_approval_emails(self, hw_mortgage_candidate_approval_patch):

        hw_mortgage_candidate_approval_patch.return_value = self.mock_success_response
        # if application has a loan advisor
        loan_advisor = random_objects.random_internal_support_user()
        application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                        product_offering=ProductOffering.BUY_ONLY,
                                                        loan_advisor=loan_advisor)
        application.save()

        hw_mortgage_candidate_approval_patch.assert_not_called()

        application.preapproval = random_objects.random_preapproval()
        application.homeward_owner_email = 'yeehaw@homeward.com'
        application.hw_mortgage_candidate = 'Yes'
        application.save()

        application.stage = ApplicationStage.APPROVED
        application.save()

        hw_mortgage_candidate_approval_patch.assert_called_once_with(ANY, ANY, ANY,
                                                                     f"${round(application.preapproval.amount):,}",
                                                                     f"${round(application.preapproval.estimated_down_payment):,}",
                                                                     "Not Applicable",
                                                                     [application.get_buying_agent_email(),
                                                                      loan_advisor.email],
                                                                     loan_advisor.first_name,
                                                                     loan_advisor.last_name, loan_advisor.phone,
                                                                     loan_advisor.email,
                                                                     loan_advisor.schedule_a_call_url)

        self.assertEquals(NotificationStatus.objects.filter(application=application).count(), 1)
        # reset notification
        NotificationStatus.objects.filter(application=application).delete()
        hw_mortgage_candidate_approval_patch.reset_mock()
        # if application does not have a loan advisor
        app_without_loan_advisor = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                                     product_offering=ProductOffering.BUY_ONLY,
                                                                     hw_mortgage_candidate='Yes')
        app_without_loan_advisor.save()
        hw_mortgage_candidate_approval_patch.assert_not_called()

        app_without_loan_advisor.preapproval = random_objects.random_preapproval()
        app_without_loan_advisor.homeward_owner_email = 'yohellowhatup@homeward.com'
        app_without_loan_advisor.save()

        app_without_loan_advisor.stage = ApplicationStage.APPROVED
        # reset notification
        NotificationStatus.objects.filter(application=app_without_loan_advisor).delete()
        app_without_loan_advisor.save()

        hw_mortgage_candidate_approval_patch.assert_called_once_with(ANY, ANY, ANY,
                                                                     f"${round(app_without_loan_advisor.preapproval.amount):,}",
                                                                     f"${round(app_without_loan_advisor.preapproval.estimated_down_payment):,}",
                                                                     "Not Applicable",
                                                                     [app_without_loan_advisor.get_buying_agent_email()],
                                                                     constants.DEFAULT_LOAN_ADVISOR_FIRST_NAME,
                                                                     constants.DEFAULT_LOAN_ADVISOR_LAST_NAME,
                                                                     constants.DEFAULT_LOAN_ADVISOR_PHONE,
                                                                     constants.DEFAULT_LOAN_ADVISOR_EMAIL,
                                                                     constants.DEFAULT_LOAN_ADVISOR_CALL_URL)

        # reset notification
        NotificationStatus.objects.filter(application=application).delete()
        hw_mortgage_candidate_approval_patch.reset_mock()

        # should not send on qualified
        application.current_home = random_objects.random_current_home()
        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()
        hw_mortgage_candidate_approval_patch.assert_not_called()

        # should send when mortgage status not pre-qualified or approved
        application.mortgage_status = MortgageStatus.VPAL_STARTED
        application.stage = ApplicationStage.APPROVED
        application.save()
        hw_mortgage_candidate_approval_patch.called_once()
        self.assertEquals(NotificationStatus.objects.filter(application=application).count(), 1)

    @patch('application.models.offer.Offer.attempt_push_to_salesforce')
    @patch("utils.hubspot.send_unacknowledged_service_agreement_email")
    @patch("user.models.requests.get")
    def test_should_send_unacknowledged_service_agreement_email(self, user_patch, email_patch, sf_patch):
        Notification.objects.create(name='offer requested unacknowledged service agreement', type='email', is_active=True)
        user_patch.return_value = data_generators.MockedAgentUserResponse()
        email_patch.return_value = self.mock_success_response
        sf_patch.return_value = self.mock_success_response

        user = self.create_user("fake_agent_user1")
        token = self.login_user(user)[1]
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        agent = RealEstateAgent.objects.create(
            **data_generators.get_fake_real_estate_agent("agent", email=user.email))
        customer = random_objects.random_customer()
        application = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION)
        application.buying_agent = agent
        application.customer = customer
        application.save()

        client = APIClient()
        url = '/api/1.0.0/offer/'

        request_data = {
            'year_built': 2012,
            'home_square_footage': 1300,
            'property_type': 'Single Family',
            'less_than_one_acre': True,
            'home_list_price': 500000,
            "offer_price": 510000,
            "contract_type": "Resale",
            "other_offers": "1-4",
            "offer_deadline": timezone.now(),
            "plan_to_lease_back_to_seller": "No",
            "waive_appraisal": "Yes",
            "already_under_contract": True,
            "comments": "test comments",
            "application_id": application.id,
            "status": OfferStatus.REQUESTED,
            "offer_property_address": {
                "street": "2222 Test St.",
                "city": "Austin",
                "state": "TX",
                "zip": 78704
            }
        }

        response = client.post(url, request_data, **headers, format='json')

        email_patch.assert_called_once_with(application.customer)
        email_patch.reset_mock()

        json_response = response.json()
        offer = Offer.objects.get(id=json_response['id'])
        offer.status = OfferStatus.INCOMPLETE
        offer.save()

        email_patch.assert_not_called()

        offer.status = OfferStatus.REQUESTED
        offer.save()

        email_patch.assert_called_once_with(application.customer)

    @patch('application.models.offer.Offer.attempt_push_to_salesforce')
    @patch("utils.hubspot.send_unacknowledged_service_agreement_email")
    def test_should_not_send_unacknowledged_service_agreement_email(self, email_patch, sf_patch):
        Notification.objects.create(name='offer requested unacknowledged service agreement', type='email',
                                    is_active=True)

        email_patch.return_value = self.mock_success_response
        sf_patch.return_value = self.mock_success_response

        application = random_objects.random_application(stage=ApplicationStage.APPROVED,
                                                        new_home_purchase=random_objects.random_new_home_purchase(),
                                                        current_home=random_objects.random_current_home(
                                                            floor_price=random_objects.random_floor_price()))

        disclosure_one = Disclosure.objects.create(name=constants.SERVICE_AGREEMENT_TX,
                                                   document_url="http://www.google.com", active=True)
        acknowledgement = Acknowledgement.objects.create(application=application, disclosure=disclosure_one)
        acknowledgement.acknowledged_at = datetime.now(pytz.utc)
        acknowledgement.save()

        offer = random_objects.random_offer(status='Complete', application_id=application.id)
        offer.status = OfferStatus.REQUESTED
        offer.save()

        email_patch.assert_not_called()

    @patch("utils.hubspot.send_offer_submitted")
    @patch("application.models.offer.Offer.attempt_push_to_salesforce")
    def test_should_send_offer_submitted_email(self, sf_patch, email_patch):
        email_patch.return_value = self.mock_success_response
        application = random_objects.random_application(stage=ApplicationStage.APPROVED,
                                                        new_home_purchase=random_objects.random_new_home_purchase(),
                                                        current_home=random_objects.random_current_home(
                                                            floor_price=random_objects.random_floor_price()))

        application.stage = ApplicationStage.OFFER_SUBMITTED
        application.save()

        email_patch.assert_not_called()

        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()

        offer = random_objects.random_offer(application=application, status='Complete')
        offer.already_under_contract = False
        offer.waive_appraisal = 'Yes'
        offer.save()

        offer.status = 'Requested'
        offer.save()

        email_patch.assert_called_once_with(application.customer, offer, ANY, [], None)
        email_patch.reset_mock()

        application.min_price = 1111111
        application.save()
        email_patch.assert_not_called()

        # reset application
        NotificationStatus.objects.filter(application=application).delete()

        offer.status = 'Incomplete'
        offer.save()
        application.stage = ApplicationStage.INCOMPLETE
        application.cx_manager = random_objects.random_internal_support_user()
        application.save()
        application.customer.co_borrower_email = "co-borrower@homeward.com"
        application.customer.save()
        application.homeward_owner_email = 'homeward@homeward.com'
        application.save()
        email_patch.reset_mock()
        offer.status = 'Requested'
        offer.save()

        # Ensure email is sent with cx_email as from_email
        email_patch.assert_called_once_with(application.customer, offer, ANY, ["co-borrower@homeward.com"],
                                            "homeward@homeward.com")

    @patch("utils.hubspot.send_offer_submitted_agent")
    @patch("application.models.offer.Offer.attempt_push_to_salesforce")
    def test_should_send_offer_submitted_agent_email(self, salesforce_patch, agent_email_patch):
        agent_email_patch.return_value = self.mock_success_response
        salesforce_patch.return_value = self.mock_success_response

        application = random_objects.random_application(stage=ApplicationStage.APPROVED,
                                                        new_home_purchase=random_objects.random_new_home_purchase(),
                                                        current_home=random_objects.random_current_home(
                                                            floor_price=random_objects.random_floor_price()))

        application.cx_manager = random_objects.random_internal_support_user()
        application.save()
        offer = random_objects.random_offer(status='Complete', application_id=application.id)
        offer.waive_appraisal = 'Yes'
        offer.already_under_contract = False
        offer.save()

        offer.status = OfferStatus.APPROVED
        offer.save()

        agent_email_patch.assert_called_once_with(offer.application.get_buying_agent_email(), ANY,
                                                  offer.offer_property_address.street, ANY, ANY,
                                                  offer.application.homeward_owner_email, ANY)
        agent_email_patch.reset_mock()

        offer.status = OfferStatus.CANCELLED
        offer.save()

        agent_email_patch.assert_not_called()

        offer.status = OfferStatus.APPROVED
        offer.save()

        agent_email_patch.assert_called_once()

    @patch("utils.hubspot.send_offer_submitted")
    def test_should_suppress_offer_submitted_if_takeover(self, email_patch):
        email_patch.return_value = self.mock_success_response
        # Setup application with takeover purchase
        application = random_objects.random_application(stage=ApplicationStage.APPROVED,
                                                        new_home_purchase=
                                                        random_objects.random_new_home_purchase(),
                                                        current_home=random_objects.random_current_home(
                                                            floor_price=random_objects.random_floor_price()))

        offer = random_objects.random_offer(application=application)
        offer.status = 'Requested'
        offer.already_under_contract = True
        offer.save()
        # Should not attempt to send email
        email_patch.assert_not_called()
        offer_submitted_notification = Notification.objects.get(name=Notification.OFFER_SUBMITTED)
        offer_submitted_notification_status = NotificationStatus.objects.get(application=application,
                                                                             notification=offer_submitted_notification)

        # Should instead save a SUPPRESSED status on this application's OFFER_SUBMITTED notification
        self.assertEqual(offer_submitted_notification_status.status, NotificationStatus.SUPPRESSED)
        self.assertEqual(offer_submitted_notification_status.reason, "Offer is takeover")

    @patch("utils.hubspot.send_offer_accepted")
    def test_should_send_offer_accepted_email(self, email_patch):
        email_patch.return_value = self.mock_success_response
        application = random_objects.random_application(stage=ApplicationStage.APPROVED,
                                                        new_home_purchase=random_objects.random_new_home_purchase(),
                                                        current_home=random_objects.random_current_home(
                                                            floor_price=random_objects.random_floor_price()))
        tc_email = "someemail@homeward.com"
        Stakeholder.objects.create(application=application, email=tc_email,
                                   type=StakeholderType.TRANSACTION_COORDINATOR)

        application.stage = ApplicationStage.OPTION_PERIOD
        application.save()

        email_patch.assert_called_once_with(ANY, ANY, ANY, ANY, [application.get_buying_agent_email(), tc_email],
                                            ANY)
        email_patch.reset_mock()

        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()

        email_patch.assert_not_called()

        application.stage = ApplicationStage.OPTION_PERIOD
        application.save()

        email_patch.assert_called_once()
        email_patch.reset_mock()

        application.min_price = 1111111
        application.save()
        email_patch.assert_not_called()

        # reset application
        NotificationStatus.objects.filter(application=application).delete()

        application.stage = ApplicationStage.INCOMPLETE
        application.cx_manager = random_objects.random_internal_support_user()
        application.save()
        application.customer.co_borrower_email = "co-borrower@homeward.com"
        application.customer.save()
        email_patch.reset_mock()
        application.stage = ApplicationStage.OPTION_PERIOD
        application.save()
        # Ensure email is sent with cx_email as from_email
        email_patch.assert_called_once_with(ANY, ANY, ANY, ANY, [application.get_buying_agent_email(),
                                                                 "co-borrower@homeward.com",
                                                                 application.cx_manager.email,
                                                                 tc_email],
                                            application.homeward_owner_email)


    @patch("utils.hubspot.send_purchase_price_updated")
    def test_should_send_purchase_price_update_email(self, email_patch):
        email_patch.return_value = self.mock_success_response
        Notification.objects.create(name=Notification.PURCHASE_PRICE_UPDATED,
                                    type='email', template_id='301001001', is_active=True)
        application = random_objects.random_application(stage=ApplicationStage.APPROVED,
                                                        new_home_purchase=random_objects.random_new_home_purchase(),
                                                        preapproval=random_objects.random_preapproval(),
                                                        current_home=random_objects.random_current_home(
                                                            floor_price=random_objects.random_floor_price()))

        application.cx_manager = random_objects.random_internal_support_user(sf_id="some-sf-id-a")
        application.save()

        application.preapproval.amount = application.preapproval.amount + 1
        application.preapproval.save()

        email_patch.assert_called_once_with(application.customer, int(application.preapproval.amount),
                                            [application.get_buying_agent_email(),
                                             application.cx_manager.email],
                                            application.cx_manager.first_name,
                                            application.cx_manager.last_name,
                                            application.cx_manager.email,
                                            application.cx_manager.schedule_a_call_url)
        email_patch.reset_mock()

        application.preapproval.amount = application.preapproval.amount - 100
        application.preapproval.save()
        application.save()

        email_patch.assert_not_called()

        email_patch.reset_mock()

        application.preapproval.amount = 0
        application.preapproval.save()

        email_patch.assert_not_called()

        email_patch.reset_mock()

        application.loan_advisor = random_objects.random_internal_support_user(sf_id="some-sf-id-b")
        application.hw_mortgage_candidate = 'Yes'
        application.save()

        application.preapproval.amount = application.preapproval.amount + 270000
        application.preapproval.save()

        email_patch.assert_called_once_with(application.customer, int(application.preapproval.amount),
                                            [application.get_buying_agent_email(),
                                             application.cx_manager.email,
                                             application.loan_advisor.email],
                                            application.loan_advisor.first_name,
                                            application.loan_advisor.last_name,
                                            application.loan_advisor.email,
                                            application.loan_advisor.schedule_a_call_url)

    @patch("utils.hubspot.send_pre_homeward_close")
    def test_should_send_pre_homeward_close_email(self, email_patch):
        email_patch.return_value = self.mock_success_response
        pre_homeward_close_notification = Notification.objects.get(name=Notification.PRE_HOMEWARD_CLOSE)
        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(),
                                                        stage=ApplicationStage.OPTION_PERIOD)
        tc_email = "some-tc-email@homeward.com"
        Stakeholder.objects.create(application=application, email=tc_email, type=StakeholderType.TRANSACTION_COORDINATOR)
        application.new_home_purchase.homeward_purchase_close_date = datetime.today() + timedelta(days=6)
        application.new_home_purchase.save()

        send_pre_homeward_close_email()
        email_patch.assert_not_called()

        application.new_home_purchase.homeward_purchase_close_date = datetime.today() + timedelta(days=4)
        application.new_home_purchase.rent= None
        application.new_home_purchase.save()

        send_pre_homeward_close_email()
        email_patch.assert_not_called()
        NotificationStatus.objects.get(application=application,
                                       notification=pre_homeward_close_notification,
                                       status=NotificationStatus.NOT_SENT)

        application.new_home_purchase.rent = random_objects.random_rent()
        application.new_home_purchase.save()

        send_pre_homeward_close_email()
        email_patch.assert_called_once_with(ANY, ANY, [application.get_buying_agent_email(), tc_email], ANY)
        email_patch.reset_mock()

        # email should not be sent if notification exists
        send_pre_homeward_close_email()
        email_patch.assert_not_called()

        # reset application
        NotificationStatus.objects.filter(application=application).delete()
        # Ensure email is sent with cx_email as from_email and co_borrower when populated
        application.cx_manager = random_objects.random_internal_support_user()
        application.save()
        application.customer.co_borrower_email = "co_borrower_test@homeward.com"
        application.customer.save()
        send_pre_homeward_close_email()

        email_patch.assert_called_once_with(ANY, ANY, [application.get_buying_agent_email(),
                                                       "co_borrower_test@homeward.com", application.cx_manager.email, tc_email],
                                            application.homeward_owner_email)

    @patch("utils.hubspot.send_pre_homeward_close")
    def test_should_suppress_pre_homeward_close_when_reassigned(self, email_patch):
        email_patch.return_value = self.mock_success_response
        # Should instead save a SUPPRESSED status on this application's Pre homeward close notification
        pre_homeward_close_notification = Notification.objects.get(name=Notification.PRE_HOMEWARD_CLOSE)
        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(is_reassigned_contract=True),
                                                        stage=ApplicationStage.OPTION_PERIOD)
        application.new_home_purchase.homeward_purchase_close_date = datetime.today() + timedelta(days=4)
        application.new_home_purchase.save()

        send_pre_homeward_close_email()
        email_patch.assert_not_called()
        pre_homeward_close_notification_status = NotificationStatus.objects.get(application=application,
                                                                                notification=pre_homeward_close_notification,
                                                                                status=NotificationStatus.SUPPRESSED)
        self.assertEqual(pre_homeward_close_notification_status.reason, "Application is reassigned contract")

        # Should reattempt a send when reassigned bool switches
        application.new_home_purchase.is_reassigned_contract = False
        application.new_home_purchase.save()
        send_pre_homeward_close_email()
        email_patch.assert_called_once()

    @patch("utils.hubspot.send_pre_homeward_close")
    @patch("utils.hubspot.send_agent_pre_customer_close")
    def test_should_send_agent_pre_customer_close_email(self, agent_email_patch, email_patch):
        agent_email_patch.return_value = self.mock_success_response
        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(),
                                                        stage=ApplicationStage.HOMEWARD_PURCHASE)
        tc_email = "some-tc-email@homeward.com"
        Stakeholder.objects.create(application=application, email=tc_email, type=StakeholderType.TRANSACTION_COORDINATOR)
        application.new_home_purchase.customer_purchase_close_date = datetime.today() + timedelta(days=8)
        application.new_home_purchase.save()

        application.cx_manager = random_objects.random_internal_support_user()
        application.save()

        send_agent_pre_customer_close_email()
        agent_email_patch.assert_not_called()

        application.new_home_purchase.customer_purchase_close_date = datetime.today() + timedelta(days=6)
        application.new_home_purchase.save()

        send_agent_pre_customer_close_email()
        agent_email_patch.assert_called_once_with(ANY, ANY, ANY, ANY, ANY, ANY, tc_email)

        agent_email_patch.reset_mock()
        send_agent_pre_customer_close_email()
        agent_email_patch.assert_not_called()

        NotificationStatus.objects.filter(application=application).delete()
        application.buying_agent = None
        application.save()
        send_agent_pre_customer_close_email()
        agent_email_patch.assert_not_called()

    @patch("utils.hubspot.send_agent_pre_customer_close")
    def test_should_suppress_agent_pre_customer_close_when_reassigned(self, email_patch):
        email_patch.return_value = self.mock_success_response
        pre_customer_close_agent_notification = Notification.objects.get(name=Notification.AGENT_PRE_CUSTOMER_CLOSE)

        # Should instead save a SUPPRESSED status on this application's Pre homeward close notification
        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(is_reassigned_contract=True),
                                                        stage=ApplicationStage.HOMEWARD_PURCHASE)
        application.new_home_purchase.customer_purchase_close_date = datetime.today() + timedelta(days=4)
        application.new_home_purchase.save()

        application.cx_manager = random_objects.random_internal_support_user()
        application.save()

        send_agent_pre_customer_close_email()
        email_patch.assert_not_called()
        pre_customer_close_agent_notification_status = NotificationStatus.objects.get(application=application,
                                                                                      notification=pre_customer_close_agent_notification,
                                                                                      status=NotificationStatus.SUPPRESSED)
        self.assertEqual(pre_customer_close_agent_notification_status.reason, "Application is reassigned contract")

        # Should reattempt a send when reassigned bool switches
        application.new_home_purchase.is_reassigned_contract = False
        application.new_home_purchase.save()
        send_agent_pre_customer_close_email()
        email_patch.assert_called_once()

    @patch("utils.hubspot.send_pre_customer_close")
    @patch("utils.hubspot.send_agent_pre_customer_close")
    def test_should_send_pre_customer_close_email(self, agent_email_patch, email_patch):
        email_patch.return_value = self.mock_success_response
        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(),
                                                        stage=ApplicationStage.HOMEWARD_PURCHASE)
        tc_email = "some-tc-email@homeward.com"
        Stakeholder.objects.create(application=application, email=tc_email, type=StakeholderType.TRANSACTION_COORDINATOR)
        application.new_home_purchase.customer_purchase_close_date = datetime.today() + timedelta(days=8)
        application.new_home_purchase.save()

        application.cx_manager = random_objects.random_internal_support_user()
        application.save()

        send_pre_customer_close_email()

        email_patch.assert_not_called()

        application.new_home_purchase.customer_purchase_close_date = datetime.today() + timedelta(days=6)
        application.new_home_purchase.save()

        send_pre_customer_close_email()
        email_patch.assert_called_once_with(ANY, ANY, [application.get_buying_agent_email(),
                                                       application.cx_manager.email, tc_email], ANY, ANY)
        email_patch.reset_mock()

        send_pre_customer_close_email()
        email_patch.assert_not_called()
        # reset application
        NotificationStatus.objects.filter(application=application).delete()

        application.customer.co_borrower_email = "co-borrower@homeard.com"
        application.customer.save()

        send_pre_customer_close_email()
        # Ensure email is sent with cx_email as from_email
        email_patch.assert_called_once_with(ANY, ANY, [application.get_buying_agent_email(), "co-borrower@homeard.com",
                                                       application.cx_manager.email, tc_email],
                                            application.cx_manager,
                                            application.homeward_owner_email)

    @patch("utils.hubspot.send_pre_customer_close")
    def test_should_send_pre_customer_close_with_existing_sent_notifications(self, customer_email_patch):
        customer_email_patch.return_value = self.mock_success_response

        pre_homeward_close_notification = Notification.objects.get(name=Notification.PRE_HOMEWARD_CLOSE)
        pre_customer_close_notification = Notification.objects.get(name=Notification.PRE_CUSTOMER_CLOSE)

        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(),
                                                        stage=ApplicationStage.HOMEWARD_PURCHASE)
        application.new_home_purchase.customer_purchase_close_date = datetime.today() + timedelta(days=4)
        application.new_home_purchase.is_reassigned_contract = False
        application.new_home_purchase.save()

        application.cx_manager = random_objects.random_internal_support_user()
        application.save()

        # insert existing SENT notificationstatus
        existing_homeward_close_notification_status = NotificationStatus.objects.create(application=application,
                                                                                        notification=pre_homeward_close_notification,
                                                                                        status=NotificationStatus.SENT)

        # ensure existing SENT notifications don't keep new ones from being created in the periodic_task emails
        send_pre_customer_close_email()
        pre_customer_statues = NotificationStatus.objects.filter(application=application,
                                                                 notification=pre_customer_close_notification,
                                                                 status=NotificationStatus.SENT)
        self.assertEqual(pre_customer_statues.count(), 1)


    @patch("utils.hubspot.send_agent_pre_customer_close")
    def test_should_send_agent_pre_customer_close_with_existing_sent_notifications(self, agent_email_patch):
        agent_email_patch.return_value = self.mock_success_response
        pre_customer_close_notification = Notification.objects.get(name=Notification.PRE_CUSTOMER_CLOSE)
        pre_customer_close_agent_notification = Notification.objects.get(name=Notification.AGENT_PRE_CUSTOMER_CLOSE)

        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(),
                                                        stage=ApplicationStage.HOMEWARD_PURCHASE)
        application.new_home_purchase.customer_purchase_close_date = datetime.today() + timedelta(days=6)
        application.new_home_purchase.is_reassigned_contract = False
        application.new_home_purchase.save()

        application.cx_manager = random_objects.random_internal_support_user()
        application.save()

        # insert existing SENT notificationstatus
        existing_homeward_close_notification_status = NotificationStatus.objects.create(application=application,
                                                                                        notification=pre_customer_close_notification,
                                                                                        status=NotificationStatus.SENT)

        send_agent_pre_customer_close_email()
        pre_customer_agent_statues = NotificationStatus.objects.filter(application=application,
                                                                       notification=pre_customer_close_agent_notification,
                                                                       status=NotificationStatus.SENT)
        self.assertEqual(pre_customer_agent_statues.count(), 1)

    @patch("utils.hubspot.send_pre_homeward_close")
    def test_should_send_pre_homeward_close_with_existing_sent_notifications(self, homeward_close_patch):
        homeward_close_patch.return_value = self.mock_success_response

        pre_customer_close_agent_notification = Notification.objects.get(name=Notification.AGENT_PRE_CUSTOMER_CLOSE)
        pre_homeward_close_notification = Notification.objects.get(name=Notification.PRE_HOMEWARD_CLOSE)

        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(),
                                                        stage=ApplicationStage.OPTION_PERIOD)
        application.new_home_purchase.homeward_purchase_close_date = datetime.today() + timedelta(days=4)
        application.new_home_purchase.is_reassigned_contract = False
        application.new_home_purchase.save()

        # insert existing SENT notificationstatus
        existing_homeward_close_notification_status = NotificationStatus.objects.create(application=application,
                                                                                        notification=pre_customer_close_agent_notification,
                                                                                        status=NotificationStatus.SENT)

        send_pre_homeward_close_email()
        pre_homeward_statues = NotificationStatus.objects.filter(application=application,
                                                                 notification=pre_homeward_close_notification,
                                                                 status=NotificationStatus.SENT)
        self.assertEqual(pre_homeward_statues.count(), 1)

    @patch("utils.hubspot.send_pre_customer_close")
    def test_should_suppress_pre_customer_close_when_reassigned(self, email_patch):
        email_patch.return_value = self.mock_success_response
        # Should instead save a SUPPRESSED status on this application's Pre homeward close notification
        pre_customer_close_notification = Notification.objects.get(name=Notification.PRE_CUSTOMER_CLOSE)
        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(),
                                                        stage=ApplicationStage.HOMEWARD_PURCHASE)
        application.new_home_purchase.customer_purchase_close_date = datetime.today() + timedelta(days=4)
        application.new_home_purchase.is_reassigned_contract = True
        application.new_home_purchase.save()

        application.cx_manager = random_objects.random_internal_support_user()
        application.save()

        send_pre_customer_close_email()
        email_patch.assert_not_called()
        pre_customer_close_notification_status = NotificationStatus.objects.get(application=application,
                                                                                notification=pre_customer_close_notification,
                                                                                status=NotificationStatus.SUPPRESSED)
        self.assertEqual(pre_customer_close_notification_status.reason, "Application is reassigned contract")

        # Should reattempt a send when reassigned bool switches
        application.new_home_purchase.is_reassigned_contract = False
        application.new_home_purchase.save()
        send_pre_customer_close_email()
        email_patch.assert_called_once()

    @patch("utils.hubspot.send_expiring_approval_email")
    @patch("utils.hubspot.send_agent_instructions")
    def test_should_send_expiring_approval_email(self, agent_instructions_patch, email_patch):
        email_patch.return_value = self.mock_success_response
        application = random_objects.random_application()
        application.stage = ApplicationStage.APPROVED
        application.preapproval = PreApproval.objects.create(amount=fake.pydecimal(right_digits=2, positive=True),
                                                             estimated_down_payment=fake.pydecimal(right_digits=2,
                                                                                                   positive=True),
                                                             vpal_approval_date=datetime.today() - timedelta(days=49))
        application.save()

        send_expiring_approval_email()
        email_patch.assert_not_called()

        application.preapproval = PreApproval.objects.create(amount=fake.pydecimal(right_digits=2, positive=True),
                                                             estimated_down_payment=fake.pydecimal(right_digits=2,
                                                                                                   positive=True),
                                                             vpal_approval_date=datetime.today() - timedelta(days=51))
        application.save()

        send_expiring_approval_email()
        email_patch.assert_called_once()
        email_patch.reset_mock()

        send_expiring_approval_email()
        email_patch.assert_not_called()

    @patch("utils.hubspot.send_expiring_approval_email")
    def test_should_not_send_inactive_expiring_approval_email(self, email_patch):
        application = random_objects.random_application()
        application.stage = ApplicationStage.APPROVED

        application.preapproval = PreApproval.objects.create(amount=fake.pydecimal(right_digits=2, positive=True),
                                                             estimated_down_payment=fake.pydecimal(right_digits=2,
                                                                                                   positive=True),
                                                             vpal_approval_date=datetime.today() - timedelta(days=51))
        application.save()

        send_expiring_approval_email()
        email_patch.assert_called_once()
        email_patch.reset_mock()

        notification = Notification.objects.get(name=Notification.EXPIRING_APPROVAL)
        notification.is_active = False
        notification.save()

        send_expiring_approval_email()
        email_patch.assert_not_called()

    @patch("utils.hubspot.send_expiring_approval_email")
    @patch("utils.hubspot.send_agent_instructions")
    def test_should_send_not_send_expiring_approval_email_when_no_buying_agent(self, agent_instructions_patch,
                                                                               expiring_approval_patch):
        expiring_approval_patch.return_value = self.mock_success_response
        application = random_objects.random_application()
        application.buying_agent = None
        application.stage = ApplicationStage.APPROVED
        application.preapproval = PreApproval.objects.create(amount=fake.pydecimal(right_digits=2, positive=True),
                                                             estimated_down_payment=fake.pydecimal(right_digits=2,
                                                                                                   positive=True),
                                                             vpal_approval_date=datetime.today() - timedelta(days=51))
        application.save()

        send_expiring_approval_email()
        expiring_approval_patch.assert_not_called()

    @patch("utils.hubspot.send_customer_close")
    @patch("utils.hubspot.send_agent_customer_close")
    def test_should_send_customer_close_emails(self, agent_email_patch, email_patch):
        agent_email_patch.return_value = self.mock_success_response
        email_patch.return_value = self.mock_success_response
        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase())
        tc_email = "some-tc-email@homeward.com"
        Stakeholder.objects.create(application=application, email=tc_email, type=StakeholderType.TRANSACTION_COORDINATOR)
        application.stage = ApplicationStage.CUSTOMER_CLOSED
        application.save()
        agent_email_patch.assert_called_once_with(ANY, ANY, ANY, ANY, ANY, tc_email)
        email_patch.assert_called_once_with(ANY, ANY, ANY, [application.buying_agent.email, tc_email], ANY)
        agent_email_patch.reset_mock()
        email_patch.reset_mock()

        application.stage = ApplicationStage.HOMEWARD_PURCHASE
        application.save()

        application.stage = ApplicationStage.CUSTOMER_CLOSED
        application.save()
        agent_email_patch.assert_not_called()
        email_patch.assert_not_called()

        # reset application
        NotificationStatus.objects.filter(application=application).delete()

        application.stage = ApplicationStage.INCOMPLETE
        application.cx_manager = random_objects.random_internal_support_user()
        application.save()
        application.customer.co_borrower_email = "co-borrower@homeward.com"
        application.customer.save()
        email_patch.reset_mock()
        application.stage = ApplicationStage.CUSTOMER_CLOSED
        application.save()
        # Ensure email is sent with cx_email as from_email

        email_patch.assert_called_once_with(ANY, ANY, ANY, [application.buying_agent.email,
                                                            "co-borrower@homeward.com",
                                                            application.cx_manager.email,
                                                            tc_email],
                                            application.homeward_owner_email)

    @patch("utils.hubspot.send_customer_close")
    @patch("utils.hubspot.send_agent_customer_close")
    def test_should_suppress_customer_close_emails_when_reassigned(self, agent_email_patch, customer_email_patch):
        agent_email_patch.return_value = self.mock_success_response
        customer_email_patch.return_value = self.mock_success_response
        # Should instead save a SUPPRESSED status on this application's Pre homeward close notification
        customer_close_notification = Notification.objects.get(name=Notification.CUSTOMER_CLOSE)
        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(is_reassigned_contract=True),
                                                        current_home=random_objects.random_current_home(
                                                        market_value=123456.78,
                                                        floor_price=random_objects.random_floor_price()))
        application.stage = ApplicationStage.CUSTOMER_CLOSED
        application.save()

        agent_email_patch.assert_not_called()
        customer_email_patch.assert_not_called()
        customer_close_notification_status = NotificationStatus.objects.get(application=application, notification=customer_close_notification, status=NotificationStatus.SUPPRESSED)
        agent_customer_close_notification_status = NotificationStatus.objects.get(application=application, notification=customer_close_notification, status=NotificationStatus.SUPPRESSED)
        self.assertEqual(customer_close_notification_status.reason, "Application is reassigned contract")
        self.assertEqual(agent_customer_close_notification_status.reason, "Application is reassigned contract")

        # Should reattempt a send when reassigned bool switches
        application.new_home_purchase.is_reassigned_contract = False
        application.new_home_purchase.save()
        application.stage = ApplicationStage.INCOMPLETE
        application.save()

        application.stage = ApplicationStage.CUSTOMER_CLOSED
        application.save()
        agent_email_patch.assert_called_once()
        customer_email_patch.assert_called_once()

    @patch("utils.hubspot.send_homeward_close")
    def test_should_send_homeward_purchase_email(self, email_patch):
        email_patch.return_value = self.mock_success_response
        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(),
                                                        current_home=random_objects.random_current_home(
                                                            market_value=123456.78,
                                                            floor_price=random_objects.random_floor_price()))
        tc_email = "some-tc-email@homeward.com"
        Stakeholder.objects.create(application=application, email=tc_email, type=StakeholderType.TRANSACTION_COORDINATOR)

        application.stage = ApplicationStage.HOMEWARD_PURCHASE
        application.save()

        email_patch.assert_called_once_with(application.customer, ANY, application.homeward_owner_email)
        self.assertEquals(NotificationStatus.objects.filter(application=application).count(), 1)
        email_patch.reset_mock()

        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()

        application.stage = ApplicationStage.HOMEWARD_PURCHASE
        application.save()

        email_patch.assert_not_called()

        # reset application
        NotificationStatus.objects.filter(application=application).delete()

        application.stage = ApplicationStage.INCOMPLETE
        application.cx_manager = random_objects.random_internal_support_user()
        application.save()
        application.customer.co_borrower_email = "co-borrower@homeward.com"
        application.customer.save()
        email_patch.reset_mock()
        application.stage = ApplicationStage.HOMEWARD_PURCHASE
        application.save()
        # Ensure email is sent with cx_email as from_email

        email_patch.assert_called_once_with(application.customer, [application.get_buying_agent_email(),
                                                                 "co-borrower@homeward.com",
                                                                 application.cx_manager.email,
                                                                 tc_email], application.homeward_owner_email)


    @patch("utils.hubspot.send_homeward_close")
    def test_should_suppress_homeward_close_when_reassigned(self, email_patch):
        email_patch.return_value = self.mock_success_response
        # Should instead save a SUPPRESSED status on this application's Pre homeward close notification
        homeward_close_notification = Notification.objects.get(name=Notification.HOMEWARD_CLOSE)
        application = random_objects.random_application(new_home_purchase=random_objects.random_new_home_purchase(is_reassigned_contract=True),
                                                        current_home=random_objects.random_current_home(
                                                        market_value=123456.78,
                                                        floor_price=random_objects.random_floor_price()))
        application.stage = ApplicationStage.HOMEWARD_PURCHASE
        application.save()

        email_patch.assert_not_called()
        homeward_close_notification_status = NotificationStatus.objects.get(application=application, notification=homeward_close_notification, status=NotificationStatus.SUPPRESSED)
        self.assertEqual(homeward_close_notification_status.reason, "Application is reassigned contract")

        # Should not create more than one notification status
        application.stage = ApplicationStage.INCOMPLETE
        application.save()
        application.stage = ApplicationStage.HOMEWARD_PURCHASE
        application.save()
        email_patch.assert_not_called()
        status_queryset = NotificationStatus.objects.filter(application=application, notification=homeward_close_notification, status=NotificationStatus.SUPPRESSED)
        self.assertEqual(status_queryset.count(), 1)

        # Should reattempt a send when reassigned bool switches
        application.new_home_purchase.is_reassigned_contract = False
        application.new_home_purchase.save()
        application.stage = ApplicationStage.INCOMPLETE
        application.save()

        application.stage = ApplicationStage.HOMEWARD_PURCHASE
        application.save()
        email_patch.assert_called_once()

    # set template id to meaningful value for testing
    def populate_db_with_template_ids(self):
        notifications = Notification.objects.all()
        for notification in notifications:
            notification.template_id = notification.name
            notification.save()

    def test_should_set_reminder_task(self):
        self.populate_db_with_template_ids()
        with patch('application.email_trigger_tasks.send_completion_reminder.apply_async') as send_completion_reminder_mock:
            customer = Customer.objects.create(email="test_fakeapplicant@fakeapplicantmail.com")
            app = Application.objects.create(customer=customer, stage=ApplicationStage.INCOMPLETE)
            TaskStatus.objects.create(application=app,
                                      task_obj=Task.objects.get(name=TaskName.EXISTING_PROPERTY),
                                      status=TaskProgress.IN_PROGRESS)

            send_completion_reminder_mock.assert_not_called()

            self.create_user('fakeapplicant')
            send_completion_reminder_mock.assert_called_with(kwargs={'application_id': app.id,
                                                                     'reminder_type':
                                                                         Notification.FORTY_FIVE_MIN_REMINDER},
                                                             countdown=2700)

    @patch("utils.hubspot.send_incomplete_account_notification")
    @patch("application.signals.get_partner")
    def test_should_suppress_completion_reminder_when_apex_sulg(self, partner_patch, email_mock):
        partner_patch.return_value = {}
        customer = Customer.objects.create(email="test_fakeapplicant@fakeapplicantmail.com")
        app = Application.objects.create(customer=customer, stage=ApplicationStage.INCOMPLETE, apex_partner_slug='some-partner-slug')
        notification = Notification.objects.get(name=Notification.FORTY_FIVE_MIN_REMINDER)
        self.create_user('fakeapplicant')

        email_mock.assert_not_called()
        forty_five_min_reminder_status = NotificationStatus.objects.get(application=app,
                                                                                notification=notification,
                                                                                status=NotificationStatus.SUPPRESSED)
        self.assertEqual(forty_five_min_reminder_status.reason, "Application has apex partner slug")


    @patch("utils.hubspot.send_incomplete_account_notification")
    @patch("application.signals.get_partner")
    def test_should_suppress_one_day_pre_account_reminders_when_apex_slug_on_app(self, partner_patch, email_patch):
        email_patch.return_value = self.mock_success_response
        partner_patch.return_value = {}
        pre_account_one_day_notification = Notification.objects.get(name=Notification.PRE_ACCOUNT_ONE_DAY_REMINDER)
        application = random_objects.random_application(internal_referral=REAL_ESTATE_AGENT,
                                                        internal_referral_detail=REGISTERED_CLIENT,
                                                        questionnaire_response_id=uuid.uuid4(),
                                                        apex_partner_slug='some-apex-partner')

        application.created_at = timezone.now() - timedelta(hours=25)
        application.stage = ApplicationStage.INCOMPLETE
        application.save()
        send_incomplete_application_reminders()
        one_day_reminder_notification_status = NotificationStatus.objects.get(application=application,
                                                                 notification=pre_account_one_day_notification,
                                                                 status=NotificationStatus.SUPPRESSED)
        self.assertEqual(one_day_reminder_notification_status.reason, "Application has apex partner slug")

    @patch("utils.hubspot.send_incomplete_account_notification")
    @patch("application.signals.get_partner")
    def test_should_suppress_three_day_pre_account_reminders_when_apex_slug_on_app(self, partner_patch, email_patch):
        email_patch.return_value = self.mock_success_response
        partner_patch.return_value = {}
        pre_account_three_day_notification = Notification.objects.get(name=Notification.PRE_ACCOUNT_THREE_DAY_REMINDER)
        application = random_objects.random_application(internal_referral=REAL_ESTATE_AGENT,
                                                        internal_referral_detail=REGISTERED_CLIENT,
                                                        questionnaire_response_id=uuid.uuid4(),
                                                        apex_partner_slug='some-apex-partner')

        application.created_at = timezone.now() - timedelta(hours=80)
        application.stage = ApplicationStage.INCOMPLETE
        application.save()
        send_incomplete_application_reminders()
        three_day_reminder_notification_status = NotificationStatus.objects.get(application=application,
                                                                                notification=pre_account_three_day_notification,
                                                                                status=NotificationStatus.SUPPRESSED)
        self.assertEqual(three_day_reminder_notification_status.reason, "Application has apex partner slug")

    @patch("utils.hubspot.send_incomplete_account_notification")
    def test_should_send_correct_incomplete_reminder_notification(self, email_patch):
        self.populate_db_with_template_ids()
        email_patch.return_value = self.mock_success_response

        # should send pre account one day reminder for pre account + referred-by-agent apps
        application = random_objects.random_application(internal_referral=REAL_ESTATE_AGENT,
                                                        internal_referral_detail=REGISTERED_CLIENT,
                                                        questionnaire_response_id=uuid.uuid4())

        random_objects.random_pricing(application=application)
        TaskStatus.objects.create(application=application,
                                  task_obj=Task.objects.get(name=TaskName.EXISTING_PROPERTY),
                                  status=TaskProgress.IN_PROGRESS)

        application.created_at = timezone.now() - timedelta(hours=25)
        application.stage = ApplicationStage.INCOMPLETE
        application.save()
        send_incomplete_application_reminders()

        email_patch.assert_called_once_with(ANY, ANY, f"{settings.ONBOARDING_BASE_URL}estimates/view/"
                                                      f"{application.questionnaire_response_id}",
                                            Notification.PRE_ACCOUNT_ONE_DAY_REMINDER)

        email_patch.reset_mock()

        # Should send normal one day reminder for created incomplete accounts
        user = User.objects.create(email=application.customer.email)

        # reset mock to clear out the 45 min reminder email that is triggered by User creation
        email_patch.reset_mock()

        send_incomplete_application_reminders()

        email_patch.assert_called_once_with(ANY, ANY, f"{settings.ONBOARDING_BASE_URL}resume/"
                                                      f"{application.questionnaire_response_id}",
                                            Notification.ONE_DAY_REMINDER)

        email_patch.reset_mock()

        # should send pre account reminder for apps with no user existing for 3 days
        user.email = 'DIFFERENTEMAIL@BADEMAILS.COM'
        user.save()
        application.created_at = timezone.now() - timedelta(hours=80)
        application.save()
        send_incomplete_application_reminders()

        email_patch.assert_called_with(ANY, ANY, f"{settings.ONBOARDING_BASE_URL}estimates/view/"
                                                 f"{application.questionnaire_response_id}",
                                       Notification.PRE_ACCOUNT_THREE_DAY_REMINDER)

        email_patch.reset_mock()

        # should send normal 3 day reminder to incomplete apps
        user.email = application.customer.email
        user.save()
        send_incomplete_application_reminders()

        email_patch.assert_called_with(ANY, ANY, f"{settings.ONBOARDING_BASE_URL}resume/"
                                                 f"{application.questionnaire_response_id}",
                                       Notification.THREE_DAY_REMINDER)

        email_patch.reset_mock()

        # should send week reminder for incomplete apps existing for a week
        application.created_at = timezone.now() - timedelta(days=7)

        application.save()

        send_incomplete_application_reminders()

        email_patch.assert_called_with(ANY, ANY, f"{settings.ONBOARDING_BASE_URL}resume/"
                                                 f"{application.questionnaire_response_id}",
                                       Notification.WEEK_REMINDER)

        email_patch.reset_mock()

        # should not send any reminder if no account exists and not referred less than one day
        application.created_at = timezone.now() - timedelta(hours=22)
        application.internal_referral_detail = None
        user.email = 'DIFFERENTEMAIL@BADEMAILS.COM'
        application.save()
        send_incomplete_application_reminders()

        email_patch.assert_not_called()

        email_patch.reset_mock()

        # should not send one day reminder if one day email has already been sent
        application.created_at = timezone.now() - timedelta(hours=25)

        application.save()
        send_incomplete_application_reminders()
        email_patch.asset_not_called()

        email_patch.reset_mock()

        # should send one day reminder if no record of email being sent exists, not agent referred, no user exists
        one_day_reminder_notification = Notification.objects.get(name=Notification.ONE_DAY_REMINDER)
        NotificationStatus.objects.get(application=application, notification=one_day_reminder_notification).delete()
        send_incomplete_application_reminders()
        email_patch.assert_called_with(ANY, ANY, f"{settings.ONBOARDING_BASE_URL}resume/"
                                                 f"{application.questionnaire_response_id}",
                                       Notification.ONE_DAY_REMINDER)

    @patch("application.email_trigger_tasks.mailer")
    def test_should_trigger_cma_request(self, mailer_patch):
        mailer_patch.send_cma_request.return_value = self.mock_success_response

        # create buy only application
        application = random_objects.random_application(current_home=random_objects.random_current_home(
            market_value=123456.78,
            floor_price=random_objects.random_floor_price()), product_offering=ProductOffering.BUY_ONLY)
        cma_request_notification = Notification.objects.get(name=Notification.CMA_REQUEST)

        application.lead_status = LeadStatus.NURTURE
        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()
        # Shoud not call on buy only apps
        mailer_patch.send_cma_request.assert_not_called()

        # should send email when offering is buy_sell
        application.product_offering = ProductOffering.BUY_SELL
        application.save()
        mailer_patch.send_cma_request.assert_called_once()

        mailer_patch.reset_mock()
        NotificationStatus.objects.get(application=application, notification=cma_request_notification).delete()

        application.stage = ApplicationStage.CUSTOMER_CLOSED
        application.save()

        mailer_patch.send_cma_request.assert_not_called()
        mailer_patch.reset_mock()

        application.lead_status = LeadStatus.QUALIFIED
        application.stage = ApplicationStage.APPROVED
        application.save()
        mailer_patch.send_cma_request.assert_not_called()
        mailer_patch.reset_mock()

        agent = RealEstateAgent.objects.get(email=application.buying_agent.email)
        agent.email = ""
        agent.save()
        application.lead_status = LeadStatus.NURTURE
        application.stage = ApplicationStage.QUALIFIED_APPLICATION
        application.save()
        mailer_patch.send_cma_request.assert_not_called()

    @patch("utils.hubspot.send_incomplete_agent_referral_reminder")
    def test_should_send_incomplete_referral_email(self, email_patch):
        email_patch.return_value = self.mock_success_response

        agent = random_objects.random_agent()

        # dont send if theyre too fresh
        random_objects.random_pricing(agent=agent, created_at=timezone.now())
        send_incomplete_agent_referral_reminders()
        email_patch.assert_not_called()

        # dont send if theyre too old!
        random_objects.random_pricing(agent=agent, created_at=timezone.now() - timedelta(hours=4))
        send_incomplete_agent_referral_reminders()
        email_patch.assert_not_called()

        pricing = random_objects.random_pricing(agent=agent, created_at=timezone.now() - timedelta(hours=1))
        pricing.created_at = timezone.now() - timedelta(hours=1)
        pricing.save()
        send_incomplete_agent_referral_reminders()
        email_patch.assert_called_with(agent.email, agent.get_first_name(), pricing.get_resume_link())

    @patch("utils.hubspot.send_fast_track_resume_email")
    def test_should_send_fast_track(self, email_patch):
        email_patch.return_value = self.mock_success_response
        app = random_objects.random_application(internal_referral_detail=FAST_TRACK_REGISTRATION)
        email_patch.assert_called_with(ANY, ANY, ANY, ANY, ANY, app.build_resume_link())

    @patch("utils.hubspot.send_fast_track_resume_email")
    @patch("application.signals.get_partner")
    def test_should_suppress_fast_track_email_when_app_has_apex_slug(self, partner_patch, email_patch):
        email_patch.return_value = self.mock_success_response
        partner_patch.return_value = {}
        fast_track_notificatiton = Notification.objects.get(name=Notification.FAST_TRACK_RESUME)
        app = random_objects.random_application(internal_referral_detail=FAST_TRACK_REGISTRATION, apex_partner_slug="some-slug")
        email_patch.assert_not_called()
        fast_track_notification_status = NotificationStatus.objects.get(application=app,
                                                                           notification=fast_track_notificatiton,
                                                                           status=NotificationStatus.SUPPRESSED)
        self.assertEqual(fast_track_notification_status.reason, "Application has apex partner slug")


    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_saved_quote_cta(self, mailer_patch):
        mailer_patch.send_saved_quote_cta.return_value = self.mock_success_response

        agent = random_objects.random_agent()
        pricing = random_objects.random_pricing(agent=agent)

        pricing.actions.append("saved")
        pricing.save()

        mailer_patch.send_saved_quote_cta.assert_called_with(pricing.agent.get_first_name(), pricing.agent.email,
                                                             pricing.get_resume_link())
        mailer_patch.reset_mock()

        pricing.actions.append("shared")
        pricing.save()

        mailer_patch.send_saved_quote_cta.assert_not_called()

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_app_incomplete_email(self, mailer_patch):
        mailer_patch.send_vpal_incomplete_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED)

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_APP_INCOMPLETE
        app.save()

        mailer_patch.send_vpal_incomplete_email.assert_called_with(app.buying_agent.email,
                                                                       app.customer.get_first_name(),
                                                                       app.customer.email,
                                                                       app.customer.co_borrower_email,
                                                                       app.get_approval_specialist_email(),
                                                                       app.get_approval_specialist_first_name(),
                                                                       app.get_approval_specialist_last_name())

    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_vpal_app_incomplete_email_twice(self, mailer_patch):
        mailer_patch.send_vpal_incomplete_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED)

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_APP_INCOMPLETE
        app.save()

        mailer_patch.send_vpal_incomplete_email.assert_called_with(app.buying_agent.email,
                                                                   app.customer.get_first_name(),
                                                                   app.customer.email,
                                                                   app.customer.co_borrower_email,
                                                                   app.get_approval_specialist_email(),
                                                                   app.get_approval_specialist_first_name(),
                                                                   app.get_approval_specialist_last_name())

        mailer_patch.reset_mock()

        app.stage = ApplicationStage.INCOMPLETE
        app.mortgage_status = MortgageStatus.VPAL_STARTED
        app.save()

        mailer_patch.send_vpal_incomplete_email.assert_not_called()

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_APP_INCOMPLETE
        app.save()

        mailer_patch.send_vpal_incomplete_email.assert_not_called()

    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_vpal_app_incomplete_email_if_not_qualified(self, mailer_patch):
        mailer_patch.send_vpal_incomplete_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED)

        app.mortgage_status = MortgageStatus.VPAL_APP_INCOMPLETE
        app.save()

        mailer_patch.send_vpal_incomplete_email.assert_not_called()

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_app_incomplete_email_if_first_send_fails(self, mailer_patch):
        mailer_patch.send_vpal_incomplete_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED)

        NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=app,
                                          notification=Notification.objects.get(name=Notification.VPAL_INCOMPLETE),
                                          reason=f"hubspot returned 500")

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_APP_INCOMPLETE
        app.save()

        mailer_patch.send_vpal_incomplete_email.assert_called_with(app.buying_agent.email,
                                                                   app.customer.get_first_name(),
                                                                   app.customer.email,
                                                                   app.customer.co_borrower_email,
                                                                   app.get_approval_specialist_email(),
                                                                   app.get_approval_specialist_first_name(),
                                                                   app.get_approval_specialist_last_name())

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_app_incomplete_email_without_agent_email(self, mailer_patch):
        mailer_patch.send_vpal_incomplete_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED)
        app.buying_agent = None
        app.save()

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_APP_INCOMPLETE
        app.save()

        mailer_patch.send_vpal_incomplete_email.assert_called_with(None,
                                                                   app.customer.get_first_name(),
                                                                   app.customer.email,
                                                                   app.customer.co_borrower_email,
                                                                   app.get_approval_specialist_email(),
                                                                   app.get_approval_specialist_first_name(),
                                                                   app.get_approval_specialist_last_name())

    @patch("application.email_trigger_tasks.mailer")
    def test_should_sent_vpal_app_incomplete_email_with_approval_specialist(self, mailer_patch):
        mailer_patch.send_vpal_incomplete_email.return_value = self.mock_success_response
        approval_specialist = random_objects.random_internal_support_user()
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED,
                                                             approval_specialist=approval_specialist)

        app.save()

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_APP_INCOMPLETE
        app.save()
        mailer_patch.send_vpal_incomplete_email.assert_called_with(app.buying_agent.email,
                                                                   app.customer.get_first_name(),
                                                                   app.customer.email,
                                                                   app.customer.co_borrower_email,
                                                                   approval_specialist.email,
                                                                   approval_specialist.first_name,
                                                                   approval_specialist.last_name)


    @patch("application.email_trigger_tasks.mailer")
    def test_should_sent_vpal_app_incomplete_email_without_approval_specialist(self, mailer_patch):
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED)

        app.save()

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_APP_INCOMPLETE
        app.save()
        mailer_patch.send_vpal_incomplete_email.assert_called_with(app.buying_agent.email,
                                                                   app.customer.get_first_name(),
                                                                   app.customer.email,
                                                                   app.customer.co_borrower_email,
                                                                   "hello@homewardmortgage.com",
                                                                   "Homeward",
                                                                   "Mortgage")

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_suspended_email_no_la(self, mailer_patch):
        mailer_patch.send_vpal_suspended_email.return_value = self.mock_success_response
        cx_manager = random_objects.random_internal_support_user(sf_id="some-sf-id-a")
        approval_specialist = random_objects.random_internal_support_user(sf_id="some-sf-id-b")
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED,
                                                             cx_manager=cx_manager,
                                                             approval_specialist=approval_specialist)
        app.customer.co_borrower_email = "co-borrower@test.com"
        app.customer.save()
        app.save()

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_SUSPENDED
        app.save()

        mailer_patch.send_vpal_suspended_email.assert_called_with(app.customer.email,
                                                                  app.customer.get_first_name(),
                                                                  [app.get_buying_agent_email(), app.customer.co_borrower_email],
                                                                  app.get_approval_specialist_email(),
                                                                  app.get_approval_specialist_first_name(),
                                                                  app.get_approval_specialist_last_name())

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_suspended_email_with_la(self, mailer_patch):
        mailer_patch.send_vpal_suspended_email.return_value = self.mock_success_response
        loan_advisor = random_objects.random_internal_support_user(sf_id="some-sf-id-a")
        approval_specialist = random_objects.random_internal_support_user(sf_id="some-sf-id-b")
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED,
                                                             loan_advisor=loan_advisor,
                                                             approval_specialist=approval_specialist)
        app.customer.co_borrower_email = "co-borrower@test.com"
        app.customer.save()

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_SUSPENDED
        app.save()

        mailer_patch.send_vpal_suspended_email.assert_called_with(app.customer.email,
                                                                  app.customer.get_first_name(),
                                                                  [app.get_buying_agent_email(), app.customer.co_borrower_email],
                                                                  app.loan_advisor.first_name,
                                                                  app.loan_advisor.last_name,
                                                                  app.loan_advisor.schedule_a_call_url,
                                                                  app.loan_advisor.phone,
                                                                  app.loan_advisor.email,
                                                                  app.get_approval_specialist_email(),
                                                                  app.get_approval_specialist_first_name(),
                                                                  app.get_approval_specialist_last_name())


    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_vpal_suspended_email_if_not_qualified(self, mailer_patch):
        mailer_patch.send_vpal_suspended_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED)

        app.mortgage_status = MortgageStatus.VPAL_SUSPENDED
        app.save()

        mailer_patch.send_vpal_suspended_email.assert_not_called()

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_suspended_email_if_first_send_fails(self, mailer_patch):
        mailer_patch.send_vpal_suspended_email.return_value = self.mock_success_response
        approval_specialist = random_objects.random_internal_support_user(sf_id="some-sf-id-b")
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED,
                                                             approval_specialist=approval_specialist)

        NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=app,
                                          notification=Notification.objects.get(name=Notification.VPAL_SUSPENDED),
                                          reason=f"hubspot returned 500")

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_SUSPENDED
        app.save()

        mailer_patch.send_vpal_suspended_email.assert_called_with(app.customer.email,
                                                                  app.customer.get_first_name(),
                                                                  [app.get_buying_agent_email(), app.customer.co_borrower_email],
                                                                  app.get_approval_specialist_email(),
                                                                  app.get_approval_specialist_first_name(),
                                                                  app.get_approval_specialist_last_name())

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_suspended_email_without_agent_email(self, mailer_patch):
        mailer_patch.send_vpal_suspended_email.return_value = self.mock_success_response
        approval_specialist = random_objects.random_internal_support_user(sf_id="some-sf-id-b")
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED,
                                                             approval_specialist=approval_specialist)
        app.buying_agent = None
        app.save()

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_SUSPENDED
        app.save()

        mailer_patch.send_vpal_suspended_email.assert_called_with(app.customer.email,
                                                                  app.customer.get_first_name(),
                                                                  [None, app.customer.co_borrower_email],
                                                                  app.get_approval_specialist_email(),
                                                                  app.get_approval_specialist_first_name(),
                                                                  app.get_approval_specialist_last_name())

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_ready_for_review_email(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED,
                                                             approval_specialist=random_objects.random_internal_support_user())


        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_READY_FOR_REVIEW
        app.save()

        mailer_patch.send_vpal_ready_for_review_email.assert_called_with(app.customer.get_first_name(),
                                                                       app.customer.email,
                                                                       app.customer.co_borrower_email,
                                                                       app.buying_agent.email,
                                                                       app.get_approval_specialist_email(),
                                                                       app.get_approval_specialist_first_name(),
                                                                       app.get_approval_specialist_last_name())

    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_vpal_ready_for_review_email_twice(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_email.return_value = self.mock_success_response
        app = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED,
                                                             approval_specialist=random_objects.random_internal_support_user())


        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_READY_FOR_REVIEW
        app.save()

        mailer_patch.send_vpal_ready_for_review_email.assert_called_with(app.customer.get_first_name(),
                                                                         app.customer.email,
                                                                         app.customer.co_borrower_email,
                                                                         app.buying_agent.email,
                                                                         app.get_approval_specialist_email(),
                                                                         app.get_approval_specialist_first_name(),
                                                                         app.get_approval_specialist_last_name())

        mailer_patch.reset_mock()

        app.stage = ApplicationStage.INCOMPLETE
        app.mortgage_status = MortgageStatus.VPAL_STARTED
        app.save()

        mailer_patch.send_vpal_ready_for_review_email.assert_not_called()

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_APP_INCOMPLETE
        app.save()

        mailer_patch.send_vpal_ready_for_review_email.assert_not_called()


    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_vpal_ready_for_review_email_if_not_qualified(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED)

        app.mortgage_status = MortgageStatus.VPAL_READY_FOR_REVIEW
        app.save()

        mailer_patch.send_vpal_ready_for_review_email.assert_not_called()

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_ready_for_review_email_if_first_send_fails(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED,
                                                             approval_specialist=random_objects.random_internal_support_user())

        NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=app,
                                          notification=Notification.objects.get(name=Notification.VPAL_INCOMPLETE),
                                          reason=f"hubspot returned 500")

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_READY_FOR_REVIEW
        app.save()

        mailer_patch.send_vpal_ready_for_review_email.assert_called_with(app.customer.get_first_name(),
                                                                         app.customer.email,
                                                                         app.customer.co_borrower_email,
                                                                         app.buying_agent.email,
                                                                         app.get_approval_specialist_email(),
                                                                         app.get_approval_specialist_first_name(),
                                                                         app.get_approval_specialist_last_name())

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_ready_for_review_email_with_default_values_if_no_approval_specialist(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                             mortgage_status=MortgageStatus.VPAL_STARTED)

        app.stage = ApplicationStage.QUALIFIED_APPLICATION
        app.mortgage_status = MortgageStatus.VPAL_READY_FOR_REVIEW
        app.save()

        mailer_patch.send_vpal_ready_for_review_email.assert_called_with(app.customer.get_first_name(),
                                                                       app.customer.email,
                                                                       app.customer.co_borrower_email,
                                                                       app.buying_agent.email,
                                                                       "hello@homewardmortgage.com",
                                                                       "Homeward",
                                                                       "Mortgage")


    @patch("application.email_trigger_tasks.mailer")
    @patch("application.signals.get_partner")
    def test_should_send_apex_site_pre_account_email(self, get_partner_patch, mailer_patch):
        get_partner_patch.return_value = {"name": "Apex Partner Name"}
        mailer_patch.send_apex_site_pre_account_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application(internal_referral=APEX_PARTNER_SITE, apex_partner_slug="some-brokerage")

        mailer_patch.send_apex_site_pre_account_email.assert_called_with(app.customer.email,
                                                                        app.customer.get_first_name(),
                                                                        "Apex Partner Name",
                                                                        app.build_apex_resume_link(),
                                                                        app.get_buying_agent_name(),
                                                                        app.get_buying_agent_email())


    @patch("application.email_trigger_tasks.mailer")
    @patch("application.signals.get_partner")
    def test_should_send_new_customer_partner_email(self, get_partner_patch, mailer_patch):
        get_partner_patch.return_value = {"name": "Apex Partner Name", "partner-email": "some-partner@homeward.com"}
        mailer_patch.send_apex_site_pre_account_email.return_value = self.mock_success_response
        current_home = random_objects.random_current_home()
        home_buying_location = random_objects.random_address()
        app: Application = random_objects.random_application(current_home=current_home, internal_referral=APEX_PARTNER_SITE,
                                                             apex_partner_slug="some-brokerage", home_buying_location=home_buying_location)

        mailer_patch.send_new_customer_partner_email.assert_called_with(app.customer.name,
                                                                        app.customer.email,
                                                                        app.customer.phone,
                                                                        app.home_buying_stage,
                                                                        app.home_buying_location.get_inline_address(),
                                                                        app.current_home.address.get_inline_address(),
                                                                        "Apex Partner Name",
                                                                        "some-partner@homeward.com")

    @patch("application.email_trigger_tasks.mailer")
    @patch("application.signals.get_partner")
    def test_should_send_new_customer_partner_email_with_legacy_webflow_field(self, get_partner_patch, mailer_patch):
        get_partner_patch.return_value = {"name": "Apex Partner Name", "parnter-email": "some-partner@homeward.com"}
        mailer_patch.send_apex_site_pre_account_email.return_value = self.mock_success_response
        current_home = random_objects.random_current_home()
        home_buying_location = random_objects.random_address()
        app: Application = random_objects.random_application(current_home=current_home, internal_referral=APEX_PARTNER_SITE,
                                                             apex_partner_slug="some-brokerage", home_buying_location=home_buying_location)

        mailer_patch.send_new_customer_partner_email.assert_called_with(app.customer.name,
                                                                        app.customer.email,
                                                                        app.customer.phone,
                                                                        app.home_buying_stage,
                                                                        app.home_buying_location.get_inline_address(),
                                                                        app.current_home.address.get_inline_address(),
                                                                        "Apex Partner Name",
                                                                        "some-partner@homeward.com")

    @patch("application.email_trigger_tasks.mailer")
    @patch("application.signals.get_partner")
    def test_should_send_new_customer_partner_email_missing_address(self, get_partner_patch, mailer_patch):
        get_partner_patch.return_value = {"name": "Apex Partner Name", "partner-email": "some-partner@homeward.com"}
        mailer_patch.send_apex_site_pre_account_email.return_value = self.mock_success_response
        current_home = random_objects.random_current_home()
        app: Application = random_objects.random_application(internal_referral=APEX_PARTNER_SITE, apex_partner_slug="some-brokerage")

        mailer_patch.send_new_customer_partner_email.assert_called_with(app.customer.name,
                                                                        app.customer.email,
                                                                        app.customer.phone,
                                                                        app.home_buying_stage,
                                                                        app.home_buying_location,
                                                                        None,
                                                                        "Apex Partner Name",
                                                                        "some-partner@homeward.com")


    @patch("application.email_trigger_tasks.mailer")
    @patch("application.signals.get_partner")
    def test_should_not_send_if_missing_partner_email(self, get_partner_patch, mailer_patch):
        get_partner_patch.return_value = {}
        new_customer_partner_email_notification = Notification.objects.get(name=Notification.NEW_CUSTOMER_PARTNER_EMAIL)
        mailer_patch.send_apex_site_pre_account_email.return_value = self.mock_success_response
        current_home = random_objects.random_current_home()
        app: Application = random_objects.random_application(internal_referral=APEX_PARTNER_SITE, apex_partner_slug="some-brokerage")

        mailer_patch.send_new_customer_partner_email.assert_not_called()
        partner_email_status = NotificationStatus.objects.get(application=app,
                                                              notification=new_customer_partner_email_notification,
                                                              status=NotificationStatus.NOT_SENT,
                                                              reason="Missing partner email address")


    @patch("utils.hubspot.send_apex_site_pre_account_email")
    @patch("application.signals.get_partner")
    def test_should_send_apex_site_pre_account_email_with_no_agent_or_partner(self, get_partner_patch, hubspot_patch):
        hubspot_patch.return_value = self.mock_success_response
        get_partner_patch.return_value = {}
        app: Application = random_objects.random_application(internal_referral=APEX_PARTNER_SITE, apex_partner_slug="some-brokerage")
        NotificationStatus.objects.filter(application=app).delete()
        app.buying_agent = None
        app.save()
        hubspot_patch.assert_called_with(app.customer.email,
                                         app.customer.get_first_name(),
                                         "your agent",
                                         app.build_apex_resume_link(),
                                         None)

    @patch("application.email_trigger_tasks.mailer")
    @patch("application.signals.get_partner")
    def test_should_not_send_apex_site_pre_account_email_twice(self, get_partner_patch, mailer_patch):
        mailer_patch.send_apex_site_pre_account_email.return_value = self.mock_success_response
        get_partner_patch.return_value = {"name": "Apex Partner Name"}
        app: Application = random_objects.random_application(internal_referral=APEX_PARTNER_SITE, apex_partner_slug="some-brokerage")

        mailer_patch.send_apex_site_pre_account_email.assert_called_with(app.customer.email,
                                                                        app.customer.get_first_name(),
                                                                        "Apex Partner Name",
                                                                        app.build_apex_resume_link(),
                                                                        app.get_buying_agent_name(),
                                                                        app.get_buying_agent_email())

        mailer_patch.reset_mock()
        app.save()
        mailer_patch.send_apex_site_pre_account_email.assert_not_called()


    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_apex_site_pre_account_email_if_referral_source_not_apex(self, mailer_patch):
        mailer_patch.send_apex_site_pre_account_email.return_value = self.mock_success_response
        app: Application = random_objects.random_application()
        mailer_patch.send_apex_site_pre_account_email.assert_not_called()

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_ready_for_review_follow_up_email(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_follow_up.return_value = self.mock_success_response
        app = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                                mortgage_status=MortgageStatus.VPAL_READY_FOR_REVIEW)

        app.save()
        send_vpal_ready_for_review_follow_up()

        mailer_patch.send_vpal_ready_for_review_follow_up.assert_called_with(app.customer.get_first_name(), app.customer.get_last_name(), app.customer.email, app.customer.co_borrower_email, app.buying_agent.email)

    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_vpal_ready_for_review_follow_up_email_if_wrong_app_stage(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_follow_up.return_value = self.mock_success_response

        app = random_objects.random_application(stage=ApplicationStage.INCOMPLETE,
                                                mortgage_status=MortgageStatus.VPAL_READY_FOR_REVIEW)
        app.save()

        mailer_patch.send_vpal_ready_for_review_email_follow_up.assert_not_called()

    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_vpal_rfrv_email_if_mortgage_status_wrong_stage(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_follow_up.return_value = self.mock_success_response

        app = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,mortgage_status=MortgageStatus.VPAL_STARTED)
        app.save()

        mailer_patch.send_vpal_ready_for_review_email_follow_up.assert_not_called()


    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_follow_up_to_correct_applications(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_follow_up.return_value = self.mock_success_response

        app1 = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,mortgage_status=MortgageStatus.VPAL_STARTED)
        app1.save()

        app2 = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                                mortgage_status=MortgageStatus.VPAL_READY_FOR_REVIEW)
        app2.save()

        send_vpal_ready_for_review_follow_up()

        mailer_patch.send_vpal_ready_for_review_follow_up.assert_called_with(app2.customer.get_first_name(), app2.customer.get_last_name(), app2.customer.email, app2.customer.co_borrower_email, app2.buying_agent.email)

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_a_follow_up_for_each_filtered_application(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_follow_up.return_value = self.mock_success_response

        app1 = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                                mortgage_status=MortgageStatus.VPAL_READY_FOR_REVIEW)
        app1.save()
        app2 = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                                mortgage_status=MortgageStatus.VPAL_READY_FOR_REVIEW)
        app2.save()

        apps = Application.objects.filter(
                                        stage=ApplicationStage.QUALIFIED_APPLICATION,
                                        mortgage_status=MortgageStatus.VPAL_READY_FOR_REVIEW)

        send_vpal_ready_for_review_follow_up()

        self.assertEqual(mailer_patch.send_vpal_ready_for_review_follow_up.call_count, 2)

    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_vpal_rfrf_email_if_original_email_sent_within_72_hours(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_follow_up.return_value = self.mock_success_response

        app = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                                mortgage_status=MortgageStatus.VPAL_READY_FOR_REVIEW)

        app.save()

        notification = Notification.objects.get(name=Notification.VPAL_READY_FOR_REVIEW)
        NotificationStatus.objects.create(application=app, notification=notification, status=NotificationStatus.SENT)

        send_vpal_ready_for_review_follow_up()

        self.assertEqual(mailer_patch.send_vpal_ready_for_review_follow_up.call_count, 0)

    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_vpal_rfrf_email_if_already_sent_within_72_hours(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_follow_up.return_value = self.mock_success_response

        app = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                                mortgage_status=MortgageStatus.VPAL_READY_FOR_REVIEW)

        app.save()

        notification = Notification.objects.get(name=Notification.VPAL_READY_FOR_REVIEW_FOLLOW_UP)
        NotificationStatus.objects.create(application=app, notification=notification, status=NotificationStatus.SENT)

        send_vpal_ready_for_review_follow_up()

        self.assertEqual(mailer_patch.send_vpal_ready_for_review_follow_up.call_count, 0)

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_rfrf_email_if_not_sent_within_72_hours(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_follow_up.return_value = self.mock_success_response

        app = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                                mortgage_status=MortgageStatus.VPAL_READY_FOR_REVIEW)

        app.save()

        time_threshold = timezone.now() - timedelta(hours=73)

        notification = Notification.objects.get(name=Notification.VPAL_READY_FOR_REVIEW)
        ns = NotificationStatus.objects.create(application=app, notification=notification,
                                               status=NotificationStatus.SENT)

        ns.created_at = time_threshold
        ns.save()

        send_vpal_ready_for_review_follow_up()

        self.assertEqual(mailer_patch.send_vpal_ready_for_review_follow_up.call_count, 1)

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_vpal_rfrf_email_if_original_not_sent_within_72_hours(self, mailer_patch):
        mailer_patch.send_vpal_ready_for_review_follow_up.return_value = self.mock_success_response

        app = random_objects.random_application(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                                mortgage_status=MortgageStatus.VPAL_READY_FOR_REVIEW)

        app.save()

        time_threshold = timezone.now() - timedelta(hours=73)

        notification = Notification.objects.get(name=Notification.VPAL_READY_FOR_REVIEW_FOLLOW_UP)
        ns = NotificationStatus.objects.create(application=app, notification=notification,
                                               status=NotificationStatus.SENT)

        ns.created_at = time_threshold
        ns.save()

        send_vpal_ready_for_review_follow_up()

        self.assertEqual(mailer_patch.send_vpal_ready_for_review_follow_up.call_count, 1)

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_welcome_email_for_pricing_referral(self, mailer_patch):
        pricing = random_objects.random_pricing()
        app = random_objects.random_application(questionnaire_response_id=pricing.questionnaire_response_id)

        mailer_patch.send_agent_referral_welcome_email = self.mock_success_response
        send_registered_client_notification(app.id)
        expected_url = f'{settings.ONBOARDING_BASE_URL}estimates/view/{app.questionnaire_response_id}'
        mailer_patch.send_agent_referral_welcome_email.assert_called_once_with(app.customer, app.buying_agent, expected_url)

    @patch("application.email_trigger_tasks.mailer")
    @patch("application.signals.get_partner")
    def test_should_suppress_welcome_email_for_pricing_referral_when_from_apex_site(self, get_partner_patch, mailer_patch):
        pricing = random_objects.random_pricing()
        get_partner_patch.return_value = {}
        app = random_objects.random_application(questionnaire_response_id=pricing.questionnaire_response_id, apex_partner_slug='some-apex-partner')
        agent_referral_customer_welcome_email_notification = Notification.objects.get(name=Notification.AGENT_REFERRAL_CUSTOMER_WELCOME_EMAIL)

        send_registered_client_notification(app.id)
        welcome_email_notification_status = NotificationStatus.objects.get(application=app,
                                                                 notification=agent_referral_customer_welcome_email_notification,
                                                                 status=NotificationStatus.SUPPRESSED)
        self.assertEqual(welcome_email_notification_status.reason, "Application has apex partner slug")

    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_application_complete_email_when_approval_specialist_assigned(self, mailer_patch):
        mailer_patch.send_application_complete_email.return_value = self.mock_success_response
        Notification.objects.create(name=Notification.APPLICATION_COMPLETE, is_active=True)
        
        agent = random_objects.random_agent()
        app = random_objects.random_application(buying_agent_id=agent.id, 
                                                loan_advisor=random_objects.random_internal_support_user(sf_id='11111111'),
                                                approval_specialist=random_objects.random_internal_support_user(sf_id='222222222')
                                                )

        app.stage = ApplicationStage.COMPLETE
        app.save()
        
        application_complete_notification = Notification.objects.get(name=Notification.APPLICATION_COMPLETE)
        
        ns = NotificationStatus.objects.create(application=app, notification=application_complete_notification,
                                               status=NotificationStatus.SENT)
        
        mailer_patch.send_application_complete_email.assert_called_with(app.customer.email, 
                                                                        app.customer.get_first_name(), 
                                                                        app.get_buying_agent_email(), 
                                                                        app.get_approval_specialist_first_name(), 
                                                                        app.get_approval_specialist_last_name(), 
                                                                        app.get_approval_specialist_email(), 
                                                                        app.get_loan_advisor_first_name(), 
                                                                        app.get_loan_advisor_last_name())

    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_application_complete_email_if_app_not_complete(self, mailer_patch):
        mailer_patch.send_application_complete_email.return_value = self.mock_success_response
        agent = random_objects.random_agent()
        app = random_objects.random_application(buying_agent_id=agent.id, 
                                                loan_advisor=random_objects.random_internal_support_user(sf_id='11111111'),
                                                approval_specialist=random_objects.random_internal_support_user(sf_id='222222222'))
        
        
        Notification.objects.create(name=Notification.APPLICATION_COMPLETE, is_active=True)
        application_complete_notification = Notification.objects.get(name=Notification.APPLICATION_COMPLETE)
        
        ns = NotificationStatus.objects.create(application=app, notification=application_complete_notification,
                                               status=NotificationStatus.SENT)
        
        mailer_patch.send_application_complete_email.assert_not_called()
    
    @patch("application.email_trigger_tasks.mailer")
    def test_should_send_application_complete_email_when_approval_specialist_assigned(self, mailer_patch):
        mailer_patch.send_application_complete_email.return_value = self.mock_success_response
        Notification.objects.create(name=Notification.APPLICATION_COMPLETE, is_active=True)
        agent = random_objects.random_agent()
        app = random_objects.random_application(buying_agent_id=agent.id, 
                                                loan_advisor=random_objects.random_internal_support_user(sf_id='11111111'))
        
        app.stage = ApplicationStage.COMPLETE
        approval_specialist= random_objects.random_internal_support_user(sf_id='222222222')
        app.approval_specialist = approval_specialist
        app.save()
        
        application_complete_notification = Notification.objects.get(name=Notification.APPLICATION_COMPLETE)
        
        ns = NotificationStatus.objects.create(application=app, notification=application_complete_notification,
                                               status=NotificationStatus.SENT)
        
        mailer_patch.send_application_complete_email.assert_called_with(app.customer.email, 
                                                                        app.customer.get_first_name(), 
                                                                        app.get_buying_agent_email(), 
                                                                        app.get_approval_specialist_first_name(), 
                                                                        app.get_approval_specialist_last_name(), 
                                                                        app.get_approval_specialist_email(), 
                                                                        app.get_loan_advisor_first_name(), 
                                                                        app.get_loan_advisor_last_name())
    
    @patch("application.email_trigger_tasks.mailer")
    def test_should_not_send_application_complete_email_approval_specialist_not_assigned(self, mailer_patch):
        mailer_patch.send_application_complete_email.return_value = self.mock_success_response
        agent = random_objects.random_agent()
        app = random_objects.random_application(buying_agent_id=agent.id, 
                                                loan_advisor=random_objects.random_internal_support_user(sf_id='11111111'))
        
        
        Notification.objects.create(name=Notification.APPLICATION_COMPLETE, is_active=True)
        application_complete_notification = Notification.objects.get(name=Notification.APPLICATION_COMPLETE)
        
        ns = NotificationStatus.objects.create(application=app, notification=application_complete_notification,
                                               status=NotificationStatus.SENT)
        
        mailer_patch.send_application_complete_email.assert_not_called()