from enum import Enum


class TaskProgress(str, Enum):
    """
    application task progress statuses
    """
    NOT_STARTED = "Not started"
    IN_PROGRESS = "In progress"
    COMPLETED = "Completed"
    UNDER_REVIEW = 'Under Review'
    APPROVED = "Approved"
    DENIED = "Denied"
