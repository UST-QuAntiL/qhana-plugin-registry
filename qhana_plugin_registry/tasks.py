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

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from celery import group
from celery.result import AsyncResult
from celery.utils.log import get_task_logger
from sqlalchemy.sql.expression import select
from requests import get
from requests.exceptions import JSONDecodeError, ConnectionError
from datetime import datetime

from .celery import CELERY
from .db.db import DB
from .db.models.plugins import (
    RAMP,
    DataToRAMP,
    ContentTypeToData,
    DATA_RELATION_PRODUCED,
    DATA_RELATION_CONSUMED,
)
from .db.models.seeds import Seed

_name = "qhana-plugin-registry"

TASK_LOGGER = get_task_logger(_name)

BATCH_SIZE = 10


@CELERY.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):  # FIXME does not seem to work
    sender.add_periodic_task(
        300, start_plugin_discovery.s(), name="Plugin discovery"
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
    now = datetime.utcnow()
    try:
        data = get(seed).json()
    except JSONDecodeError or ConnectionError as err:
        return
    if data.keys() >= PLUGIN_KEYS:
        # Data matches the structure of a plugin resource => is most likely a plugin
        update_plugin_data(data, url=seed, now=now, seed=root_seed)
        return  # TODO update/register plugin in DB

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


def split_mimetype(mimetype_like: str) -> Tuple[str, str]:
    """Split and normalize a mimetype like string into two components on the first '/'."""
    if not mimetype_like:
        return "*", "*"
    split = mimetype_like.split("/", maxsplit=1)
    start = split[0] if split[0] else "*"
    end = split[1] if len(split) > 1 and split[1] else "*"
    return start, end


def update_plugin_data(
    plugin_data: Dict[str, Any], *, now: datetime, url: str, seed: Optional[str] = None
):
    """Update the plugin data in the database.

    Args:
        plugin_data (Dict[str, Any]): the new data from the plugin root endpoint
        now (datetime): the time the data was requested
        url (str): the plugin root url
        seed (Optional[str], optional): optional root_seed. Defaults to None.
    """
    plugin_id = plugin_data["name"]
    plugin_version = plugin_data["version"]

    q = select(RAMP).where(RAMP.plugin_id == plugin_id, RAMP.version == plugin_version)
    found_plugin: Optional[RAMP] = DB.session.execute(q).scalar_one_or_none()

    if not found_plugin:
        entry_point = plugin_data["entryPoint"]

        data: List[DataToRAMP] = []
        for output in entry_point.get("dataOutput"):
            data_type = split_mimetype(output.get("dataType", ""))
            content_types = [
                ContentTypeToData(
                    content_type_start=(c_type := split_mimetype(c))[0],
                    content_type_end=c_type[1],
                )
                for c in output.get("contentType", [])
            ]
            data.append(
                DataToRAMP(
                    identifier=output.get("name", ""),
                    relation=DATA_RELATION_PRODUCED,
                    required=output.get("required", False),
                    data_type_start=data_type[0],
                    data_type_end=data_type[1],
                    content_types=content_types,
                )
            )
        for output in entry_point.get("dataInput"):
            data_type = split_mimetype(output.get("dataType", ""))
            content_types = [
                ContentTypeToData(
                    content_type_start=(c_type := split_mimetype(c))[0],
                    content_type_end=c_type[1],
                )
                for c in output.get("contentType", [])
            ]
            data.append(
                DataToRAMP(
                    identifier=output.get("parameter", ""),
                    relation=DATA_RELATION_CONSUMED,
                    required=output.get("required", False),
                    data_type_start=data_type[0],
                    data_type_end=data_type[1],
                    content_types=content_types,
                )
            )

        found_plugin = RAMP(
            plugin_id=plugin_id,
            version=plugin_version,
            name=plugin_data.get("title", plugin_id),
            description=plugin_data.get("description", ""),
            plugin_type=plugin_data["type"],
            url=url,
            entry_url=entry_point["href"],
            ui_url=entry_point["uiHref"],
            data=data,
            # TODO plugin dependencies
            # TODO seed
        )

    found_plugin.last_available = now

    DB.session.add(found_plugin)
    DB.session.commit()
