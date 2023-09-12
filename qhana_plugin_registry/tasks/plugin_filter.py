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

from typing import Iterator
from difflib import SequenceMatcher
from celery.utils.log import get_task_logger
from packaging.specifiers import InvalidSpecifier
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from ..celery import CELERY
from ..db.models.templates import TemplateTab
from ..db.db import DB
from ..db.models.plugins import RAMP

_name = "qhana-plugin-registry.tasks.tabs"

TASK_LOGGER = get_task_logger(_name)

DEFAULT_BATCH_SIZE = 500
PLUGIN_NAME_MATCHING_THREASHOLD = 0.8


def get_plugins_from_filter(
    filter_dict: dict, plugin_mapping: dict[str, RAMP]
) -> set[RAMP]:
    """Get the plugins that match a filter.

    Args:
        filter_dict (dict): the filter to evaluate
        plugin_mapping (dict): a mapping from plugin ids to plugins

    Returns:
        set[RAMP]: the plugin ids that match the filter
    """

    match filter_dict:
        case {"and": filter_expr}:
            if not filter_expr:
                return set()
            return set.intersection(
                *(get_plugins_from_filter(f, plugin_mapping) for f in filter_expr)
            )
        case {"or": filter_expr}:
            if not filter_expr:
                return set()
            return set.union(
                *(get_plugins_from_filter(f, plugin_mapping) for f in filter_expr)
            )
        case {"not": filter_expr}:
            return plugin_mapping.keys() - get_plugins_from_filter(
                filter_expr, plugin_mapping
            )
        case {"tag": tag}:
            has_tag = lambda p, t: any(tag.tag == t for tag in p.tags)
            return {p_id for p_id, p in plugin_mapping.items() if has_tag(p, tag)}
        case {"version": version}:
            try:
                specifier = SpecifierSet(version)
            except InvalidSpecifier:
                TASK_LOGGER.warning(f"Invalid version specifier: '{version}'")
                return set()
            return {
                p_id
                for p_id, p in plugin_mapping.items()
                if Version(p.version) in specifier
            }
        case {"name": name}:
            plugin_ids = set()
            for p_id, p in plugin_mapping.items():
                matcher = SequenceMatcher(None, name.lower(), p.name.lower())
                if matcher.ratio() > PLUGIN_NAME_MATCHING_THREASHOLD:
                    plugin_ids.add(p_id)
            return plugin_ids
        case {"id": plugin_id}:
            # match plugin id or plugin id without version
            plugin_ids = set()
            plugin_id_split = plugin_id.split("@")
            for p_id, p in plugin_mapping.items():
                if plugin_id == p.full_id:
                    plugin_ids.add(p_id)
                elif plugin_id_split == p.full_id.split("@")[:-1]:
                    # id matches, except for the version string
                    plugin_ids.add(p_id)
            return plugin_ids
        case {"type": plugin_type}:
            plugin_type_lower = plugin_type.lower()
            return {
                p_id
                for p_id, p in plugin_mapping.items()
                if p.plugin_type.lower() == plugin_type_lower
            }
        case _:
            TASK_LOGGER.warning(f"Invalid filter: '{filter_dict}'")
            return set()


def evaluate_plugin_filter(plugin_filter: dict) -> Iterator[RAMP]:
    """Evaluate a plugin filter and return the matching plugins (calls `get_plugins_from_filter` in batches).

    Args:
        plugin_filter (str): the recursivly parsed JSON filter string. The following key-value pairs are allowed:
            - "and": list of filters
            - "or": list of filters
            - "not": filter
            - "id": plugin id
            - "tag": tag name
            - "version": version specifier (https://peps.python.org/pep-0440/#version-specifiers)
            - "name": plugin name
            - "type": plugin type

    Returns:
        Iterator[RAMP]: an iterator over the plugins that match the filter
    """
    count = DB.session.query(RAMP).count()
    for offset in range(0, count, DEFAULT_BATCH_SIZE):
        plugin_mapping = {
            plugin.id: plugin
            for plugin in DB.session.query(RAMP).limit(DEFAULT_BATCH_SIZE).offset(offset)
        }
        p_ids = get_plugins_from_filter(plugin_filter, plugin_mapping)
        for p_id in p_ids:
            yield plugin_mapping[p_id]


@CELERY.task(name=f"{_name}.apply_filter_for_tab", bind=True, ignore_result=True)
def apply_filter_for_tab(self, tab_id):
    found_tab = TemplateTab.get_by_id(tab_id)
    if not found_tab or not isinstance(found_tab, TemplateTab):
        TASK_LOGGER.warning(f"Tab with id {tab_id} not found.")
        return
    found_tab.plugins = list(evaluate_plugin_filter(found_tab.plugin_filter))
    DB.session.commit()


@CELERY.task(name=f"{_name}.update_plugin_lists", bind=True, ignore_result=True)
def update_plugin_lists(self, plugin_id):
    for tab in DB.session.query(TemplateTab).all():
        plugins = list(evaluate_plugin_filter(tab.plugin_filter))
        if plugin_id in (p.id for p in plugins):
            tab.plugins = plugins
            DB.session.commit()
