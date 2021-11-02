from django.db import models

from utils.models import CustomBaseModelMixin


class InternalSupportUser(CustomBaseModelMixin,):
    # Salesforce Fields
    USER_EMAIL = 'Email'
    USER_FIRST_NAME = 'FirstName'
    USER_LAST_NAME = 'LastName'
    USER_PHONE = 'Phone'
    USER_PHOTO_URL = 'S3_Photo_Url__c'
    USER_BIO = 'Bio__c'
    USER_SCHEDULE_A_CALL_URL = 'Hubspot_Calendar_Link__c'
    USER_PROFILE_NAME = 'Profile_Name__c'
    ID_FIELD = 'Id'
    OWNER_ID_FIELD: str = 'OwnerId'   # Owning User identifier on the SF Customer Payload
    LOAN_ADVISOR_ID_FIELD: str = 'Loan_Advisor__c'  # Loan Advisor User identifier on the SF Customer Payload

    # Model Fields
    sf_id = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    photo_url = models.URLField()
    bio = models.TextField(max_length=1000, blank=True, null=True)
    schedule_a_call_url = models.URLField(default='https://meetings.hubspot.com/homeward/homeward-intro-call')
