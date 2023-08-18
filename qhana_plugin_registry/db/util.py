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

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from sqlalchemy.sql.expression import select
from datetime import datetime
from itertools import chain, cycle


from .db import DB
from .models.plugins import (
    RAMP,
    DataToRAMP,
    ContentTypeToData,
    DATA_RELATION_PRODUCED,
    DATA_RELATION_CONSUMED,
    DependencyToRAMP,
    PluginTag,
    TagToDependency,
)
from .models.seeds import Seed


def split_mimetype(mimetype_like: str) -> Tuple[str, str]:
    """Split and normalize a mimetype like string into two components on the first '/'."""
    if not mimetype_like:
        return "*", "*"
    split = mimetype_like.split("/", maxsplit=1)
    start = split[0] if split[0] else "*"
    end = split[1] if len(split) > 1 and split[1] else "*"
    return start, end


def _prepare_plugin_data(entry_point: Dict[str, Any]):
    data: List[DataToRAMP] = []
    data_output_gen = zip(
        entry_point.get("dataOutput", []),
        cycle(["name"]),  # identifier key
        cycle([DATA_RELATION_PRODUCED]),  # data relation type
    )
    data_input_gen = zip(
        entry_point.get("dataInput", []),
        cycle(["parameter"]),  # identifier key
        cycle([DATA_RELATION_CONSUMED]),  # data relation type
    )
    for output, identifier_key, relation in chain(data_input_gen, data_output_gen):
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
                identifier=output.get(identifier_key, ""),
                relation=relation,
                required=output.get("required", False),
                data_type_start=data_type[0],
                data_type_end=data_type[1],
                content_types=content_types,
            )
        )
    return data


def _prepare_dependencies(entry_point) -> List[DependencyToRAMP]:
    dependencies: List[DependencyToRAMP] = []
    dependency: Dict[str, Any]
    for dependency in entry_point.get("pluginDependencies", []):
        tag_filter: List[str] = dependency.get("tags", [])
        dependencies.append(
            DependencyToRAMP(
                required=bool(dependency.get("required", False)),
                parameter=dependency.get("parameter", ""),
                plugin_id=dependency.get("name", None),
                version=dependency.get("version", None),
                plugin_type=dependency.get("type", None),
                dependency_tags=[
                    TagToDependency(
                        tag=PluginTag.get_or_create(t.lstrip("!")),
                        exclude=t.startswith("!"),
                    )
                    for t in tag_filter
                ],
            )
        )
    return dependencies


def update_plugin_data(
    plugin_data: Dict[str, Any],
    *,
    now: datetime,
    url: str,
    seed_url: Optional[str] = None,
):
    """Update the plugin data in the database.

    Args:
        plugin_data (Dict[str, Any]): the new data from the plugin root endpoint
        now (datetime): the time the data was requested
        url (str): the plugin root url
        seed_url (Optional[str], optional): optional root_seed. Defaults to None.
    """
    plugin_id = plugin_data["name"]
    plugin_version = plugin_data["version"]

    q = select(RAMP).where(RAMP.plugin_id == plugin_id, RAMP.version == plugin_version)
    found_plugin: Optional[RAMP] = DB.session.execute(q).scalar_one_or_none()

    is_new_plugin = not found_plugin

    if not found_plugin:
        entry_point = plugin_data["entryPoint"]

        seed: Optional[Seed] = None

        if seed_url:
            seed_query = select(Seed).where(Seed.url == seed_url)
            seed = DB.session.execute(seed_query).scalar_one()

        found_plugin = RAMP(
            seed=seed,
            # plugin identifier
            plugin_id=plugin_id,
            version=plugin_version,
            # human identifiers
            name=plugin_data.get("title", plugin_id),
            description=plugin_data.get("description", ""),
            # metadata
            plugin_type=plugin_data["type"],
            tags=PluginTag.get_or_create_all(plugin_data.get("tags", [])),
            # api URL
            url=url,
            # entry point data
            entry_url=urljoin(base=url, url=entry_point["href"]),
            ui_url=urljoin(base=url, url=entry_point["uiHref"]),
            data=_prepare_plugin_data(entry_point),
            dependencies=_prepare_dependencies(entry_point),
        )

    found_plugin.last_available = now

    # do not error for misbehaving plugins without a name
    if found_plugin.name is None:
        found_plugin.name = "UNNAMED"

    DB.session.add(found_plugin)
    DB.session.commit()

    return found_plugin, is_new_plugin
