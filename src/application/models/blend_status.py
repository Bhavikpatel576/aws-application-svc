import re


class BlendStatus:
    APPLICATION_CREATED = 'Application created'
    APPLICATION_ARCHIVED = 'Application Archived'
    APPLICATION_IN_PROGRESS_PATTERN = re.compile('Application in progress: .+', re.IGNORECASE)
    APPLICATION_COMPLETED_PATTERN = re.compile('Application completed.+', re.IGNORECASE)
