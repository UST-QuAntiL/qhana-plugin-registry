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

from typing import Optional

from celery.utils.log import get_task_logger
from sqlalchemy.sql.expression import select
from requests import get
from requests.exceptions import JSONDecodeError, ConnectionError
from datetime import datetime, timezone

from .celery import CELERY
from .db.db import DB
from .db.models.plugins import RAMP
from .db.models.seeds import Seed
from .db.util import update_plugin_data

_name = "qhana-plugin-registry"

TASK_LOGGER = get_task_logger(_name)

BATCH_SIZE = 10


@CELERY.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        20, start_plugin_discovery.s(), name="Plugin discovery"
    )  # FIXME make period configurable


@CELERY.task(name=f"{_name}.start_plugin_discovery", bind=True, ignore_result=True)
def start_plugin_discovery(self):
    """Kick of plugin discovery process starting from the seed urls."""
    seeds = DB.session.execute(select(Seed.url)).scalars().all()
    tasks = discover_plugins_from_seeds.chunks(((i,) for i in seeds), BATCH_SIZE).group()
    tasks.skew().apply_async()


PLUGIN_KEYS = {"name", "version", "title", "description", "type", "tags", "entryPoint"}
"A set of keys to determine if an object is likely to be a QHAna plugin."


@CELERY.task(name=f"{_name}.discover_plugins_from_seeds", bind=True, ignore_result=True)
def discover_plugins_from_seeds(
    self, seed: str, root_seed: Optional[str] = None, nesting: int = 0
):
    """Discover QHAna plugins starting off with a seed URL.

    Args:
        seed (str): the current seed to discover plugins at
        root_seed (Optional[str], optional): the root seed at the start of discovery (e.g. an URL to a plugin runner). Defaults to None.
        nesting (int, optional): a nesting level to avoid catastrophic infinite recursions. Defaults to 0.
    """
    if nesting > 3:
        TASK_LOGGER.error(
            f"Plugin discovery nested too deep, aborting! ({seed=}, {root_seed=}, {nesting=})"
        )
        return
    now = datetime.now(timezone.utc)
    try:
        data = get(seed).json()
    except JSONDecodeError or ConnectionError as err:
        return
    if data.keys() >= PLUGIN_KEYS:
        # Data matches the structure of a plugin resource => is most likely a plugin
        plugin: RAMP
        plugin, is_new_plugin = update_plugin_data(
            data, url=seed, now=now, seed_url=root_seed
        )
        if is_new_plugin:
            pass  # TODO run all updates / checks for new plugins (e.g. dependencies, templates, etc.)
        return

    # treat seed as plugin runner
    try:
        plugin_data = get(seed.rstrip("/") + "/plugins").json()
    except JSONDecodeError or ConnectionError as err:
        return

    root_seed = root_seed if root_seed else seed
    plugin_seeds = [
        (api, root_seed, nesting + 1)
        for p in plugin_data.get("plugins", [])
        if (api := p.get("apiRoot"))
    ]

    tasks = discover_plugins_from_seeds.chunks(plugin_seeds, BATCH_SIZE).group()
    tasks.skew().apply_async()
