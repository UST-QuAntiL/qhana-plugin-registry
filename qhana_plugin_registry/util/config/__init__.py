"""Module containing default config values."""
from logging import INFO, WARNING
from os import urandom

from .celery_config import CELERY_DEBUG_CONFIG, CELERY_PRODUCTION_CONFIG
from .smorest_config import SmorestDebugConfig, SmorestProductionConfig
from .sqlalchemy_config import SQLAchemyDebugConfig, SQLAchemyProductionConfig


class ProductionConfig(SQLAchemyProductionConfig, SmorestProductionConfig):
    ENV = "production"
    SECRET_KEY = urandom(32)

    REVERSE_PROXY_COUNT = 0

    DEBUG = False
    TESTING = False

    # JSON_SORT_KEYS = False
    # JSONIFY_PRETTYPRINT_REGULAR = False
    JSON = {
        "sort_keys": True,
        "compact": True,
    }

    LOG_CONFIG = None  # if set this is preferred

    DEFAULT_LOG_SEVERITY = WARNING
    DEFAULT_LOG_FORMAT_STYLE = "{"
    DEFAULT_LOG_FORMAT = "{asctime} [{levelname:^7}] [{module:<30}] {message}    <{funcName}, {lineno}; {pathname}>"
    DEFAULT_LOG_DATE_FORMAT = None

    CELERY = CELERY_PRODUCTION_CONFIG

    # config related to celery tasks
    PLUGIN_DISCOVERY_INTERVAL = 15 * 60  # 15 minutes
    PLUGIN_BATCH_SIZE = 50

    PLUGIN_PURGE_INTERVAL = 15 * 60  # 15 minutes
    PLUGIN_PURGE_AFTER = 7 * 24 * 60 * 60  # 1 week

    # plugin recommendations
    RECOMMENDER_WEIGHTS = {
        "AvailableDataRecommender": 1,
        "CurrentDataRecommender": 5,
        "StepDataRecommender": 3,
    }
    RECOMMENDATION_TIMEOUT = 5
    RECOMMENDATION_LIMIT = 5

    # preloading the DB with some values
    CURRENT_ENV = {}  # a (string) key: value dict representing env variables
    INITIAL_PLUGIN_SEEDS = []  # a list of URLs
    PRECONFIGURED_SERVICES = []  # a list of dicts with service info

    # rewrite rules for URLs e.g. to map localhost to docker container name and vise versa
    # these dicts will be converted to and replaced by lists of (key, value) tuples
    URL_MAP_FROM_LOCALHOST = {}
    URL_MAP_TO_LOCALHOST = {}


class DebugConfig(ProductionConfig, SQLAchemyDebugConfig, SmorestDebugConfig):
    ENV = "development"
    DEBUG = True
    SECRET_KEY = "debug_secret"  # FIXME make sure this NEVER! gets used in production!!!

    DEFAULT_LOG_SEVERITY = INFO

    JSON = {
        "sort_keys": True,
        "compact": False,
    }

    CELERY = CELERY_DEBUG_CONFIG

    # config related to celery tasks
    PLUGIN_DISCOVERY_INTERVAL = 60  # 1 minute
    PLUGIN_BATCH_SIZE = 10

    PLUGIN_PURGE_INTERVAL = 60  # 1 minute
    PLUGIN_PURGE_AFTER = "auto"
