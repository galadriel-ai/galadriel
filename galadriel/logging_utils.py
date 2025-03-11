import logging
import os
from logging import DEBUG
from logging import INFO
from typing import Optional

from pythonjsonlogger import jsonlogger

from galadriel.domain.logs_exporter import LogsExportHandler
from galadriel.proof.prover import Prover

GALADRIEL_NODE_LOGGER = "galadriel"

LOG_FILE_PATH = "logs/logs.log"
LOGGING_MESSAGE_FORMAT = "%(asctime)s %(name)-12s %(levelname)s %(message)s"

logger: Optional[logging.Logger] = None


def init_logging(prover: Optional[Prover], debug: bool):
    global logger  # pylint:disable=W0603
    if logger:
        return
    log_level = DEBUG if debug else INFO
    file_handler = _get_file_logger()
    console_handler = _get_console_logger()
    logger = logging.getLogger()
    logs_exports_handler = LogsExportHandler(logger, prover)
    logger.setLevel(log_level)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(logs_exports_handler)
    apply_default_formatter(file_handler)
    apply_default_formatter(console_handler)
    apply_default_formatter(logs_exports_handler)
    logger.propagate = False

    logs_exports_handler.run()


def _get_file_logger() -> logging.FileHandler:
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE_PATH)
    file_handler.setLevel(logging.DEBUG)
    return file_handler


def _get_console_logger() -> logging.StreamHandler:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    return console_handler


def apply_default_formatter(handler: logging.Handler):
    formatter = jsonlogger.JsonFormatter(LOGGING_MESSAGE_FORMAT)
    handler.setFormatter(formatter)


def get_agent_logger():
    return logging.getLogger()
