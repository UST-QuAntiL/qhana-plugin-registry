# Copyright 2022 University of Stuttgart
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from celery import Celery
from flask import Flask

from .plugin_discovery import purge_plugins, start_plugin_discovery

from ..recommendations import recommenders  # noqa


def register_periodic_tasks(app: Flask, celery: Celery):
    """Register periodic tasks with celery.

    Args:
        app (Flask): flask app passed for configuration values
        celery (Celery): celery instance to register tasks for
    """
    _register_plugin_discovery_task(app, celery)
    _register_plugin_purge_task(app, celery)


def _register_plugin_discovery_task(app: Flask, celery: Celery):
    """Register the plugin discovery periodic task with celery.

    Args:
        app (Flask): flask app passed for configuration values
        celery (Celery): celery instance to register tasks for
    """
    plugin_discovery_intervall: int = app.config.get("PLUGIN_DISCOVERY_INTERVAL", 15 * 60)

    if not isinstance(plugin_discovery_intervall, (int, float)):
        raise TypeError(
            "The plugin discovery intervall setting has the wrong type! (expected int or float)"
        )

    if plugin_discovery_intervall == -1:
        return  # -1 prevents recurring task entirely

    if plugin_discovery_intervall < 5:
        raise ValueError(
            f"The shortest allowed intervall for the plugin discovery task is 5 seconds (got {plugin_discovery_intervall})."
        )

    celery.add_periodic_task(
        plugin_discovery_intervall,
        start_plugin_discovery.s(),
        name="Plugin discovery",
    )


def _register_plugin_purge_task(app: Flask, celery: Celery):
    """Register the plugin purge periodic task with celery.

    Args:
        app (Flask): flask app passed for configuration values
        celery (Celery): celery instance to register tasks for
    """
    plugin_purge_intervall: int = app.config.get("PLUGIN_PURGE_INTERVAL", 15 * 60)

    if not isinstance(plugin_purge_intervall, (int, float)):
        raise TypeError(
            "The plugin purge intervall setting has the wrong type! (expected int or float)"
        )

    if plugin_purge_intervall == -1:
        return  # -1 prevents recurring task entirely

    if plugin_purge_intervall < 5:
        raise ValueError(
            f"The shortest allowed intervall for the plugin purging task is 5 seconds (got {plugin_purge_intervall})."
        )

    purge_after = app.config.get("PLUGIN_PURGE_AFTER", "never")
    if purge_after in ("never", -1) or purge_after is None:
        return  # plugins will not be purged so there is no need to schedule the task

    celery.add_periodic_task(
        plugin_purge_intervall,
        purge_plugins.s(),
        name="Plugin purge",
    )
