import logging
import uuid
from datetime import datetime, timedelta

from celery.task import periodic_task
from django.utils import timezone

from application import constants
from application.models.application import (FloorPriceNotFoundException,
                                            MortgageStatus)
from application.models.models import (Application, ApplicationStage,
                                       StageHistory)
from application.models.notification import Notification
from application.models.notification_status import NotificationStatus
from application.models.offer import Offer
from application.models.pricing import Pricing
from utils import mailer
from utils.celery import app as celery_app


class EmailTriggerCriteriaValidationException(Exception):
    pass


logger = logging.getLogger(__name__)


@celery_app.task(queue='application-service-tasks')
def queue_photo_task_complete_notification(current_home_id: uuid.UUID):
    photo_upload_notification = Notification.objects.get(name=Notification.PHOTO_UPLOAD)

    if not photo_upload_notification.is_active:
        logger.info("Photo upload notification is_active is False", extra=dict(
            type="photo_upload_notification_not_active",
            notification_id=photo_upload_notification.id,
            current_home_id=current_home_id
        ))
        return

    applications = Application.objects.filter(current_home_id=current_home_id)

    if applications.count() != 1:
        raise EmailTriggerCriteriaValidationException(
            "tried sending email for current home {}, but {} applications found!".format(
                current_home_id, applications.count()))
    else:
        application: Application = applications.first()
        mailer.send_photo_task_complete_notification(application.customer.get_first_name(),
                                                 application.customer.get_last_name(), application.get_link())
        NotificationStatus.objects.create(status=NotificationStatus.SENT,
                                          application=application,
                                          notification=photo_upload_notification)


@celery_app.task(queue='application-service-tasks')
def queue_under_review_email(application_id: uuid.UUID):
    application_under_review_notification = Notification.objects.get(name=Notification.APPLICATION_UNDER_REVIEW)

    if not application_under_review_notification.is_active:
        logger.info("Photo under review notification is_active is False", extra=dict(
            type="photo_under_review_notification_not_active",
            notification_id=application_under_review_notification.id,
            application_id=application_id,
            action="email_not_active"
        ))
        return

    application = Application.objects.get(id=application_id)
    number_of_times_in_qualified = StageHistory.objects.filter(application_id=application_id,
                                                               new_stage=
                                                               ApplicationStage.QUALIFIED_APPLICATION).count()

    cc_email_list = []
    agent_email = application.get_buying_agent_email()
    if agent_email:
        cc_email_list.append(agent_email)
    if application.customer.co_borrower_email:
        cc_email_list.append(application.customer.co_borrower_email)
    if number_of_times_in_qualified == 1:
        loan_advisor = application.loan_advisor
        if loan_advisor:
            response = mailer.send_application_under_review(application.customer.get_first_name(),
                                                            application.customer.email,
                                                            str(application.id), cc_email_list, loan_advisor.first_name,
                                                            loan_advisor.last_name, loan_advisor.schedule_a_call_url,
                                                            loan_advisor.phone)
        else:
            response = mailer.send_application_under_review(application.customer.get_first_name(),
                                                            application.customer.email,
                                                            str(application.id), cc_email_list)
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT,
                                              application=application,
                                              notification=application_under_review_notification)
    else:
        logger.info("Email not sent", extra=dict(
            type="email_not_sent_under_review_email",
            application_id=application_id,
            number_of_times_in_qualified=number_of_times_in_qualified,
            application_under_review_notification_id=application_under_review_notification.id
        ))


@celery_app.task(queue='application-service-tasks')
def queue_approval_email(application_id: uuid.UUID):
    application = Application.objects.get(id=application_id)
    street_address = mailer.get_address_if_applicable(application)

    approval_notification = Notification.objects.get(name=Notification.APPROVAL)
    hw_mortgage_candidate_approval_notification = Notification.objects.get(
        name=Notification.HW_MORTGAGE_CANDIDATE_APPROVAL)

    if NotificationStatus.objects.filter(application=application, status=NotificationStatus.SENT,
                                         notification_id__in=[approval_notification,
                                                              hw_mortgage_candidate_approval_notification]).count() == 0:
        if application.is_hw_mortgage_candidate():
            if not hw_mortgage_candidate_approval_notification.is_active:
                logger.info(
                    "Mortgage candidate approval notification not active", extra=dict(
                        type="mortgage_candidate_approval_notification_not_active",
                        application_id=application_id,
                        hw_mortgage_candidate_approval_notification_id=hw_mortgage_candidate_approval_notification.id
                    ))
                return
            queue_hw_mortgage_candidate_email(application, street_address, hw_mortgage_candidate_approval_notification)
        else:
            if not approval_notification.is_active:
                logger.info(
                    "Non-mortgage candidate approval notification not active", extra=dict(
                        type="non_mortgage_candidate_approval_notification_not_active",
                        application_id=application_id,
                        hw_mortgage_candidate_approval_notification_id=hw_mortgage_candidate_approval_notification.id
                    ))
                return
            queue_non_hw_mortgage_candidate_email(application, street_address, approval_notification)


def queue_hw_mortgage_candidate_email(application, address, notification):
    if not notification.is_active:
        logger.info("Queue HW Mortgage candidate email notification is_active is False", extra=dict(
            type="hw_mortgage_candidate_email_notification_not_active",
            application_id=application.id,
            notification_id=notification.id,
        ))
        return

    if address is None:
        NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                          notification=notification, reason="Missing street_address value")
        return
    if application.homeward_owner_email is None:
        NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                          notification=notification, reason="Missing homeward_owner_email")
        return

    if application.preapproval:
        estimated_down_payment = application.preapproval.estimated_down_payment
        amount = application.preapproval.amount
    else:
        estimated_down_payment = None
        amount = None
    loan_advisor = application.loan_advisor
    cc_email_list = application.generate_cc_emails_list()

    if loan_advisor is not None:
        cc_email_list.append(application.get_loan_advisor_email())
        response = mailer.send_hw_mortgage_candidate_approval(application.customer.email,
                                                              application.homeward_owner_email,
                                                              application.customer.get_first_name(),
                                                              amount,
                                                              estimated_down_payment,
                                                              address,
                                                              cc_email_list,
                                                              loan_advisor.first_name,
                                                              loan_advisor.last_name,
                                                              loan_advisor.phone,
                                                              loan_advisor.email,
                                                              loan_advisor.schedule_a_call_url)
    else:
        response = mailer.send_hw_mortgage_candidate_approval(application.customer.email,
                                                              application.homeward_owner_email,
                                                              application.customer.get_first_name(),
                                                              amount,
                                                              estimated_down_payment,
                                                              address,
                                                              cc_email_list,
                                                              constants.DEFAULT_LOAN_ADVISOR_FIRST_NAME,
                                                              constants.DEFAULT_LOAN_ADVISOR_LAST_NAME,
                                                              constants.DEFAULT_LOAN_ADVISOR_PHONE,
                                                              constants.DEFAULT_LOAN_ADVISOR_EMAIL,
                                                              constants.DEFAULT_LOAN_ADVISOR_CALL_URL)
    if response.status_code == 200:
        NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                          notification=notification)
    else:
        logger.info("Non-success response code from send_hw_mortgage_candidate_approval", extra=dict(
            type="non_success_from_send_hw_mortgage_candidate_approval",
            response_code=response.status_code,
            response=response.json(),
            application_id=application.id
        ))


def queue_non_hw_mortgage_candidate_email(application, address, notification):
    if not notification.is_active:
        logger.info("Queue non-HW Mortgage candidate email notification is_active is False", extra=dict(
            type="non_hw_mortgage_candidate_email_notification_not_active",
            application_id=application.id,
            notification_id=notification.id,
        ))
        return

    if address is None:
        NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                          notification=notification, reason="Missing street_address value")
        return
    if application.homeward_owner_email is None:
        NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                          notification=notification, reason="Missing homeward_owner_email")
        return

    if application.preapproval:
        estimated_down_payment = application.preapproval.estimated_down_payment
        amount = application.preapproval.amount
    else:
        estimated_down_payment = None
        amount = None
    cx = application.cx_manager
    cc_email_list = application.generate_cc_emails_list()
    if cx:
        response = mailer.send_non_hw_mortgage_candidate_approval(application.customer.email,
                                                                  application.customer.get_first_name(),
                                                                  amount, estimated_down_payment, address,
                                                                  cc_email_list,
                                                                  application.homeward_owner_email, cx.first_name,
                                                                  cx.last_name, cx.schedule_a_call_url, cx.email)
    else:
        response = mailer.send_non_hw_mortgage_candidate_approval(application.customer.email,
                                                                  application.customer.get_first_name(),
                                                                  amount, estimated_down_payment, address,
                                                                  cc_email_list, application.homeward_owner_email)

    if response.status_code == 200:
        NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                          notification=notification)
    else:
        logger.info("Non-success response code from send_non_hw_mortgage_candidate_approval", extra=dict(
            type="non_success_from_send_non_hw_mortgage_candidate_approval",
            response_code=response.status_code,
            response=response.json(),
            application_id=application.id
        ))


@celery_app.task(queue='application-service-tasks')
def queue_agent_instructions_email(application_id: uuid.UUID):
    agent_instructions_notification = Notification.objects.get(name=Notification.AGENT_OFFER_INSTRUCTIONS)

    if not agent_instructions_notification.is_active:
        logger.info("Queue agent instructions email notification is_active is False", extra=dict(
            type="agent_instructions_notification_not_active",
            application_id=application_id,
            agent_instructions_notification_id=agent_instructions_notification.id,
        ))
        return

    application = Application.objects.get(id=application_id)

    if application.buying_agent is None \
            or application.buying_agent.email is None:
        raise EmailTriggerCriteriaValidationException(
            'missing buying agent email address for application {}'.format(application_id))
    street_address = mailer.get_address_if_applicable(application)
    notification_count = NotificationStatus.objects.filter(application=application,
                                                           notification=agent_instructions_notification).count()
    if (street_address is not None
        and application.homeward_owner_email is not None) \
            and notification_count == 0:

        cx = application.cx_manager
        homeward_owner_email = application.homeward_owner_email
        if cx:
            response = mailer.send_agent_instructions(application.buying_agent.name,
                                                      application.get_buying_agent_email(),
                                                      application.customer.name, str(application.id), [cx.email],
                                                      homeward_owner_email, cx.first_name, cx.last_name,
                                                      cx.schedule_a_call_url)
        else:
            response = mailer.send_agent_instructions(application.buying_agent.name,
                                                      application.get_buying_agent_email(),
                                                      application.customer.name, str(application.id), [],
                                                      homeward_owner_email)
    else:
        logger.info("current home, pre_approval, owner email data or instructions have already been sent."
                    "Skipping queue_agent_instructions", extra=dict(
                        type="missing_info_queue_agent_instructions_email",
                        street_address=street_address,
                        homeward_owner_email=application.homeward_owner_email,
                        notification_count=notification_count
                    ))
        return
    if response.status_code == 200:
        NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                          notification=agent_instructions_notification)


@celery_app.task(queue='application-service-tasks')
def queue_offer_submitted_email(offer_id: uuid.UUID, offer_price: int):
    offer_submitted_notification = Notification.objects.get(name=Notification.OFFER_SUBMITTED)

    if not offer_submitted_notification.is_active:
        logger.info("Queue offer submitted notification not active", extra=dict(
            type="offer_submitted_notification_not_active",
            offer_id=offer_id,
            offer_submitted_notification_id=offer_submitted_notification.id,
            offer_price=offer_price
        ))
        return

    offer = Offer.objects.get(id=offer_id)
    application = offer.application

    if offer.offer_property_address is None \
            or offer.offer_property_address.street is None \
            or offer_price is None:
        raise EmailTriggerCriteriaValidationException(
            "missing required data to send offer submitted email for application {}".format(application.id))

    if offer.already_under_contract:
        # Do not send offer submitted email if offer is takeover
        NotificationStatus.objects.create(status=NotificationStatus.SUPPRESSED, application=application,
                                          notification=offer_submitted_notification,
                                          reason="Offer is takeover")
        return

    cc_email_list = []

    if application.customer.co_borrower_email:
        cc_email_list.append(application.customer.co_borrower_email)

    try:
        response = mailer.send_offer_submitted(application.customer, offer, offer_price, cc_email_list,
                                               application.homeward_owner_email)
    except FloorPriceNotFoundException as e:
        logger.exception("FloorPriceNotFoundException raised during send_offer_submitted", extra=dict(
            type="send_offer_submitted_exception_raised",
            application_id=application.id
        ))
        NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                          notification=offer_submitted_notification, reason=f"Floor price not set: {e}")
        return

    if response.status_code == 200:
        NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                          notification=offer_submitted_notification)


@celery_app.task(queue='application-service-tasks')
def queue_offer_submitted_agent_email(offer_id: uuid.UUID):
    offer_submitted_agent_notification = Notification.objects.get(name=Notification.OFFER_SUBMITTED_AGENT)

    if not offer_submitted_agent_notification.is_active:
        logger.info("Queue offer_submitted_agent_notification is not active", extra=dict(
            type="offer_submitted_agent_notification_not_active",
            offer_id=offer_id,
            offer_submitted_agent_notification_id=offer_submitted_agent_notification.id
        ))
        return

    offer = Offer.objects.get(id=offer_id)

    if offer.offer_property_address is None \
            or offer.offer_property_address.street is None \
            or offer.application.buying_agent is None \
            or offer.application.buying_agent.email is None \
            or offer.application.buying_agent.name is None \
            or offer.application.cx_manager is None \
            or offer.application.cx_manager.first_name is None \
            or offer.application.cx_manager.last_name is None:
        raise EmailTriggerCriteriaValidationException(
            "missing information necessary to send offer submitted agent email for offer {}".format(offer_id))

    if offer.already_under_contract:
        # Do not send offer submitted email if offer is takeover
        NotificationStatus.objects.create(status=NotificationStatus.SUPPRESSED, application=offer.application,
                                          notification=offer_submitted_agent_notification,
                                          reason="Offer is takeover")
        return

    cc_email_list = [offer.application.get_cx_email()]
    response = mailer.send_offer_submitted_agent(offer.application.buying_agent.email,
                                                 offer.application.buying_agent.name,
                                                 offer.offer_property_address.street,
                                                 offer.application.cx_manager.first_name,
                                                 offer.application.cx_manager.last_name,
                                                 offer.application.homeward_owner_email,
                                                 cc_email_list)

    if response.status_code == 200:
        NotificationStatus.objects.create(status=NotificationStatus.SENT, application=offer.application,
                                          notification=offer_submitted_agent_notification)


@celery_app.task(queue='application-service-tasks')
def queue_unacknowledged_service_agreement_email(application_id: uuid.UUID):
    unacknowledged_service_agreement_notification = Notification.objects.get(
        name=Notification.OFFER_REQUESTED_UNACKNOWLEDGED_SERVICE_AGREEMENT)

    if not unacknowledged_service_agreement_notification.is_active:
        logger.info("Queue unacknowledged_service_agreement_notification is not active", extra=dict(
            type="unacknowledged_service_agreement_notification_not_active",
            application_id=application_id,
            unacknowledged_service_agreement_notification_id=unacknowledged_service_agreement_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)

    if application is None \
            or application.customer is None \
            or application.customer.email is None \
            or application.customer.name is None:
        raise EmailTriggerCriteriaValidationException(
            f"missing required data to send unacknowledged service agreement email for application {application_id}")

    response = mailer.send_unacknowledged_service_agreement_email(application.customer)

    if response.status_code == 200:
        NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                          notification=unacknowledged_service_agreement_notification)
    else:
        logger.error("Non-success response code from send_unacknowledged_service_agreement_email", extra=dict(
            type="non_success_for_send_unacknowledged_service_agreement_email",
            response_status_code=response.status_code,
            response=response.json(),
            application_id=application_id,
        ))
        NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                          notification=unacknowledged_service_agreement_notification,
                                          reason=f"hubspot returned {response.status_code}")


@celery_app.task(queue='application-service-tasks')
def queue_offer_accepted_email(application_id: uuid.UUID):
    offer_accepted_notification = Notification.objects.get(name=Notification.OFFER_ACCEPTED)

    if not offer_accepted_notification.is_active:
        logger.info("Queue offer_accepted_notification is not active", extra=dict(
            type="offer_accepted_notification_not_active",
            application_id=application_id,
            offer_accepted_notification_id=offer_accepted_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)

    if application.new_home_purchase is None \
            or application.new_home_purchase.contract_price is None \
            or application.new_home_purchase.rent is None \
            or application.new_home_purchase.rent.amount_months_one_and_two is None \
            or application.new_home_purchase.rent.type is None \
            or application.new_home_purchase.earnest_deposit_percentage is None \
            or application.new_home_purchase.option_period_end_date is None \
            or application.new_home_purchase.address is None \
            or application.new_home_purchase.address.street is None:
        raise EmailTriggerCriteriaValidationException(
            "missing information necessary to send offer accepted email for application {}"
                .format(application_id))

    cc_email_list = application.generate_cc_emails_list()
    response = mailer.send_offer_accepted(application.customer.email, application.customer.get_first_name(),
                                          application.new_home_purchase, application.get_formatted_floor_price(),
                                          cc_email_list, application.homeward_owner_email)

    if response.status_code == 200:
        NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                          notification=offer_accepted_notification)
    else:
        logger.error("Non-success response code from send_offer_accepted", extra=dict(
            type="non_success_for_send_offer_accepted",
            response_status_code=response.status_code,
            response=response.json(),
            application_id=application_id,
        ))
        NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                          notification=offer_accepted_notification,
                                          reason=f"hubspot returned {response.status_code}")


@celery_app.task(queue='application-service-tasks')
def queue_purchase_price_updated_email(preapproval_id: uuid.UUID, amount: int):
    purchase_price_notification = Notification.objects.get(name=Notification.PURCHASE_PRICE_UPDATED)

    if not purchase_price_notification.is_active:
        logger.info("Queue purchase_price_notification is not active", extra=dict(
            type="purchase_price_notification_not_active",
            preapproval_id=preapproval_id,
            purchase_price_notification=purchase_price_notification.id
        ))
        return

    try:
        application = Application.objects.get(preapproval_id=preapproval_id)
    except Application.DoesNotExist as e:
        logger.exception(f"Application does not exist for preapproval_id: {preapproval_id}", exc_info=e, extra=dict(
            type="application_not_exist_for_preapproval_id",
            preapproval_id=preapproval_id
        ))
        return

    if application.customer is None \
            or application.customer.get_first_name() is None \
            or application.customer.email is None \
            or amount <= 0:
        raise EmailTriggerCriteriaValidationException(
            f"missing information necessary to send purchase price updated email for application {application.id}")

    cc_email_list = application.generate_cc_emails_list()

    if application.is_hw_mortgage_candidate():
        loan_advisor = application.loan_advisor

        if loan_advisor:
            cc_email_list.append(application.get_loan_advisor_email())

        contact_first_name = loan_advisor.first_name if loan_advisor else constants.DEFAULT_LOAN_ADVISOR_FIRST_NAME
        contact_last_name = loan_advisor.last_name if loan_advisor else constants.DEFAULT_LOAN_ADVISOR_LAST_NAME
        contact_email = loan_advisor.email if loan_advisor else constants.DEFAULT_LOAN_ADVISOR_EMAIL
        contact_schedule_a_call_url = loan_advisor.schedule_a_call_url if loan_advisor else constants.DEFAULT_LOAN_ADVISOR_CALL_URL
    else:
        cx = application.cx_manager
        contact_first_name = cx.first_name if cx else constants.DEFAULT_CX_MANAGER_FIRST_NAME
        contact_last_name = cx.last_name if cx else constants.DEFAULT_CX_MANAGER_LAST_NAME
        contact_email = cx.email if cx else constants.DEFAULT_CX_MANAGER_EMAIL
        contact_schedule_a_call_url = cx.schedule_a_call_url if cx else constants.DEFAULT_CX_MANAGER_CALL_URL

    response = mailer.send_purchase_price_updated(application.customer, amount, cc_email_list, contact_first_name,
                                                  contact_last_name, contact_email, contact_schedule_a_call_url)

    if response.status_code == 200:
        NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                          notification=purchase_price_notification)
    else:
        logger.error("Non-success response code from send_purchase_price_updated", extra=dict(
            type="non_success_for_send_purchase_price_updated",
            response_status_code=response.status_code,
            response=response.json(),
            application_id=application.id,
        ))
        NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                          notification=purchase_price_notification,
                                          reason=f'hubspot returned {response.status_code}')


@celery_app.task(queue='application-service-tasks')
def queue_customer_close_email(application_id: uuid.UUID):
    customer_close_notification = Notification.objects.get(name=Notification.CUSTOMER_CLOSE)

    if not customer_close_notification.is_active:
        logger.info("Queue customer_close_notification is not active", extra=dict(
            type="customer_close_notification_not_active",
            application_id=application_id,
            customer_close_notification_id=customer_close_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)

    if application.notificationstatus_set.filter(notification=customer_close_notification,
                                                 status=NotificationStatus.SENT).count() > 0:
        logger.info(f"Customer close email send for {application_id} has been sent", extra=dict(
            type="customer_close_email_already_sent",
            application_id=application_id
        ))
    elif application.new_home_purchase is None \
            or application.new_home_purchase.address is None \
            or application.new_home_purchase.address.street is None:
        raise EmailTriggerCriteriaValidationException(
            "missing information necessary to send customer close email for application {}"
            .format(application_id))
    elif application.new_home_purchase.is_reassigned_contract:
        NotificationStatus.objects.get_or_create(status=NotificationStatus.SUPPRESSED, application=application,
                                                 notification=customer_close_notification,
                                                 reason="Application is reassigned contract")
    else:
        cc_email_list = application.generate_cc_emails_list()
        response = mailer.send_customer_close(application.customer.get_first_name(), application.customer.email,
                                              application.new_home_purchase.address.street, cc_email_list,
                                              application.homeward_owner_email)
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=customer_close_notification)
        else:
            logger.error("Non-success response code from send_customer_close", extra=dict(
                type="non_success_for_send_customer_close",
                response_status_code=response.status_code,
                response=response.json(),
                application_id=application.id,
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=customer_close_notification,
                                              reason=f'hubspot returned {response.status_code}')


@celery_app.task(queue='application-service-tasks')
def queue_agent_customer_close_email(application_id: uuid.UUID):
    agent_customer_close_notification = Notification.objects.get(name=Notification.AGENT_CUSTOMER_CLOSE)

    if not agent_customer_close_notification.is_active:
        logger.info("Queue agent_customer_close_notification is not active", extra=dict(
            type="agent_customer_close_notification_not_active",
            application_id=application_id,
            agent_customer_close_notification_id=agent_customer_close_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)

    if application.notificationstatus_set.filter(notification=agent_customer_close_notification,
                                                 status=NotificationStatus.SENT).count() > 0:
        logger.info(f"Agent customer close email send for {application_id} has been sent", extra=dict(
            type="agent_customer_close_email_already_sent",
            application_id=application_id
        ))
    elif application.new_home_purchase is None \
            or application.new_home_purchase.address is None \
            or application.new_home_purchase.address.street is None:
        raise EmailTriggerCriteriaValidationException(
            "missing information necessary to send agent customer close email for application {}"
            .format(application_id))
    elif application.new_home_purchase.is_reassigned_contract:
        NotificationStatus.objects.get_or_create(status=NotificationStatus.SUPPRESSED, application=application,
                                                 notification=agent_customer_close_notification,
                                                 reason="Application is reassigned contract")
    else:
        tc_email = application.get_transaction_coordinator_email()
        response = mailer.send_agent_customer_close(application.buying_agent.get_first_name(),
                                                    application.get_buying_agent_email(),
                                                    application.customer.name,
                                                    application.new_home_purchase.address.street,
                                                    application.homeward_owner_email, tc_email)
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=agent_customer_close_notification)
        else:
            logger.error("Non-success response code from send_agent_customer_close", extra=dict(
                type="non_success_for_send_agent_customer_close",
                response_status_code=response.status_code,
                response=response.json(),
                application_id=application.id,
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=agent_customer_close_notification,
                                              reason=f'hubspot returned {response.status_code}')


@celery_app.task(queue='application-service-tasks')
def queue_homeward_close_email(application_id: uuid.UUID):
    homeward_close_notification = Notification.objects.get(name=Notification.HOMEWARD_CLOSE)

    if not homeward_close_notification.is_active:
        logger.info("Queue homeward_close_notification is not active", extra=dict(
            type="homeward_close_notification_not_active",
            application_id=application_id,
            homeward_close_notification_id=homeward_close_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)

    if application.notificationstatus_set.filter(notification=homeward_close_notification,
                                                 status=NotificationStatus.SENT).count() == 0:
        if application.new_home_purchase and application.new_home_purchase.is_reassigned_contract:
            NotificationStatus.objects.get_or_create(status=NotificationStatus.SUPPRESSED, application=application,
                                                     notification=homeward_close_notification,
                                                     reason="Application is reassigned contract")
            return

        cc_email_list = application.generate_cc_emails_list()
        response = mailer.send_homeward_close(application.customer, cc_email_list,
                                              application.homeward_owner_email)
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=homeward_close_notification)
        else:
            logger.error("Non-success response code from send_homeward_close", extra=dict(
                type="non_success_for_send_homeward_close",
                response_status_code=response.status_code,
                response=response.json(),
                application_id=application.id,
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=homeward_close_notification,
                                              reason=f'hubspot returned {response.status_code}')
    else:
        logger.info("Notification homeward_close_notification already sent for application", extra=dict(
            type="homeward_close_notification_already_sent",
            application_id=application_id,
            homeward_close_notification_id=homeward_close_notification.id
        ))


@celery_app.task(queue='application-service-tasks')
def send_completion_reminder(application_id: uuid.UUID, reminder_type: str):
    completion_reminder_notification = Notification.objects.get(name=reminder_type)

    if not completion_reminder_notification.is_active:
        logger.info("completion_reminder notification is not active", extra=dict(
            type="completion_reminder_notification_not_active",
            application_id=application_id,
            notification_id=completion_reminder_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)
    if application.apex_partner_slug:
        NotificationStatus.objects.create(status=NotificationStatus.SUPPRESSED,
                                          application=application,
                                          notification=completion_reminder_notification,
                                          reason="Application has apex partner slug")
        return
    elif application.notificationstatus_set.filter(notification=completion_reminder_notification).count() == 0:
        if application.stage == ApplicationStage.INCOMPLETE:
            response = mailer.send_incomplete_account_notification(application.customer, application.buying_agent,
                                                                   application.build_resume_link(),
                                                                   completion_reminder_notification.name)

            if response.status_code == 200:
                NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                                  notification=completion_reminder_notification)
            else:
                logger.error("Non-success response code from send_incomplete_account_notification", extra=dict(
                    type="non_success_for_send_incomplete_account_notification_in_completion_reminder",
                    response_status_code=response.status_code,
                    response=response.json(),
                    application_id=application.id,
                ))
                NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                                  notification=completion_reminder_notification,
                                                  reason=f'hubspot returned {response.status_code}')
    else:
        logger.info("Notification send_completion_reminder already sent for application", extra=dict(
            type="completion_reminder_already_sent",
            application_id=application_id,
            completion_reminder_notification_id=completion_reminder_notification.id
        ))


@celery_app.task(queue='application-service-tasks')
def send_registered_client_notification(application_id: uuid.UUID):
    logger.info("Sending registered_client_notification", extra=dict(
        type="sending_registered_client_notification",
        application_id=application_id
    ))
    registered_client_notification = Notification.objects.get(name=Notification.AGENT_REFERRAL_CUSTOMER_WELCOME_EMAIL)

    if not registered_client_notification.is_active:
        logger.info("registered_client_notification is not active", extra=dict(
            type="registered_client_notification_not_active",
            application_id=application_id,
            registered_client_notification_id=registered_client_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)

    if application.apex_partner_slug:
        NotificationStatus.objects.create(status=NotificationStatus.SUPPRESSED,
                                          application=application,
                                          notification=registered_client_notification,
                                          reason="Application has apex partner slug")
    elif application.notificationstatus_set.filter(notification=registered_client_notification).count() == 0:
        try:
            application.pricing
        except Application.pricing.RelatedObjectDoesNotExist:
            try:
                pricing = Pricing.objects.get(questionnaire_response_id=application.questionnaire_response_id)
                pricing.application = application
                pricing.save()
            except Pricing.ObjectNotFound as e:
                logger.exception("Pricing object not found for questionnnaire response ID", extra=dict(
                    type="pricing_object_not_found_for_questionnaire_response_id",
                    questionnaire_response_id=application.questionnaire_response_id,
                    application_id=application_id
                ))
                NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                                  notification=registered_client_notification,
                                                  reason="Pricing object not found for app: {}".format(application.id))
                return

        response = mailer.send_agent_referral_welcome_email(application.customer, application.buying_agent,
                                                            application.get_pricing_url())
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=registered_client_notification)
        else:
            logger.error("Non-success response code from send_agent_referral_welcome_email", extra=dict(
                type="non_success_for_send_agent_referral_welcome_email",
                response_status_code=response.status_code,
                response=response.json(),
                application_id=application.id,
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=registered_client_notification,
                                              reason=f'hubspot returned {response.status_code}')

    else:
        logger.info("Notification send_registered_client_notification already sent for application", extra=dict(
            type="registered_client_notification_already_sent",
            application_id=application_id,
            registered_client_notification_id=registered_client_notification.id
        ))


@celery_app.task(queue='application-service-tasks')
def queue_cma_request(application_id: uuid.UUID):
    cma_request_notification = Notification.objects.get(name=Notification.CMA_REQUEST)

    if not cma_request_notification.is_active:
        logger.info("cma_request_notification is not active", extra=dict(
            type="cma_request_notification_not_active",
            application_id=application_id,
            cma_request_notification_id=cma_request_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)

    if application.is_buy_sell():
        if application.buying_agent is None \
                or not application.buying_agent.email \
                or application.current_home is None \
                or application.current_home.address is None \
                or application.current_home.address.street is None:
            raise EmailTriggerCriteriaValidationException(
                f"missing information necessary to send CMA request for application {application.id}")

        if application.notificationstatus_set.filter(notification=cma_request_notification).count() == 0:
            response = mailer.send_cma_request(application.buying_agent.email,
                                               application.buying_agent.get_first_name(),
                                               application.customer.name, application.current_home.address.street)

            if response.status_code == 200:
                NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                                  notification=cma_request_notification)
            else:
                logger.error("Non-success response code from send_cma_request", extra=dict(
                    type="non_success_for_send_cma_request",
                    response_status_code=response.status_code,
                    response=response.json(),
                    application_id=application.id,
                ))
                NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                                  notification=cma_request_notification,
                                                  reason=f'hubspot returned {response.status_code}')
        else:
            logger.info("Notification cma_request_notification already sent for application", extra=dict(
                type="cma_request_notification_already_sent",
                application_id=application_id,
                cma_request_notification_id=cma_request_notification.id
            ))


@celery_app.task(queue='application-service-tasks')
def queue_saved_quote_cta(pricing_id: uuid.UUID):
    cma_saved_quote_cta_notification = Notification.objects.get(name=Notification.SAVED_QUOTE)

    if not cma_saved_quote_cta_notification.is_active:
        logger.info("cma_request_notification is not active", extra=dict(
            type="cma_saved_quote_cta_notification_not_active",
            pricing_id=pricing_id,
            cma_saved_quote_cta_notification_id=cma_saved_quote_cta_notification.id
        ))
        return

    pricing = Pricing.objects.get(id=pricing_id)
    mailer.send_saved_quote_cta(pricing.agent.get_first_name(), pricing.agent.email,
                                pricing.get_resume_link())


@celery_app.task(queue='application-service-tasks')
def queue_new_customer_partner_email(application_id: uuid.UUID, apex_partner):
    new_customer_partner_email_notification = Notification.objects.get(name=Notification.NEW_CUSTOMER_PARTNER_EMAIL)

    if not new_customer_partner_email_notification.is_active:
        logger.info("new_customer_partner_email_notification is not active", extra=dict(
            type="new_customer_partner_email_notification_not_active",
            application_id=application_id,
            new_customer_partner_email_notification_id=new_customer_partner_email_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)
    partner_name = apex_partner.get('name')
    partner_email = apex_partner.get('partner-email')
    if partner_email is None:
        # Handle legacy weblfow typo case
        partner_email = apex_partner.get('parnter-email')
        if partner_email is None:
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=new_customer_partner_email_notification,
                                              reason='Missing partner email address')
            return
    if application.notificationstatus_set.filter(notification=new_customer_partner_email_notification,
                                                 status=NotificationStatus.SENT).count() == 0:
        if application.current_home:
            address = application.current_home.address.get_inline_address()
        else:
            address = None
        if application.home_buying_location:
            home_buying_location = application.home_buying_location.get_inline_address()
        else:
            home_buying_location = None
        response = mailer.send_new_customer_partner_email(application.customer.name,
                                                          application.customer.email,
                                                          application.customer.phone,
                                                          application.home_buying_stage,
                                                          home_buying_location,
                                                          address,
                                                          partner_name,
                                                          partner_email)
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=new_customer_partner_email_notification)
        else:
            logger.error("Non-success response code from send_new_customer_partner_email", extra=dict(
                type="non_success_for_send_new_customer_partner_email",
                response_status_code=response.status_code,
                response=response.json(),
                application_id=application.id,
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=new_customer_partner_email_notification,
                                              reason=f'hubspot returned {response.status_code}')
    else:
        logger.info("Notification new_customer_partner_email_notification already sent for application", extra=dict(
            type="new_customer_partner_email_notification_already_sent",
            application_id=application_id,
            new_customer_partner_email_notification_id=new_customer_partner_email_notification.id
        ))


@celery_app.task(queue='application-service-tasks')
def queue_apex_site_pre_account_email(application_id: uuid.UUID, apex_partner):
    apex_site_pre_account_notification = Notification.objects.get(name=Notification.APEX_SITE_PRE_ACCOUNT)

    if not apex_site_pre_account_notification.is_active:
        logger.info("apex_site_pre_account_notification is not active", extra=dict(
            type="apex_site_pre_account_notification_not_active",
            application_id=application_id,
            apex_site_pre_account_notification_id=apex_site_pre_account_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)
    partner_name = apex_partner.get('name')

    if application.notificationstatus_set.filter(notification=apex_site_pre_account_notification,
                                                 status=NotificationStatus.SENT).count() == 0:
        response = mailer.send_apex_site_pre_account_email(application.customer.email,
                                                           application.customer.get_first_name(),
                                                           partner_name,
                                                           application.build_apex_resume_link(),
                                                           application.get_buying_agent_name(),
                                                           application.get_buying_agent_email())

        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=apex_site_pre_account_notification)
        else:
            logger.error("Non-success response code from send_apex_site_pre_account_email", extra=dict(
                type="non_success_for_send_apex_site_pre_account_email",
                response_status_code=response.status_code,
                response=response.json(),
                application_id=application.id,
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=apex_site_pre_account_notification,
                                              reason=f'hubspot returned {response.status_code}')

    else:
        logger.info("Notification new_customer_partner_email_notification already sent for application", extra=dict(
            type="new_customer_partner_email_notification_already_sent",
            application_id=application_id,
            apex_site_pre_account_notification_id=apex_site_pre_account_notification.id
        ))


@celery_app.task(queue='application-service-tasks')
def queue_fast_track_resume_email(application_id: uuid.UUID):
    fast_track_resume_notification = Notification.objects.get(name=Notification.FAST_TRACK_RESUME)

    if not fast_track_resume_notification.is_active:
        logger.info("fast_track_resume_notification is not active", extra=dict(
            type="fast_track_resume_notification_not_active",
            application_id=application_id,
            fast_track_resume_notification_id=fast_track_resume_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)

    if application.apex_partner_slug:
        NotificationStatus.objects.create(status=NotificationStatus.SUPPRESSED,
                                          application=application,
                                          notification=fast_track_resume_notification,
                                          reason="Application has apex partner slug")
    elif application.buying_agent.has_name_and_email() and application.notificationstatus_set.filter(
            notification=fast_track_resume_notification).count() == 0:
        response = mailer.send_fast_track_resume_email(application.buying_agent.email, application.buying_agent.name,
                                                       application.customer.name,
                                                       application.customer.get_first_name(),
                                                       application.customer.email,
                                                       application.build_resume_link())
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=fast_track_resume_notification)
        else:
            logger.error("Non-success response code from send_fast_track_resume_email", extra=dict(
                type="non_success_for_send_fast_track_resume_email",
                response_status_code=response.status_code,
                response=response.json(),
                application_id=application.id,
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=fast_track_resume_notification,
                                              reason=f'hubspot returned {response.status_code}')
    else:
        logger.info("Notification fast_track_resume_notification already sent for application", extra=dict(
            type="fast_track_resume_notification_already_sent",
            application_id=application_id,
            fast_track_resume_notification_id=fast_track_resume_notification.id
        ))


@celery_app.task(queue='application-service-tasks')
def queue_vpal_incomplete_email(application_id: uuid.UUID):
    vpal_incomplete_notification = Notification.objects.get(name=Notification.VPAL_INCOMPLETE)

    if not vpal_incomplete_notification.is_active:
        logger.info("vpal_incomplete_notification is not active", extra=dict(
            type="vpal_incomplete_notification_not_active",
            application_id=application_id,
            vpal_incomplete_notification_id=vpal_incomplete_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)

    if application.notificationstatus_set.filter(notification=vpal_incomplete_notification,
                                                 status=NotificationStatus.SENT).count() == 0:
        response = mailer.send_vpal_incomplete_email(application.get_buying_agent_email(),
                                                     application.customer.get_first_name(),
                                                     application.customer.email,
                                                     application.customer.co_borrower_email,
                                                     application.get_approval_specialist_email(),
                                                     application.get_approval_specialist_first_name(),
                                                     application.get_approval_specialist_last_name())
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=vpal_incomplete_notification)
        else:
            logger.error("Non-success response code from send_vpal_incomplete_email", extra=dict(
                type="non_success_for_send_vpal_incomplete_email",
                response_status_code=response.status_code,
                response=response.json(),
                application_id=application.id,
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=vpal_incomplete_notification,
                                              reason=f"hubspot returned {response.status_code}")
    else:
        logger.info("Notification vpal_incomplete_notification already sent for application", extra=dict(
            type="vpal_incomplete_notification_already_sent",
            application_id=application_id,
            vpal_incomplete_notification_id=vpal_incomplete_notification.id
        ))


@celery_app.task(queue='application-service-tasks')
def queue_vpal_suspended_email(application_id: uuid.UUID):
    vpal_suspended_notification = Notification.objects.get(name=Notification.VPAL_SUSPENDED)

    if not vpal_suspended_notification.is_active:
        logger.info("vpal_suspended_notification is not active", extra=dict(
            type="vpal_suspended_notification_not_active",
            application_id=application_id,
            vpal_suspended_notification_id=vpal_suspended_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)

    if application.notificationstatus_set.filter(notification=vpal_suspended_notification,
                                                 status=NotificationStatus.SENT).count() == 0:
        cc_email_list = [application.get_buying_agent_email(), application.customer.co_borrower_email]
        loan_advisor = application.loan_advisor
        if loan_advisor:
            response = mailer.send_vpal_suspended_email(application.customer.email,
                                                        application.customer.get_first_name(),
                                                        cc_email_list,
                                                        loan_advisor.first_name,
                                                        loan_advisor.last_name,
                                                        loan_advisor.schedule_a_call_url,
                                                        loan_advisor.phone,
                                                        loan_advisor.email,
                                                        application.get_approval_specialist_email(),
                                                        application.get_approval_specialist_first_name(),
                                                        application.get_approval_specialist_last_name())
        else:
            response = mailer.send_vpal_suspended_email(application.customer.email,
                                                        application.customer.get_first_name(),
                                                        cc_email_list,
                                                        application.get_approval_specialist_email(),
                                                        application.get_approval_specialist_first_name(),
                                                        application.get_approval_specialist_last_name())
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=vpal_suspended_notification)
        else:
            logger.error("Non-success response code from send_vpal_suspended_email", extra=dict(
                type="non_success_for_send_vpal_suspended_email",
                response_status_code=response.status_code,
                response=response.json(),
                application_id=application.id,
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=vpal_suspended_notification,
                                              reason=f"hubspot returned {response.status_code}")
    else:
        logger.info("Notification vpal_suspended_notification already sent for application", extra=dict(
            type="vpal_suspended_notification_already_sent",
            application_id=application_id,
            vpal_suspended_notification_id=vpal_suspended_notification.id
        ))


@celery_app.task(queue='application-service-tasks')
def queue_vpal_ready_for_review_email(application_id: uuid.UUID):
    vpal_ready_for_review_notification = Notification.objects.get(name=Notification.VPAL_READY_FOR_REVIEW)

    if not vpal_ready_for_review_notification.is_active:
        logger.info("vpal_ready_for_review_notification is not active", extra=dict(
            type="vpal_ready_for_review_notification_not_active",
            application_id=application_id,
            vpal_ready_for_review_notification_id=vpal_ready_for_review_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)

    if application.notificationstatus_set.filter(notification=vpal_ready_for_review_notification,
                                                 status=NotificationStatus.SENT).count() == 0:

        response = mailer.send_vpal_ready_for_review_email(application.customer.get_first_name(),
                                                           application.customer.email,
                                                           application.customer.co_borrower_email,
                                                           application.get_buying_agent_email(),
                                                           application.get_approval_specialist_email(),
                                                           application.get_approval_specialist_first_name(),
                                                           application.get_approval_specialist_last_name())
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=vpal_ready_for_review_notification)
        else:
            logger.error("Non-success response code from send_vpal_ready_for_review_email", extra=dict(
                type="non_success_for_send_vpal_ready_for_review_email",
                response_status_code=response.status_code,
                response=response.json(),
                application_id=application.id,
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=vpal_ready_for_review_notification,
                                              reason=f"hubspot returned {response.status_code}")
    else:
        logger.info("Notification vpal_ready_for_review_notification already sent for application", extra=dict(
            type="vpal_ready_for_review_notification_already_sent",
            application_id=application_id,
            vpal_ready_for_review_notification_id=vpal_ready_for_review_notification.id
        ))

@celery_app.task(queue='application-service-tasks')
def queue_application_complete_email(application_id: uuid.UUID):

    application_complete_notification = Notification.objects.get(name=Notification.APPLICATION_COMPLETE)
    
    if not application_complete_notification.is_active:
        logger.info("application_complete_notification is not active", extra=dict(
            type="active",
            application_id=application_id,
            application_complete_notification_id=application_complete_notification.id
        ))
        return
    
    application = Application.objects.get(id=application_id)
    
    if application.notificationstatus_set.filter(notification=application_complete_notification,
                                                 status=NotificationStatus.SENT).count() == 0:
        response = mailer.send_application_complete_email(application.customer.email, 
                                                          application.customer.get_first_name(), 
                                                          application.get_buying_agent_email(), 
                                                          application.get_approval_specialist_first_name(), 
                                                          application.get_approval_specialist_last_name(), 
                                                          application.get_approval_specialist_email(), 
                                                          application.get_loan_advisor_first_name(), 
                                                          application.get_loan_advisor_last_name())
        
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=application_complete_notification)
        else:
            logger.error("Non-success response code from application_complete_notification", extra=dict(
                type="non_success_for_send_application_complete_email",
                response_status_code=response.status_code,
                response=response.json(),
                application_id=application.id,
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=application_complete_notification,
                                              reason=f"hubspot returned {response.status_code}")
    else:
        logger.info("Notification application_complete_notification already sent for application", extra=dict(
            type="application_complete_notification_already_sent",
            application_id=application_id,
            application_complete_notification_id=application_complete_notification.id
        ))
    

@periodic_task(run_every=timedelta(hours=24), options={'queue': 'application-service-tasks'})
def send_pre_homeward_close_email():
    pre_homeward_close_notification = Notification.objects.get(name=Notification.PRE_HOMEWARD_CLOSE)

    if not pre_homeward_close_notification.is_active:
        logger.info("pre_homeward_close_notification is not active", extra=dict(
            type="pre_homeward_close_notification_not_active",
            pre_homeward_close_notification_id=pre_homeward_close_notification.id
        ))
        return

    applications = Application.objects.filter(
        new_home_purchase__homeward_purchase_close_date__lte=datetime.now() + timedelta(days=5),
        stage__in=[ApplicationStage.OPTION_PERIOD, ApplicationStage.POST_OPTION]).exclude(
        id__in=Application.objects.filter(notificationstatus__notification=pre_homeward_close_notification,
                                          notificationstatus__status=NotificationStatus.SENT))

    for application in applications:
        if application.new_home_purchase is None \
                or application.new_home_purchase.rent is None \
                or application.new_home_purchase.rent.type is None \
                or application.new_home_purchase.rent.amount_months_one_and_two is None:
            logger.error(f"Missing data to send pre-homeward close email for application {application.id}", extra=dict(
                type="missing_data_prehomeward_close_email",
                application_id=application.id,
                new_home_purchase_obj=application.new_home_purchase.__dict__
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT,
                                              application=application,
                                              notification=pre_homeward_close_notification,
                                              reason=f"missing new_home_purchase data")

        elif application.new_home_purchase.is_reassigned_contract:
            NotificationStatus.objects.get_or_create(status=NotificationStatus.SUPPRESSED, application=application,
                                                     notification=pre_homeward_close_notification,
                                                     reason="Application is reassigned contract")
        else:
            cc_email_list = application.generate_cc_emails_list()
            try:
                response = mailer.send_pre_homeward_close(application.customer, application.new_home_purchase,
                                                          cc_email_list, application.homeward_owner_email)
                if response.status_code == 200:
                    NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                                      notification=pre_homeward_close_notification)
                else:
                    logger.error("Non-success response code from send_pre_homeward_close", extra=dict(
                        type="non_success_for_send_pre_homeward_close",
                        response_status_code=response.status_code,
                        application_id=application.id,
                        response=response.json()
                    ))
                    NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                                      notification=pre_homeward_close_notification,
                                                      reason=f"hubspot returned {response.status_code}")
            except Exception as e:
                logger.exception(f"Unable to send pre-homeward close email for application {application.id}",
                                 exc_info=e,
                                 extra=dict(type="unable_to_send_prehomeward_close_email",
                                            application_id=application.id))


@periodic_task(run_every=timedelta(hours=24), options={'queue': 'application-service-tasks'})
def send_agent_pre_customer_close_email():
    pre_customer_close_agent_notification = Notification.objects.get(name=Notification.AGENT_PRE_CUSTOMER_CLOSE)

    if not pre_customer_close_agent_notification.is_active:
        logger.info("pre_customer_close_agent_notification is not active", extra=dict(
            type="pre_customer_close_agent_notification_not_active",
            pre_customer_close_agent_notification_id=pre_customer_close_agent_notification.id
        ))
        return

    applications = Application.objects.filter(
        new_home_purchase__customer_purchase_close_date__lte=datetime.now() + timedelta(days=7),
        stage=ApplicationStage.HOMEWARD_PURCHASE).exclude(
        id__in=Application.objects.filter(notificationstatus__notification=pre_customer_close_agent_notification,
                                          notificationstatus__status=NotificationStatus.SENT))

    for application in applications:
        if application.new_home_purchase is None \
                or application.new_home_purchase.address is None \
                or application.new_home_purchase.address.street is None \
                or application.new_home_purchase.customer_purchase_close_date is None \
                or application.buying_agent is None \
                or application.buying_agent.email is None:
            logger.error(
                f"Missing data to send agent pre-customer close email for application {application.id}", extra=dict(
                    type="missing_data_agent_prehomeward_close_email",
                    application_id=application.id,
                    data=dict(
                        new_home_purchase=application.new_home_purchase.__dict__ if application.new_home_purchase else None,
                        buying_agent=application.buying_agent.__dict__ if application.buying_agent else None,
                    )
                ))
        elif application.new_home_purchase.is_reassigned_contract:
            NotificationStatus.objects.get_or_create(status=NotificationStatus.SUPPRESSED, application=application,
                                                     notification=pre_customer_close_agent_notification,
                                                     reason="Application is reassigned contract")
        else:
            close_date_str = application.new_home_purchase.customer_purchase_close_date.strftime("%-m/%-d/%Y")
            tc_email = application.get_transaction_coordinator_email()
            try:
                response = \
                    mailer.send_agent_pre_customer_close(application.customer.name,
                                                         application.buying_agent.get_first_name(),
                                                         application.buying_agent.email,
                                                         application.new_home_purchase.address.street,
                                                         close_date_str,
                                                         application.homeward_owner_email,
                                                         tc_email)
                if response.status_code == 200:
                    NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                                      notification=pre_customer_close_agent_notification)
                else:
                    logger.error("Non-success response code from send_agent_pre_customer_close", extra=dict(
                        type="non_success_for_send_agent_pre_customer_close",
                        response_status_code=response.status_code,
                        application_id=application.id,
                        response=response.json()
                    ))
                    NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                                      notification=pre_customer_close_agent_notification,
                                                      reason=f"hubspot returned {response.status_code}")
            except Exception:
                logger.error(f"Unable to send agent pre-customer close email for application {application.id}",
                             extra=dict(
                                 type="unable_to_send_agent_precustomer_close_email",
                                 application_id=application.id,
                                 pre_customer_close_agent_notification_id=pre_customer_close_agent_notification.id
                             ))


@periodic_task(run_every=timedelta(hours=24), options={'queue': 'application-service-tasks'})
def send_pre_customer_close_email():
    pre_customer_close_notification = Notification.objects.get(name=Notification.PRE_CUSTOMER_CLOSE)

    if not pre_customer_close_notification.is_active:
        logger.info("pre_customer_close_notification is not active", extra=dict(
            type="pre_customer_close_notification_not_active",
            pre_customer_close_notification_id=pre_customer_close_notification.id
        ))
        return

    applications = \
        Application.objects.filter(
            new_home_purchase__customer_purchase_close_date__lte=datetime.now() + timedelta(days=7),
            stage=ApplicationStage.HOMEWARD_PURCHASE).exclude(id__in=Application.objects.filter(
            notificationstatus__notification=pre_customer_close_notification,
            notificationstatus__status=NotificationStatus.SENT))

    for application in applications:
        if application.new_home_purchase is None \
                or application.new_home_purchase.customer_purchase_close_date is None \
                or application.cx_manager is None \
                or application.cx_manager.email is None \
                or application.cx_manager.first_name is None \
                or application.cx_manager.last_name is None \
                or application.cx_manager.schedule_a_call_url is None:
            logger.error(
                f"Missing data to send pre-customer close email for application {application.id}", extra=dict(
                    type="missing_data_prehomeward_customer_close_email",
                    application_id=application.id,
                    data=dict(
                        new_home_purchase_customer_purchase_close_date=application.new_home_purchase.customer_purchase_close_date,
                        cx_manager=application.cx_manager,
                        cx_manager_email=application.cx_manager.email,
                        cx_manager_first_name=application.cx_manager.first_name,
                        cx_manager_last_name=application.cx_manager.last_name,
                        cx_manager_call_url=application.cx_manager.schedule_a_call_url
                    )
                ))
        elif application.new_home_purchase.is_reassigned_contract:
            NotificationStatus.objects.get_or_create(status=NotificationStatus.SUPPRESSED, application=application,
                                                     notification=pre_customer_close_notification,
                                                     reason="Application is reassigned contract")
        else:
            try:
                cc_email_list = application.generate_cc_emails_list()
                response = mailer.send_pre_customer_close(application.customer, application.new_home_purchase,
                                                          cc_email_list,
                                                          application.cx_manager, application.homeward_owner_email)
                if response.status_code == 200:
                    NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                                      notification=pre_customer_close_notification)
                else:
                    logger.error("Non-success response code from send_pre_customer_close", extra=dict(
                        type="non_success_for_send_pre_customer_close",
                        response_status_code=response.status_code,
                        application_id=application.id,
                        response=response.json()
                    ))
                    NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                                      notification=pre_customer_close_notification,
                                                      reason=f"hubspot returned {response.status_code}")
            except Exception as e:
                logger.exception(f"Unable to send customer close email for application {application.id}", exc_info=e,
                                 extra=dict(
                                     type="unable_to_send_customer_close_email",
                                     application_id=application.id,
                                     pre_customer_close_agent_notification_id=pre_customer_close_notification.id
                                 ))


@periodic_task(run_every=timedelta(hours=24), options={'queue': 'application-service-tasks'})
def send_expiring_approval_email():
    expiring_approval_notification = Notification.objects.get(name=Notification.EXPIRING_APPROVAL)

    if not expiring_approval_notification.is_active:
        logger.info("expiring_approval_notification is not active", extra=dict(
            type="expiring_approval_notification_not_active",
            expiring_approval_notification_id=expiring_approval_notification.id
        ))
        return

    applications = Application.objects.filter(stage=ApplicationStage.APPROVED,
                                              preapproval__vpal_approval_date__lte=datetime.now() - timedelta(
                                                  days=50)).exclude(
        notificationstatus__notification=expiring_approval_notification)

    for application in applications:
        if application.buying_agent is None or application.buying_agent.email is None:
            logger.error(
                f"Missing buying agent email to send agent expiring-approval email for application {application.id}",
                extra=dict(
                    type="missing_info_to_send_agent_expiring_approval_email",
                    application_id=application.id,
                    buying_agent=application.buying_agent.__dict__ if application.buying_agent else None
                ))
        else:
            try:
                response = mailer.send_expiring_approval_email(application.customer.email,
                                                               application.customer.get_first_name(),
                                                               application.buying_agent.email,
                                                               application.homeward_owner_email)
                if response.status_code == 200:
                    NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                                      notification=expiring_approval_notification)
                else:
                    logger.error("Non-success response code from send_expiring_approval_email", extra=dict(
                        type="non_success_for_send_expiring_approval_email",
                        response_status_code=response.status_code,
                        application_id=application.id,
                        response=response.json()
                    ))
                    NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                                      notification=expiring_approval_notification,
                                                      reason=f"hubspot returned {response.status_code}")
            except Exception as e:
                logger.exception(f"Unable to send expiration email for application {application.id}", exc_info=e,
                                 extra=dict(
                                     type="unable_to_send_customer_close_email",
                                     application_id=application.id,
                                     expiring_approval_notification_id=expiring_approval_notification.id
                                 ))
    return


@periodic_task(run_every=timedelta(hours=24), options={'queue': 'application-service-tasks'})
def send_incomplete_application_reminders():
    # grab all incomplete apps from the last week
    applications = Application.objects.filter(stage=ApplicationStage.INCOMPLETE,
                                              created_at__gte=timezone.now() - timedelta(days=8))

    for application in applications:
        notification_type = None
        # day old apps
        if timezone.now() - timedelta(days=2) <= application.created_at <= timezone.now() - timedelta(days=1):
            if application.is_agent_registered_client() and not application.user_exists_for_application():  # pre account and agent registered
                notification_type = Notification.PRE_ACCOUNT_ONE_DAY_REMINDER
            else:
                notification_type = Notification.ONE_DAY_REMINDER
        # 3 day old apps
        elif timezone.now() - timedelta(days=4) <= application.created_at <= timezone.now() - timedelta(
                days=3):
            if application.is_agent_registered_client() and not application.user_exists_for_application():  # pre account and agent registered
                notification_type = Notification.PRE_ACCOUNT_THREE_DAY_REMINDER
            else:
                notification_type = Notification.THREE_DAY_REMINDER
        # week old apps
        elif timezone.now() - timedelta(days=8) <= application.created_at <= timezone.now() - timedelta(
                days=7):
            notification_type = Notification.WEEK_REMINDER

        if notification_type:
            notification = Notification.objects.get(name=notification_type)

            if not notification.is_active:
                logger.info(f"Notification {notification_type} is not active", extra=dict(
                    type="incomplete_application_reminder_notitication_not_active",
                    notification_id=notification.id,
                    notification_type=notification_type,
                    application_id=application.id
                ))
                return

            if application.apex_partner_slug:
                NotificationStatus.objects.create(status=NotificationStatus.SUPPRESSED,
                                                  application=application,
                                                  notification=notification,
                                                  reason="Application has apex partner slug")
            elif application.notificationstatus_set.filter(notification=notification).count() == 0:
                response = mailer.send_incomplete_account_notification(application.customer, application.buying_agent,
                                                                       application.get_cta_link(), notification.name)
                if response.status_code == 200:
                    NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                                      notification=notification)
                else:
                    logger.error("Non-success response code from send_incomplete_account_notification", extra=dict(
                        type="non_success_for_send_incomplete_account_notification_incomplete_application_reminders",
                        response_status_code=response.status_code,
                        notification_name=notification.name,
                        notification_id=notification.id,
                        application_id=application.id,
                        response=response.json()
                    ))
                    NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                                      notification=notification,
                                                      reason=f"hubspot returned {response.status_code}")


@periodic_task(run_every=timedelta(hours=1), options={'queue': 'application-service-tasks'})
def send_incomplete_agent_referral_reminders():
    incomplete_agent_referral_notification = Notification.objects.get(name=Notification.INCOMPLETE_REFERRAL)

    if not incomplete_agent_referral_notification.is_active:
        logger.info(f"incomplete_agent_referral_notification is not active", extra=dict(
            type="incomplete_agent_referral_notification_not_active",
            incomplete_agent_referral_notification_id=incomplete_agent_referral_notification.id,
        ))
        return

    for pricing in Pricing.objects.filter(created_at__gte=timezone.now() - timedelta(hours=2),
                                          created_at__lte=timezone.now() - timedelta(hours=1),
                                          application_id__isnull=True):
        try:
            response = mailer.send_incomplete_agent_referral_reminder(
                pricing.agent.email,
                pricing.agent.get_first_name(),
                pricing.get_resume_link())
        except Exception as e:
            logger.exception("Exception raised while sending incomplete_agent_referral_reminder", exc_info=e,
                             extra=dict(
                                 type="exception_during_send_incomplete_agent_referral_reminder",
                             ))
        else:
            if response.status_code != 200:
                logger.error("Non-success response code from send_incomplete_agent_referral_reminder", extra=dict(
                    type="non_success_for_send_incomplete_agent_referral_reminder",
                    incomplete_agent_referral_notification_id=incomplete_agent_referral_notification.id,
                    pricing_id=pricing.id,
                    response=response.json()
                ))


@periodic_task(run_every=timedelta(hours=24), options={'queue': 'application-service-tasks'})
def send_vpal_ready_for_review_follow_up():
    vpal_ready_for_review_notification = Notification.objects.get(name=Notification.VPAL_READY_FOR_REVIEW_FOLLOW_UP)

    if not vpal_ready_for_review_notification.is_active:
        logger.info(
            f"method=send_vpal_ready_for_review_follow_up action=email_not_active notification_id={vpal_ready_for_review_notification.id}")
        logger.info(f"vpal_ready_for_review_notification is not active", extra=dict(
            type="vpal_ready_for_review_notification_not_active",
            incomplete_agent_referral_notification_id=vpal_ready_for_review_notification.id,
        ))
        return

    applications = Application.objects.filter(stage=ApplicationStage.QUALIFIED_APPLICATION,
                                              mortgage_status=MortgageStatus.VPAL_READY_FOR_REVIEW)  # grab all vpal ready for review apps

    vpal_original_notification = Notification.objects.get(name=Notification.VPAL_READY_FOR_REVIEW)
    time_threshold = timezone.now() - timedelta(hours=72)

    for application in applications:
        if application.notificationstatus_set.filter(
                notification__in=[vpal_original_notification, vpal_ready_for_review_notification],
                status=NotificationStatus.SENT, created_at__gt=time_threshold).count() > 0:
            logger.info("Notification vpal_ready_for_review_notification already sent for application", extra=dict(
                type="vpal_ready_for_review_notification_already_sent_within_72hrs",
                vpal_ready_for_review_notification_id=vpal_ready_for_review_notification.id,
                application_id=application.id
            ))
            continue

        response = mailer.send_vpal_ready_for_review_follow_up(application.customer.get_first_name(),
                                                               application.customer.get_last_name(),
                                                               application.customer.email,
                                                               application.customer.co_borrower_email,
                                                               application.get_buying_agent_email())
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=vpal_ready_for_review_notification)
        else:
            logger.error("Non-success response code from send_vpal_ready_for_review_follow_up", extra=dict(
                type="non_success_for_send_vpal_ready_for_review_follow_up",
                response_status_code=response.status_code,
                vpal_ready_for_review_notification_id=vpal_ready_for_review_notification.id,
                application_id=application.id,
                response=response.json()
            ))
            NotificationStatus.objects.create(status=NotificationStatus.NOT_SENT, application=application,
                                              notification=vpal_ready_for_review_notification,
                                              reason=f"hubspot returned {response.status_code}")
    

