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

from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from celery.utils.log import get_task_logger
from flask.globals import current_app
from requests.exceptions import (
    ConnectionError,
    JSONDecodeError,
    HTTPError,
    RequestException,
)
from sqlalchemy.sql.expression import delete, desc, select

from .url_mapped_requests import open_url, map_url
from ..celery import CELERY, FlaskTask
from ..db.db import DB
from ..db.models.plugins import RAMP
from ..db.models.seeds import Seed
from ..db.util import update_plugin_data
from .plugin_filter import update_plugin_lists

_name = "qhana-plugin-registry.tasks.plugins"

TASK_LOGGER = get_task_logger(_name)

DEFAULT_BATCH_SIZE = 20


@CELERY.task(name=f"{_name}.start_plugin_discovery", bind=True, ignore_result=True)
def start_plugin_discovery(self: FlaskTask):
    """Kick of plugin discovery process starting from the seed urls."""
    batch_size: int = current_app.config.get("PLUGIN_BATCH_SIZE", DEFAULT_BATCH_SIZE)
    seeds = DB.session.execute(select(Seed.url)).scalars().all()
    tasks = discover_plugins_from_seeds.chunks(((i,) for i in seeds), batch_size).group()
    tasks.skew().apply_async()


PLUGIN_KEYS = {"name", "version", "title", "description", "type", "tags", "entryPoint"}
"A set of keys to determine if an object is likely to be a QHAna plugin."


@CELERY.task(name=f"{_name}.discover_plugins_from_seeds", bind=True, ignore_result=True)
def discover_plugins_from_seeds(
    self: FlaskTask,
    seed: str,
    root_seed: Optional[str] = None,
    nesting: int = 0,
    delete_on_missing: bool = False,
):
    """Discover QHAna plugins starting off with a seed URL.

    Args:
        seed (str): the current seed to discover plugins at
        root_seed (Optional[str], optional): the root seed at the start of discovery (e.g. an URL to a plugin runner). Defaults to None.
        nesting (int, optional): a nesting level to avoid catastrophic infinite recursions. Defaults to 0.
        delete_on_missing (bool, optional): whether a plugin should be deleted from the registry if it's missing or a connection error occurred
    """
    if nesting > 3:
        TASK_LOGGER.error(
            f"Plugin discovery nested too deep, aborting! ({seed=}, {root_seed=}, {nesting=})"
        )
        return
    now = datetime.now(timezone.utc)
    try:
        data = open_url(seed, timeout=5).json()
    except JSONDecodeError as err:
        return
    except ConnectionError as err:
        if delete_on_missing:
            TASK_LOGGER.info(f"Can't reach '{seed}', trying to delete it")
            _delete_plugin(seed)

        return
    except HTTPError as err:
        if err.response is not None and err.response.status_code == 404:
            if delete_on_missing:
                TASK_LOGGER.info(f"Plugin/seed '{seed}' not found, trying to delete it")
                _delete_plugin(seed)

            return  # ignore not found status codes
        TASK_LOGGER.info(
            f"Could not reach seed/plugin '{seed}' because of a server error. ({err})"
        )
        return
    except RequestException as err:
        TASK_LOGGER.info(
            f"Could not reach seed/plugin '{seed}' because of a network error. ({err})"
        )
        return

    if data.keys() >= PLUGIN_KEYS:
        # Data matches the structure of a plugin resource => is most likely a plugin
        plugin: RAMP

        mapped_seed = map_url(seed, "URL_MAP_TO_LOCALHOST")
        mapped_root_seed = map_url(root_seed, "URL_MAP_TO_LOCALHOST")

        plugin, is_new_plugin = update_plugin_data(
            data, url=mapped_seed, now=now, seed_url=mapped_root_seed
        )
        if is_new_plugin:
            update_plugin_lists.delay(plugin.id)
            # TODO run all updates / checks for new plugins (e.g. dependencies, templates, etc.)
        return

    # treat seed as plugin runner
    try:
        plugin_data = open_url(seed.rstrip("/") + "/plugins", timeout=10).json()
    except JSONDecodeError or ConnectionError or RequestException as err:
        return

    root_seed = root_seed if root_seed else seed
    plugin_seeds = [
        (api, root_seed, nesting + 1)
        for p in plugin_data.get("plugins", [])
        if (api := p.get("apiRoot"))
    ]

    batch_size: int = current_app.config.get("PLUGIN_BATCH_SIZE", DEFAULT_BATCH_SIZE)
    tasks = discover_plugins_from_seeds.chunks(plugin_seeds, batch_size).group()
    tasks.skew().apply_async()


@CELERY.task(name=f"{_name}.purge_plugins", ignore_result=True)
def purge_plugins():
    """Purge plugin according to the PLUGIN_PURGE_AFTER setting.

    Plugins that were not available in the timeframe specified are removed from the database.
    The time is counted from the latest time any plugin was available.
    This means that only if the plugin discovery task updates these timestamps
    more plugins will be removed on repeated runs of this task.
    """
    purge_after: Union[str, int, float, timedelta, None] = current_app.config.get(
        "PLUGIN_PURGE_AFTER", "never"
    )
    if purge_after in ("never", -1) or purge_after is None:
        return  # do not purge
    if purge_after == "auto":
        plugin_discovery_intervall = current_app.config.get(
            "PLUGIN_DISCOVERY_INTERVAL", 15 * 60
        )
        if not isinstance(plugin_discovery_intervall, (int, float)):
            TASK_LOGGER.warning(
                f"The purge_after configuration could not be inferred automatically (invalid discovery interval {plugin_discovery_intervall}). Aborting."
            )
            return
        if plugin_discovery_intervall < 5:
            TASK_LOGGER.warning(
                f"The purge_after configuration could not be inferred automatically (too small discovery interval {plugin_discovery_intervall}). Aborting."
            )
            return

        # allow up to 10 failures to reach the plugin before purging
        purge_after = plugin_discovery_intervall * 10
    if isinstance(purge_after, str):
        TASK_LOGGER.warning(
            f"The purge_after configuration has the wrong type (expected int but got {purge_after}). Aborting."
        )
        return
    if isinstance(purge_after, (int, float)):
        purge_after = timedelta(seconds=purge_after)

    assert purge_after is not None  # to keep typechecker happy

    latest_date_query = select(RAMP.last_available).order_by(desc(RAMP.last_available))

    latest_date: Optional[datetime] = (
        DB.session.execute(latest_date_query).scalars().first()
    )

    if latest_date is None:
        TASK_LOGGER.info("No plugins detected. No plugins to purge.")
        return

    purge_before_date = latest_date - purge_after

    delete_query = (
        delete(RAMP)
        .filter(RAMP.last_available < purge_before_date)
        .execution_options(synchronize_session="fetch")
    )

    DB.session.execute(delete_query)
    DB.session.commit()


def _delete_plugin(url: str):
    delete_query = (
        delete(RAMP)
        .filter(RAMP.url == url)
        .execution_options(synchronize_session="fetch")
    )

    DB.session.execute(delete_query)
    DB.session.commit()
