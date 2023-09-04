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

from difflib import SequenceMatcher
from typing import Optional
from qhana_plugin_registry.db.models.plugins import RAMP, PluginTag
from qhana_plugin_registry.db.models.templates import TemplateTab
from qhana_plugin_registry.tasks.plugin_filter import (
    PLUGIN_NAME_MATCHING_THREASHOLD,
    apply_filter_for_tab,
)

from hypothesis import strategies as st
from packaging.specifiers import Specifier, SpecifierSet, InvalidSpecifier
import json


def filter_strategy():
    """Strategy for generating filters."""
    return st.one_of(
        st.fixed_dictionaries({}),
        st.fixed_dictionaries({"id": st.text()}),
        st.fixed_dictionaries({"tag": st.text()}),
        st.fixed_dictionaries({"name": st.text()}),
        st.fixed_dictionaries({"version": st.from_regex(Specifier._regex)}),
        st.fixed_dictionaries({"type": st.text()}),
        st.fixed_dictionaries({"and": st.lists(st.deferred(filter_strategy))}),
        st.fixed_dictionaries({"or": st.lists(st.deferred(filter_strategy))}),
        st.fixed_dictionaries({"not": st.deferred(filter_strategy)}),
    )


def create_plugin(
    tmp_db,
    plugin_id: Optional[str] = None,
    name: str = "test-plugin",
    version: str = "0.0.0",
    tags: list[PluginTag] | None = None,
    plugin_type: str = "test-type",
    description: str = "descr",
) -> RAMP:
    """Create a plugin and return its id.

    Args:
        tmp_db: The database fixture.
        plugin_id: The id of the plugin.
        name: The name of the plugin.
        version: The version of the plugin.
        tags: The tags of the plugin.
        description: The description of the plugin.

    Returns:
        The id of the created plugin."""
    if not tags:
        tags = []
    plugin = RAMP(
        name=name,
        description=description,
        version=version,
        tags=tags,
        plugin_type=plugin_type,
    )
    if plugin_id:
        plugin.plugin_id = plugin_id
    else:
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
    """Create a template tab and return its id.

    Args:
        tmp_db: The database fixture.
        client: The client fixture.
        template_id: The id of the template to which the tab belongs.
        tab_name: The name of the tab.
        tab_description: The description of the tab.
        tab_location: The location of the tab.
        sort_key: The sort key of the tab.
        filter_dict: The filter of the tab.

    Returns:
        The id of the created template tab.
    """
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


def update_plugin_filter(
    tmp_db, client, template_tab: TemplateTab, filter_dict: dict
) -> set[int]:
    """Update the filter of a template tab and return the ids of the plugins that match the filter.

    Args:
        tmp_db: The database fixture.
        client: The client fixture.
        template_tab: The template tab to update.
        filter_dict: The new filter.

    Returns:
        The ids of the plugins that match the filter.
    """
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
    plugins = (
        tmp_db.session.query(TemplateTab)
        .filter(TemplateTab.id == template_tab.id)
        .first()
        .plugins
    )
    return {plugin.id for plugin in plugins}


def filter_matches_plugin(filter_dict: dict, plugin: RAMP) -> bool:
    """Check if a plugin matches a filter.

    Args:
        filter_dict: The filter.
        plugin: The plugin.

    Returns:
        True if the plugin matches the filter, False otherwise.
    """
    match filter_dict:
        case {"id": plugin_id}:
            return (
                plugin.plugin_id == plugin_id
                or plugin_id.split("@") == plugin.plugin_id.split("@")[:-1]
            )
        case {"name": name}:
            sm = SequenceMatcher(None, plugin.name, name)
            return sm.ratio() > PLUGIN_NAME_MATCHING_THREASHOLD
        case {"tag": tag}:
            return tag in (tag.tag for tag in plugin.tags)
        case {"version": version}:
            spec = SpecifierSet(version)
            return spec.contains(plugin.version)
        case {"type": plugin_type}:
            return plugin.plugin_type.lower() == plugin_type.lower()
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


def is_specifier_set(s: str) -> bool:
    """Check if a string is a valid PEP 440 specifier set.

    Args:
        s: The string to check.

    Returns:
        True if the string is a valid PEP 440 specifier set, False otherwise.
    """
    try:
        SpecifierSet(s)
    except InvalidSpecifier:
        return False
    return True
