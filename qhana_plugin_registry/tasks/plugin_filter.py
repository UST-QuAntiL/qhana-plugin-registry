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

import json
import re
from celery.utils.log import get_task_logger
from sqlalchemy.sql.expression import select
from packaging.specifiers import InvalidSpecifier
from packaging.specifiers import SpecifierSet
from packaging.specifiers import Version

from ..celery import CELERY
from ..db.models.templates import TemplateTab
from ..db.db import DB
from ..db.models.plugins import RAMP

_name = "qhana-plugin-registry.tasks.tabs"

TASK_LOGGER = get_task_logger(_name)


def evaluate_plugin_filter(plugin_filter: dict) -> list[RAMP]:
    """Get a list of plugins from a filter.

    Args:
        plugin_filter (str): the recursivly parsed JSON filter string. The following key-value pairs are allowed:
            - "and": list of filters
            - "or": list of filters
            - "not": filter
            - "tag": tag name
            - "version": version specifier (https://peps.python.org/pep-0440/#version-specifiers)
            - "name": plugin name

    Returns:
        list: A list of plugins.
    """
    # TODO: filter plugins in batches
    plugin_mapping = {plugin.id: plugin for plugin in DB.session.query(RAMP).all()}

    def get_plugins_from_filter(filter_dict: dict) -> list[RAMP]:
        match filter_dict:
            case {"and": filter_expr}:
                return set.intersection(
                    *(get_plugins_from_filter(f) for f in filter_expr)
                )
            case {"or": filter_expr}:
                return set.union(*(get_plugins_from_filter(f) for f in filter_expr))
            case {"not": filter_expr}:
                return plugin_mapping.keys() - get_plugins_from_filter(filter_expr)
            case {"tag": tag}:
                has_tag = lambda p, t: any(tag.tag == t for tag in p.tags)
                return {p_id for p_id, p in plugin_mapping.items() if has_tag(p, tag)}
            case {"version": version}:
                specifier_str = re.sub(
                    r"([^\s,])(\s+)", r"\1,\2", version
                )  # add commas to whitespace
                try:
                    specifier = SpecifierSet(specifier_str)
                except InvalidSpecifier:
                    TASK_LOGGER.warning(f"Invalid version specifier: '{version}'")
                    return set()
                return {
                    p_id
                    for p_id, p in plugin_mapping.items()
                    if Version(p.version) in specifier
                }
            case {"name": name}:
                return {p_id for p_id, p in plugin_mapping.items() if name == p.name}
            case _:
                TASK_LOGGER.warning(f"Invalid filter: '{filter_dict}'")
                return set()

    return [plugin_mapping[p_id] for p_id in get_plugins_from_filter(plugin_filter)]


@CELERY.task(name=f"{_name}.apply_filter_for_tab", bind=True, ignore_result=True)
def apply_filter_for_tab(self, tab_id):
    found_tab = TemplateTab.get_by_id(tab_id)
    found_tab.plugins = evaluate_plugin_filter(found_tab.plugin_filter)
    DB.session.commit()


@CELERY.task(name=f"{_name}.update_plugin_lists", bind=True, ignore_result=True)
def update_plugin_lists(self, plugin_id):
    found_plugin = RAMP.get_by_id(plugin_id)
    for tab in DB.session.query(TemplateTab).all():
        plugins = evaluate_plugin_filter(tab.plugin_filter)
        if plugin_id in (p.id for p in plugins):
            tab.plugins = plugins
            DB.session.commit()
