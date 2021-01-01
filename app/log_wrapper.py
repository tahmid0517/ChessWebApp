import logging
import sys
from datetime import datetime

LOG_WRAPPER_TAG = "LOGW"

class Logger:
    logger = None

    def __init__(self, module_tag):
        self.module_tag = module_tag
        if Logger.logger is None:
            Logger.logger = logging.getLogger(LOG_WRAPPER_TAG)
            Logger.logger.setLevel(logging.DEBUG)
            Logger.logger.addHandler(logging.StreamHandler(sys.stdout))

    def get_timestamp(self):
        return str(datetime.now())

    def debug(self, msg: str):
        DEBUG_TAG = "DEBUG"
        timestamp = self.get_timestamp()
        Logger.logger.debug(LOG_WRAPPER_TAG + " | " + timestamp + " | " + DEBUG_TAG + " | "  + self.module_tag + " | " + msg)

    def error(self, msg: str):
        ERROR_TAG = "ERROR"
        timestamp = self.get_timestamp()
        Logger.logger.error(LOG_WRAPPER_TAG + " | " + timestamp + " | " + ERROR_TAG + " | " + self.module_tag + " | " + msg)

