from enum import Enum


class TaskCategory(str, Enum):
    """
    application task given to user
    """
    EXISTING_PROPERTY = "existing_property"
    REAL_ESTATE_AGENT = "real_estate_agent"
    HOMEWARD_MORTGAGE = "homeward_mortgage"
    LENDER = 'lender'
    BUYING_SITUATION = "buying_situation"
    PHOTO_UPLOAD = "photo_upload"
    DISCLOSURES = "disclosures"
