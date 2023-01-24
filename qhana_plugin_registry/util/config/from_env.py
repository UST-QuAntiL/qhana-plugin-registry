import re
from json import loads
from os import environ
from typing import Mapping

from flask import Config

_KEY_VALUE_REGEX = re.compile(r"(?P<key>[^\s:=,;]+)\s*[:=,;\s]\s*(?P<value>[^\n]+)")
"""Match a string with key and value sides separated by any of the separator 
characters '\s' (space or tab), ':', '=', ','and ';'. The key may not contain 
spaces or any of the other separator characters. The value may not start with
a space and cannot contain newline characters."""


def load_config_from_env(config: Config):
    _load_database_uri_from_env(config)
    _load_celery_config_from_env(config)
    _load_plugin_discovery_config_from_env(config)
    _load_plugin_recommendation_config_from_env(config)
    _load_preconfigured_values(config)
    _load_url_rewrite_rules(config, "URL_MAP_FROM_LOCALHOST")
    _load_url_rewrite_rules(config, "URL_MAP_TO_LOCALHOST")


def _load_database_uri_from_env(config: Config):
    if "SQLALCHEMY_DATABASE_URI" in environ:
        config["SQLALCHEMY_DATABASE_URI"] = environ["SQLALCHEMY_DATABASE_URI"]


def _load_celery_config_from_env(config: Config):
    if "BROKER_URL" in environ:
        celery_conf = config.get("CELERY", {})
        celery_conf["broker_url"] = environ["BROKER_URL"]
        config["CELERY"] = celery_conf

    if "RESULT_BACKEND" in environ:
        celery_conf = config.get("CELERY", {})
        celery_conf["result_backend"] = environ["RESULT_BACKEND"]
        config["CELERY"] = celery_conf

    if "CELERY_QUEUE" in environ:
        celery_conf = config.get("CELERY", {})
        celery_conf["task_default_queue"] = environ["CELERY_QUEUE"]
        config["CELERY"] = celery_conf


def _load_plugin_discovery_config_from_env(config: Config):
    if "PLUGIN_DISCOVERY_INTERVAL" in environ:
        interval = int(environ["PLUGIN_DISCOVERY_INTERVAL"])
        if interval < 1 and interval != -1:
            raise ValueError(
                f"PLUGIN_DISCOVERY_INTERVAL may not be smaller than 1 (got {interval})! Use -1 to disable plugin discovery job."
            )
        config["PLUGIN_DISCOVERY_INTERVAL"] = interval

    if "PLUGIN_BATCH_SIZE" in environ:
        size = int(environ["PLUGIN_BATCH_SIZE"])
        if size < 1:
            raise ValueError(f"PLUGIN_BATCH_SIZE may not be smaller than 1 (got {size})!")
        config["PLUGIN_BATCH_SIZE"] = size

    if "PLUGIN_PURGE_INTERVAL" in environ:
        interval = int(environ["PLUGIN_PURGE_INTERVAL"])
        if interval < 1 and interval != -1:
            raise ValueError(
                f"PLUGIN_PURGE_INTERVAL may not be smaller than 1 (got {interval})! Use -1 to disable plugin purging job."
            )
        config["PLUGIN_PURGE_INTERVAL"] = interval

    if "PLUGIN_PURGE_AFTER" in environ:
        purge_after = environ["PLUGIN_PURGE_AFTER"]
        if purge_after in ("auto", "never"):
            config["PLUGIN_PURGE_AFTER"] = purge_after
        else:
            interval = int(purge_after)
            if interval < 1 and interval != -1:
                raise ValueError(
                    f'PLUGIN_PURGE_AFTER may not be smaller than 1 (got {interval})! Use -1 or "never" to never purge a plugin.'
                )
            config["PLUGIN_PURGE_AFTER"] = interval


def _load_plugin_recommendation_config_from_env(config: Config):
    if "PLUGIN_RECOMMENDER_WEIGHTS" in environ:
        weights_str = environ["PLUGIN_RECOMMENDER_WEIGHTS"]
        if weights_str.startswith("{"):
            config["PLUGIN_RECOMMENDER_WEIGHTS"] = loads(weights_str)
        else:
            config["PLUGIN_RECOMMENDER_WEIGHTS"] = {
                (match := _KEY_VALUE_REGEX.match(w)).group("key"): float(
                    match.group("value")
                )
                for w in weights_str.splitlines()
                if not w.isspace()
            }


def _load_preconfigured_values(config: Config):
    env_dict = config.get("CURRENT_ENV", {})
    # load all env variables prefixed with QHANA_ENV_ (remove prefix)
    env_dict.update({k[10:]: v for k, v in environ.items() if k.startswith("QHANA_ENV_")})
    config["CURRENT_ENV"] = env_dict
    if "INITIAL_PLUGIN_SEEDS" in environ:
        seeds = environ["INITIAL_PLUGIN_SEEDS"]
        if seeds.startswith("["):
            config["INITIAL_PLUGIN_SEEDS"] = loads(seeds)
        else:
            config["INITIAL_PLUGIN_SEEDS"] = [
                s.strip() for s in seeds.splitlines() if s and not s.isspace()
            ]
    if "PRECONFIGURED_SERVICES" in environ:
        services = environ["PRECONFIGURED_SERVICES"]
        config["PRECONFIGURED_SERVICES"] = loads(services)


def _load_url_rewrite_rules(config: Config, key: str):
    if key in environ:
        config[key] = loads(environ[key])

    if isinstance(config.get(key), Mapping):
        # rewrite mapping to tuple sequence and precompile regex patterns
        url_map = config[key]
        config[key] = [
            (re.compile(key), value)  # pattern, replacement pairs
            for key, value in url_map.items()
            if isinstance(key, str) and isinstance(value, str)  # only str, str allowed
        ]

        if len(config[key]) != len(url_map):
            pass  # TODO some rewrite rules were dismissed as invalid!
