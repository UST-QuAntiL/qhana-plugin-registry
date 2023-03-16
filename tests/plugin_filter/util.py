# Copyright 2023 University of Stuttgart
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

from qhana_plugin_registry.db.models.plugins import RAMP, PluginTag
from qhana_plugin_registry.db.models.templates import TemplateTab
from qhana_plugin_registry.tasks.plugin_filter import apply_filter_for_tab

from hypothesis import strategies as st
from packaging.specifiers import Specifier
import json


def filter_strategy():
    return st.one_of(
        st.fixed_dictionaries({}),
        st.fixed_dictionaries({"tag": st.text()}),
        st.fixed_dictionaries({"name": st.text()}),
        st.fixed_dictionaries({"version": st.from_regex(Specifier._regex)}),
        st.fixed_dictionaries({"and": st.lists(st.deferred(filter_strategy))}),
        st.fixed_dictionaries({"or": st.lists(st.deferred(filter_strategy))}),
        st.fixed_dictionaries({"not": st.deferred(filter_strategy)}),
    )


def create_plugin(
    tmp_db,
    name: str = "test-plugin",
    version: str = "0.0.0",
    tags: list[PluginTag] | None = None,
    description: str = "descr",
) -> RAMP:
    if not tags:
        tags = []
    plugin = RAMP(
        name=name,
        description=description,
        version=version,
        tags=tags,
    )
    plugin.plugin_id = f"{name}@{version}"
    tmp_db.session.add(plugin)
    tmp_db.session.commit()
    plugin_id = (
        tmp_db.session.query(RAMP.id)
        .filter(RAMP.name == name, RAMP.version == version)
        .first()[0]
    )
    return plugin_id


def create_template_tab(
    tmp_db,
    client,
    template_id: str = "1",
    tab_name: str = "test_tab",
    tab_description: str = "test tab",
    tab_location: str = "test_location",
    sort_key: int = 0,
    filter_dict: dict | None = None,
) -> int:
    if not filter_dict:
        filter_dict = {}
    filter_string = json.dumps(filter_dict)
    response = client.post(
        f"/api/templates/{template_id}/tabs/",
        json={
            "name": tab_name,
            "description": tab_description,
            "location": tab_location,
            "sortKey": sort_key,
            "filterString": filter_string,
        },
    )
    assert response.status_code == 200
    template_tab_id = (
        tmp_db.session.query(TemplateTab.id)
        .filter(
            TemplateTab.name == tab_name,
            TemplateTab.description == tab_description,
            TemplateTab.location == tab_location,
            TemplateTab.sort_key == sort_key,
            TemplateTab.filter_string == filter_string,
        )
        .first()[0]
    )
    apply_filter_for_tab.apply(args=(template_tab_id,))
    return template_tab_id


def update_plugin_filter(tmp_db, client, template_tab: TemplateTab, filter_dict: dict):
    response = client.put(
        f"/api/templates/{template_tab.template_id}/tabs/{template_tab.id}/",
        json={
            "name": template_tab.name,
            "description": template_tab.description,
            "location": template_tab.location,
            "filterString": json.dumps(filter_dict),
            "sortKey": template_tab.sort_key,
        },
    )
    assert response.status_code == 200
    apply_filter_for_tab.apply(args=(template_tab.id,))
    return (
        tmp_db.session.query(TemplateTab)
        .filter(TemplateTab.id == template_tab.id)
        .first()
        .plugins
    )


def filter_matches_plugin(filter_dict: dict, plugin: RAMP) -> bool:
    match filter_dict:
        case {"name": name}:
            return plugin.name == name
        case {"tag": tag}:
            return tag in (tag.tag for tag in plugin.tags)
        case {"version": version}:
            spec = Specifier(version)
            return spec.contains(plugin.version)
        case {"and": and_filters}:
            if not and_filters:
                return False
            return all(
                filter_matches_plugin(filter_dict, plugin) for filter_dict in and_filters
            )
        case {"or": or_filters}:
            if not or_filters:
                return False
            return any(
                filter_matches_plugin(filter_dict, plugin) for filter_dict in or_filters
            )
        case {"not": not_filter}:
            return not filter_matches_plugin(not_filter, plugin)
        case _:
            return False