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
from celery.utils.log import get_task_logger
from sqlalchemy.sql.expression import select

from ..celery import CELERY
from ..db.models.templates import TemplateTab
from ..db.db import DB
from ..db.models.plugins import RAMP

_name = "qhana-plugin-registry.tasks.tabs"

TASK_LOGGER = get_task_logger(_name)


def evaluate_plugin_filter(filter_string: str) -> list[RAMP]:
    """Get a list of plugins from a filter.

    Args:
        plugin_filter (str): The filter string.

    Returns:
        list: A list of plugins.
    """
    # TODO: store filter as dict in DB to avoid parsing
    plugin_filter: dict = json.loads(filter_string)
    plugins = DB.session.query(RAMP).all()

    def get_plugins_from_filter(filter_dict: dict) -> list[RAMP]:
        # TODO: add match for plugin description
        match filter_dict:
            case {"and": filter_expr}:
                return set.intersection(*map(set, [get_plugins_from_filter(f) for f in filter_expr]))
            case {"or": filter_expr}:
                return set.union(*map(set, [get_plugins_from_filter(f) for f in filter_expr]))
            case {"not": filter_expr}:
                return set.difference(set(plugins), set(get_plugins_from_filter(filter_expr)))
            case {"tag": tag}:
                return [plugin for plugin in plugins if tag in [t.tag for t in plugin.tags]]
            case {"version": version}:
                # TODO: match version with semver
                return [plugin for plugin in plugins if version == plugin.version]
            case {"name": name}:
                return [plugin for plugin in plugins if name == plugin.name]
            case _:
                return []

    return get_plugins_from_filter(plugin_filter)


@CELERY.task(name=f"{_name}.apply_filter_for_tab", bind=True, ignore_result=True)
def apply_filter_for_tab(self, tab_id):
    q = select(TemplateTab).where(TemplateTab.id == tab_id)
    found_tab: Optional[TemplateTab] = DB.session.execute(q).scalar_one_or_none()
    found_tab.plugins = evaluate_plugin_filter(found_tab.plugin_filter)
    DB.session.commit()


@CELERY.task(name=f"{_name}.update_plugin_lists", bind=True, ignore_result=True)
def update_plugin_lists(self, plugin_id):
    for tab in DB.session.query(TemplateTab).all():
        # TODO: reevaluate plugin_filter and update plugin list if necessary
        pass
