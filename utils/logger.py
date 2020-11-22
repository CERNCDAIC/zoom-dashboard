from datetime import datetime
import logging
from pytz import timezone, utc
import sys


def zurich_time(*args):
    """
    Convert the given date to Geneva/Zurich timezone
    :param args:
    :return:
    """
    utc_dt = utc.localize(datetime.utcnow())
    my_tz = timezone("Europe/Zurich")
    converted = utc_dt.astimezone(my_tz)
    return converted.timetuple()


def setup_logs(app, logger_name, to_stdout=True, to_file=False):
    """
    Configure the application loggers

    :param app: 
    :param logger_name:
    :param to_stdout:
    :param to_file:
    :return:
    """
    logger = logging.getLogger(logger_name)

    if app.config['LOG_LEVEL'] == 'DEV':
        logger.setLevel(logging.DEBUG)

    if app.config['LOG_LEVEL'] == 'PROD':
        logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(levelname)s - %(asctime)s - %(name)s - %(message)s - %(pathname)s - %(funcName)s():%(lineno)d')

    logging.Formatter.converter = zurich_time

    if to_stdout:
        configure_stdout_logging(logger=logger, formatter=formatter, log_level=app.config['LOG_LEVEL'])

    if to_file:
        configure_file_logging(logger=logger, formatter=formatter)


def configure_stdout_logging(logger=None, formatter=None, log_level="DEV"):
    stream_handler = logging.StreamHandler(stream=sys.stdout)

    stream_handler.setFormatter(formatter)
    if log_level == 'DEV':
        stream_handler.setLevel(logging.DEBUG)
    if log_level == 'PROD':
        stream_handler.setLevel(logging.INFO)

    logger.addHandler(stream_handler)
    print("Logging {logger_name} to stdout -> True".format(logger_name=str(logger)))


def configure_file_logging(logger=None, formatter=None):
    handler = logging.FileHandler('error.log')

    handler.setFormatter(formatter)
    handler.setLevel(logging.WARN)

    logger.addHandler(handler)
    print("Logging {logger_name} to file -> True".format(logger_name=str(logger)))
