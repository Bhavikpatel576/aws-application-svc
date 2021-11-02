import logging
from application.email_trigger_tasks import queue_photo_task_complete_notification
from application.models.task_progress import TaskProgress
from application.models.task_category import TaskCategory
from application.models.task_status import TaskStatus

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from application.email_trigger_tasks import (queue_agent_customer_close_email,
                                             queue_agent_instructions_email,
                                             queue_apex_site_pre_account_email,
                                             queue_approval_email,
                                             queue_cma_request,
                                             queue_customer_close_email,
                                             queue_fast_track_resume_email,
                                             queue_homeward_close_email,
                                             queue_new_customer_partner_email,
                                             queue_offer_accepted_email,
                                             queue_offer_submitted_email,
                                             queue_offer_submitted_agent_email,
                                             queue_unacknowledged_service_agreement_email,
                                             queue_saved_quote_cta,
                                             queue_under_review_email,
                                             queue_vpal_incomplete_email,
                                             queue_vpal_ready_for_review_email,
                                             queue_vpal_suspended_email,
                                             send_completion_reminder,
                                             queue_purchase_price_updated_email,
                                             queue_application_complete_email)
from application.application_acknowledgements import create_service_agreement
from application.models.acknowledgement import Acknowledgement
from application.models.application import (FAST_TRACK_REGISTRATION,
                                            ApplicationStage, LeadStatus,
                                            MortgageStatus)
from application.models.disclosure import DisclosureType
from application.models.models import Application, StageHistory
from application.models.offer import Offer, OfferStatus
from application.models.preapproval import PreApproval
from application.models.pricing import Pricing
from application.tasks import push_homeward_user_to_salesforce, push_to_salesforce
from application.task_operations import run_task_operations
from utils.partner_branding_config_service import get_partner
from user.models import User
from utils.hubspot import Notification

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Application)
def create_stage_history(instance, **kwargs):
    if instance._state.adding:
        return
    original_application = Application.objects.get(pk=instance.id)
    if original_application.stage != instance.stage:
        StageHistory.objects.create(application=instance, previous_stage=original_application.stage,
                                    new_stage=instance.stage)


@receiver(post_save, sender=Application)
def update_stage_when_all_tasks_are_complete(instance, **kwargs):
    if instance._state.adding:
        return
    original_application = Application.objects.get(pk=instance.id)
    if original_application.stage == ApplicationStage.INCOMPLETE and original_application.are_all_tasks_complete():
        instance.stage = ApplicationStage.COMPLETE


@receiver(pre_save, sender=Application)
def send_emails_when_application_stage_changes(instance, **kwargs):
    if instance._state.adding:
        return
    original_application = Application.objects.get(pk=instance.id)
    if original_application.stage != instance.stage:
        if instance.stage == ApplicationStage.APPROVED:
            queue_approval_email.delay(instance.id)
            queue_agent_instructions_email.delay(instance.id)
        if instance.stage == ApplicationStage.QUALIFIED_APPLICATION:
            queue_under_review_email.delay(instance.id)
        elif instance.stage == ApplicationStage.OPTION_PERIOD:
            queue_offer_accepted_email.delay(instance.id)
        elif instance.stage == ApplicationStage.HOMEWARD_PURCHASE:
            queue_homeward_close_email.delay(instance.id)
        elif instance.stage == ApplicationStage.CUSTOMER_CLOSED:
            queue_customer_close_email.delay(instance.id)
            queue_agent_customer_close_email.delay(instance.id)


@receiver(post_save, sender=Acknowledgement)
def push_app_to_salesforce_when_service_agreement_complete(instance, **kwargs):
    acknowledgement = Acknowledgement.objects.get(pk=instance.id)
    if acknowledgement.disclosure.disclosure_type == DisclosureType.SERVICE_AGREEMENT\
            and acknowledgement.is_acknowledged:
        push_to_salesforce(acknowledgement.application.id)


@receiver(pre_save, sender=Application)
def add_service_agreement_when_application_stage_changes(instance, **kwargs):
    if instance._state.adding:
        return

    original_application = Application.objects.get(pk=instance.id)

    current_stages = [ApplicationStage.OPTION_PERIOD,
                      ApplicationStage.POST_OPTION,
                      ApplicationStage.HOMEWARD_PURCHASE,
                      ApplicationStage.CUSTOMER_CLOSED,
                      ApplicationStage.CANCELLED_CONTRACT,
                      ApplicationStage.TRASH]

    updated_stages = [ApplicationStage.INCOMPLETE,
                      ApplicationStage.COMPLETE,
                      ApplicationStage.QUALIFIED_APPLICATION,
                      ApplicationStage.FLOOR_PRICE_REQUESTED,
                      ApplicationStage.FLOOR_PRICE_COMPLETED,
                      ApplicationStage.APPROVED,
                      ApplicationStage.DENIED,
                      ApplicationStage.OFFER_REQUESTED,
                      ApplicationStage.OFFER_SUBMITTED]

    if original_application.stage in current_stages\
            and instance.stage in updated_stages:
        buying_state = instance.get_purchasing_state()
        if buying_state:
            buying_state = buying_state.lower()
        else:
            logger.error("No state found for application", extra=dict(
                type="no_state_found_for_application",
                instance_id=instance.id
            ))
            return

        buying_agent_brokerage = instance.get_buying_agent_brokerage_name()

        create_service_agreement(instance, buying_state, buying_agent_brokerage)
        run_task_operations(instance)

@receiver(post_save, sender=Application)
def send_email_when_application_complete(instance: Application, **kwargs):
    if instance._state.adding:
        return

    if 'stage' in instance.diff or 'approval_specialist' in instance.diff:
        if instance.stage == ApplicationStage.COMPLETE and instance.approval_specialist is not None:
            queue_application_complete_email.delay(instance.id)


@receiver(pre_save, sender=Offer)
def send_emails_when_offer_stage_changes(instance, **kwargs):
    if instance._state.adding:
        return
    original_offer = Offer.objects.get(pk=instance.id)
    if original_offer.status != instance.status:
        if instance.status == OfferStatus.APPROVED:
            queue_offer_submitted_agent_email.delay(instance.id)
        if instance.status == OfferStatus.REQUESTED:
            offer_price = int(instance.offer_price) if instance.offer_price else 0
            queue_offer_submitted_email.delay(instance.id, offer_price)


@receiver(pre_save, sender=PreApproval)
def send_emails_when_preapproval_amount_changes(instance, **kwargs):
    if instance._state.adding:
        return

    original_preapproval = PreApproval.objects.get(pk=instance.id)
    try:
        application = Application.objects.get(preapproval_id=instance.id)
    except Application.DoesNotExist as e:
        logger.exception(f"Application not found for preapproval {instance.id}", exc_info=e, extra=dict(
            type="application_not_found_for_preapproval",
            original_preapproval_id=original_preapproval.id,
            instance_id=instance.id
        ))
        return

    if application.stage not in [ApplicationStage.APPROVED, ApplicationStage.OFFER_REQUESTED,
                                 ApplicationStage.OFFER_SUBMITTED]:
        return

    if original_preapproval.amount != instance.amount \
            and original_preapproval.amount < instance.amount:
        amount = int(instance.amount) if instance.amount else 0
        queue_purchase_price_updated_email.delay(instance.id, amount)


@receiver(pre_save, sender=Offer)
def send_email_when_unacknowledged_service_agreement(instance, **kwargs):
    if instance._state.adding:
        if instance.status == OfferStatus.REQUESTED and not instance.application.new_service_agreement_acknowledged_date:
            queue_unacknowledged_service_agreement_email.delay(instance.application.id)
    else:
        original_offer = Offer.objects.get(pk=instance.id)
        if original_offer.status != instance.status:
            if instance.status == OfferStatus.REQUESTED and not instance.application.new_service_agreement_acknowledged_date:
                queue_unacknowledged_service_agreement_email.delay(instance.application.id)


@receiver(pre_save, sender=Application)
def send_emails_when_mortgage_status_changes(instance, **kwargs):
    if instance._state.adding:
        return
    if instance.stage == ApplicationStage.QUALIFIED_APPLICATION:
        original_application: Application = Application.objects.get(pk=instance.id)
        if original_application.mortgage_status != instance.mortgage_status:
            if instance.mortgage_status == MortgageStatus.VPAL_APP_INCOMPLETE:
                queue_vpal_incomplete_email.delay(instance.id)
            elif instance.mortgage_status == MortgageStatus.VPAL_SUSPENDED:
                queue_vpal_suspended_email.delay(instance.id)
            elif instance.mortgage_status == MortgageStatus.VPAL_READY_FOR_REVIEW:
                queue_vpal_ready_for_review_email.delay(instance.id)


@receiver(post_save, sender=User)
def queue_incomplete_reminder_email(instance, created, **kwargs):
    if created:
        try:
            app = Application.objects.get(customer__email=instance.email)
        except Application.DoesNotExist as e:
            logger.exception("Application DNE for incomplete reminder email", exc_info=e, extra=dict(
                type="no_application_for_application_incomplete_reminder_email",
                customer_email=instance.email,
                instance_id=instance.id
            ))
            return
        send_completion_reminder.apply_async(kwargs=
                                             {
                                                 "application_id": app.id,
                                                 "reminder_type": Notification.FORTY_FIVE_MIN_REMINDER
                                             }, countdown=2700)  # run incomplete app check in 45 min


@receiver(post_save, sender=User)
def sync_user_to_sf(instance, **kwargs):
    push_homeward_user_to_salesforce.delay(instance.id)


@receiver(post_save, sender=Application)
def send_apex_site_pre_account_emails(instance, **kwargs):
    if instance.apex_partner_slug:
        apex_partner = get_partner(instance.apex_partner_slug)
        queue_new_customer_partner_email.delay(instance.id, apex_partner)
        queue_apex_site_pre_account_email.delay(instance.id, apex_partner)


@receiver(post_save, sender=Application)
def send_cma_request_when_agent_added(instance: Application, **kwargs):
    if instance._state.adding:
        return

    if instance.buying_agent is None:
        return
    elif instance.lead_status in [LeadStatus.NURTURE, LeadStatus.QUALIFIED] \
            and instance.stage in ApplicationStage.PRE_APPROVAL_STAGES:
        queue_cma_request.delay(instance.id)


@receiver(post_save, sender=Application)
def send_fast_track_resume_email(instance: Application, created, **kwargs):
    if created and instance.internal_referral_detail is FAST_TRACK_REGISTRATION:
        queue_fast_track_resume_email.delay(instance.id)


@receiver(pre_save, sender=Pricing)
def send_pricing_action_emails(instance: Pricing, **kwargs):
    if instance._state.adding:
        return
    original_actions = Pricing.objects.get(id=instance.id).actions
    new_actions = instance.actions.copy()
    if "saved" in set(new_actions) - set(original_actions):
        queue_saved_quote_cta.delay(instance.id)

@receiver(pre_save, sender=TaskStatus)
def send_task_status_update_emails(instance: TaskStatus, **kwargs):
    if instance._state.adding:
        return
    if instance.task_obj.category == TaskCategory.PHOTO_UPLOAD and instance.application.current_home:
        original_task_status = TaskStatus.objects.get(pk=instance.id)
        if instance.status != original_task_status.status and \
           instance.status == TaskProgress.COMPLETED:
            queue_photo_task_complete_notification.apply_async(args=[instance.application.current_home.id], countdown=300)

@receiver(post_save, sender=TaskStatus)
def update_application_stage_if_all_tasks_complete(instance: TaskStatus, **kwargs):
    if instance._state.adding:
        return

    task_application = Application.objects.get(pk=instance.application.id)
    if task_application.stage == ApplicationStage.INCOMPLETE and task_application.are_all_tasks_complete():
        task_application.stage = ApplicationStage.COMPLETE
        task_application.save()
        push_to_salesforce(task_application.id)



    