from enum import Enum

from django.db import models

from utils.models import CustomBaseModelMixin


class NotificationType(str, Enum):
    EMAIL = 'email'


class Notification(CustomBaseModelMixin):
    APPLICATION_UNDER_REVIEW = 'application under review'
    APPLICATION_COMPLETE = 'application complete'
    APPROVAL = 'approval'
    HW_MORTGAGE_CANDIDATE_APPROVAL = 'homeward mortgage candidiate approval'
    AGENT_OFFER_INSTRUCTIONS = 'agent offer instructions'
    OFFER_SUBMITTED = 'offer submitted'
    OFFER_SUBMITTED_AGENT = 'offer submitted agent'
    OFFER_ACCEPTED = 'offer accepted'
    PRE_HOMEWARD_CLOSE = 'pre-homeward close'
    HOMEWARD_CLOSE = 'homeward close'
    PRE_CUSTOMER_CLOSE = 'pre-customer close'
    AGENT_PRE_CUSTOMER_CLOSE = 'agent pre-customer close'
    EXPIRING_APPROVAL = 'expiring approval'
    CUSTOMER_CLOSE = 'customer close'
    AGENT_CUSTOMER_CLOSE = 'agent customer close'
    PRE_ACCOUNT_ONE_DAY_REMINDER = "pre account one day reminder"
    PRE_ACCOUNT_THREE_DAY_REMINDER = "pre account three day reminder"
    ONE_DAY_REMINDER = "one day reminder"
    THREE_DAY_REMINDER = "three day reminder"
    WEEK_REMINDER = "week reminder"
    FORTY_FIVE_MIN_REMINDER = "forty five min reminder"
    AGENT_REFERRAL_CUSTOMER_WELCOME_EMAIL = "agent referral welcome email"
    AGENT_REFERRAL_COMPLETE_EMAIL = "agent referral complete"
    CMA_REQUEST = 'agent cma request'
    PHOTO_UPLOAD = 'photo upload'
    REFERRAL_SIGN_UP = 'referral sign-up'
    CX_MESSAGE = 'cx message'
    INCOMPLETE_REFERRAL = 'incomplete referral'
    SAVED_QUOTE = 'saved quote'
    FAST_TRACK_RESUME = 'fast track resume'
    VPAL_INCOMPLETE = 'VPAL Incomplete'
    VPAL_SUSPENDED = 'VPAL Suspended'
    VPAL_READY_FOR_REVIEW = 'VPAL Ready for Review'
    APEX_SITE_PRE_ACCOUNT = 'apex site pre account'
    VPAL_READY_FOR_REVIEW_FOLLOW_UP = 'VPAL Ready for Review Follow up'
    NEW_CUSTOMER_PARTNER_EMAIL = 'new customer partner email'
    OFFER_REQUESTED_UNACKNOWLEDGED_SERVICE_AGREEMENT = 'offer requested unacknowledged service agreement'
    PURCHASE_PRICE_UPDATED = 'purchase price updated'

    name = models.CharField(max_length=50)
    type = models.CharField(max_length=50)
    template_id = models.CharField(null=True, blank=True, max_length=50)
    is_active = models.BooleanField(default=False)
