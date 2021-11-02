from enum import Enum

from django.contrib.auth import get_user_model
from django.db import models

from application.models.address import Address
from application.models.application import Application, ApplicationStage
from application.models.current_home import CurrentHome
from application.models.acknowledgement import Acknowledgement
from application.models.task_dependency import TaskDependency
from application.models.disclosure import Disclosure
from application.models.task_status import TaskStatus
from application.models.preapproval import PreApproval
from application.models.offer import Offer
from application.models.contract_template import ContractTemplate

from user.models import User
from utils.models import CustomBaseModelMixin


class PropertyCondition(str, Enum):
    POOR = "Poor"
    AVERAGE = "Average"
    EXCELLENT = "Excellent"


class SalesPriceConfidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ComparableType(str, Enum):
    SUBJECT_PROPERTY = "Subject property"
    PRIMARY = "Primary"
    SECONDARY = "Secondary"


class MarketValueReportName(str, Enum):
    HOUSE_CANARY = "House Canary"


class CurrentHomeImageStatus(str, Enum):
    """
    Image Statuses.
    """
    PENDING = "pending"
    UPLOADED = "uploaded"
    LABELED = "labeled"


class CurrentHomeImageLabel(str, Enum):
    """
    options for current home image label/category
    """
    KITCHEN = 'kitchen'
    LIVING_ROOM = 'living_room'
    MASTER_BATH = 'master_bath'
    FRONT_EXTERIOR = 'front_exterior'
    ALL_OTHER_ROOMS = 'all_other_rooms'
    REQUIRED_REPAIRS_PHOTOS = 'required_repairs'
    HOME_UPDATES_PHOTOS = 'home_updates'


class CurrentHomeImage(CustomBaseModelMixin):
    current_home = models.ForeignKey(CurrentHome, on_delete=models.CASCADE, related_name='images')
    url = models.TextField(unique=True)
    label = models.TextField(null=True, blank=True, choices=[(tag.value, tag.value) for tag in CurrentHomeImageLabel])
    status = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in CurrentHomeImageStatus],
                              default=CurrentHomeImageStatus.PENDING)
    created_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)


class MarketValuation(CustomBaseModelMixin):
    current_home = models.ForeignKey(CurrentHome, on_delete=models.CASCADE)
    property_condition = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in PropertyCondition], blank=True, null=True)
    is_in_completed_neighborhood = models.BooleanField(blank=True, null=True)
    is_less_than_one_acre = models.BooleanField(blank=True, null=True)
    is_built_after_1960 = models.BooleanField(blank=True, null=True)


class MarketValueReport(CustomBaseModelMixin):
    """
    To store AVM Report
    """
    market_valuation = models.ForeignKey(MarketValuation, on_delete=models.CASCADE, related_name='avm')
    name = models.CharField(max_length=50, choices=[(tag.value, tag.value)
                                                    for tag in MarketValueReportName], default=MarketValueReportName.HOUSE_CANARY, blank=True, null=True)
    link = models.URLField(max_length=200, blank=True, null=True)


class MarketValueOpinionType(str, Enum):
    """
    Market value Opinion Types.
    """
    LOCAL_AGENT = 'local_agent'
    SR_ANALYST = 'sr_analyst'


class MarketValueOpinion(CustomBaseModelMixin):
    """
    To store market value opinions about property.
    """
    market_valuation = models.ForeignKey(MarketValuation, on_delete=models.CASCADE, related_name="value_opinions")
    suggested_list_price = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    minimum_sales_price = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    maximum_sales_price = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    sales_price_confidence = models.CharField(max_length=50, choices=[(tag.value, tag.value)
                                                                      for tag in SalesPriceConfidence], blank=True, null=True)
    estimated_days_on_market = models.CharField(max_length=50, blank=True, null=True)
    type = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in MarketValueOpinionType])


class MarketValueOpinionComment(CustomBaseModelMixin):
    """
    To store market value opinion related comments.
    """
    market_value_opinion = models.ForeignKey(MarketValueOpinion, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField(max_length=140)
    is_favorite = models.BooleanField(default=False)


class Comparable(CustomBaseModelMixin):
    market_valuation = models.ForeignKey(MarketValuation, on_delete=models.CASCADE, related_name='comparables')
    comparable_type = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in ComparableType])
    comment = models.TextField(blank=True, null=True)
    address = models.ForeignKey(Address, on_delete=models.PROTECT, null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)


class StageHistory(CustomBaseModelMixin):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    previous_stage = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in ApplicationStage])
    new_stage = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in ApplicationStage])


class NoteType(str, Enum):
    """
    To distinguish between system generated and user created.
    """
    APPLICATION_STAGE = "application stage"
    GENERAL = "general"


class Note(CustomBaseModelMixin):
    """
    To store conversation note of agents related to their applications.
    """
    author = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True, related_name="notes")
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="notes")
    title = models.CharField(max_length=255)
    note = models.TextField()
    type = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in NoteType], default=NoteType.GENERAL)

    class Meta:
        ordering = ['-created_at']
