from enum import Enum


class TaskName(str, Enum):
    """
    application task given to user
    """
    EXISTING_PROPERTY = "existing_property"
    REAL_ESTATE_AGENT = "real_estate_agent"
    MY_LENDER = 'my_lender'
    MY_LENDER_BETTER = 'my_lender_better'
    BUYING_SITUATION = "buying_situation"
    PHOTO_UPLOAD = "photo_upload"
    DISCLOSURES = "disclosures"
    COLORADO_MORTGAGE = 'co_mortgage'
    TEXAS_MORTGAGE = 'tx_mortgage'
