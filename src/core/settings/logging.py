import logging
class AddSeverityLevel(logging.Filter):
    def filter(self, record):
        record.severity = str(record.levelname)
        return True
