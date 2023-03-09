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
from qhana_plugin_registry.db.models.templates import UiTemplate, TemplateTab
from qhana_plugin_registry.tasks.plugin_filter import apply_filter_for_tab

import random
from hypothesis import strategies as st
from packaging.specifiers import Specifier
import json
from sqlalchemy.sql import exists


def filter_strategy():
    return st.one_of(
        st.fixed_dictionaries({"tag": st.text()}),
        st.fixed_dictionaries({"name": st.text()}),
        st.fixed_dictionaries(
            {"version": st.from_regex(Specifier._regex)}
        ),  # TODO: type PEP 0440 version specifier
        st.fixed_dictionaries({"and": st.lists(st.deferred(filter_strategy))}),
        st.fixed_dictionaries({"or": st.lists(st.deferred(filter_strategy))}),
        st.fixed_dictionaries({"not": st.deferred(filter_strategy)}),
    )


def extract_key(key: str, filter_dict: dict):
    if key in filter_dict:
        yield filter_dict[key]
    for k, v in filter_dict.items():
        if k in ["and", "or"]:
            for sub_filter in v:
                extract_key(key, sub_filter)
        if k == "not":
            extract_key(key, v)


def create_template(
    tmp_db, name: str = "test_template", description: str = "test template"
) -> str:
    template_exists = tmp_db.session.query(
        exists().where(UiTemplate.name == name)
    ).scalar()
    if template_exists:
        return tmp_db.session.query(UiTemplate.id).first()[0]
    template = UiTemplate(
        name=name,
        description=description,
    )
    tmp_db.session.add(template)
    tmp_db.session.commit()
    template_id = (
        tmp_db.session.query(UiTemplate.id)
        .filter(UiTemplate.name == template.name)
        .first()[0]
    )
    return template_id


def create_or_update_plugin(
    tmp_db,
    name: str = "test-plugin",
    version: str = "0.0.0",
    tags: list[PluginTag] | None = None,
    description: str = "descr",
) -> RAMP:
    if not tags:
        tags = []
    plugin_exists = tmp_db.session.query(
        exists().where(RAMP.name == name, RAMP.version == version)
    ).scalar()
    if plugin_exists:
        plugin = (
            tmp_db.session.query(RAMP)
            .filter(RAMP.name == name, RAMP.version == version)
            .first()
        )
        plugin.plugin_id = f"{name}@{version}"
        plugin.name = name
        plugin.version = version
        plugin.tags = tags
        plugin.description = description
        tmp_db.session.commit()
        plugin_id = (
            tmp_db.session.query(RAMP.id)
            .filter(RAMP.name == name, RAMP.version == version)
            .first()[0]
        )
        return plugin_id
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


def create_plugins(
    tmp_db, tags: list[PluginTag], versions: list[str] = ["1.0.0", "1.1.0", "2.0.0"], n=3
) -> None:
    for i in range(n):
        create_or_update_plugin(
            tmp_db,
            name=f"p{i}",
            description=f"d{i}",
            version=f"{random.choice(versions)}",
            tags=[]
            if not tags
            else random.sample(tags, random.randint(1, len(tags) - 1)),
        )


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


def create_tags(tmp_db, tags: list[str] | None = None) -> list[PluginTag]:
    if not tags:
        plugin_tags = [PluginTag(f"t{tag}") for tag in range(5)]
        tags = [tag.tag for tag in plugin_tags]
    else:
        plugin_tags = [PluginTag(tag) for tag in tags]
    for tag in plugin_tags:
        tag_exists = tmp_db.session.query(
            exists().where(PluginTag.tag == tag.tag)
        ).scalar()
        if not tag_exists:
            tmp_db.session.add(tag)
    tmp_db.session.commit()
    return tmp_db.session.query(PluginTag).filter(PluginTag.tag.in_(tags)).all()


def compare_plugins(plugin: RAMP, other: RAMP):
    assert plugin.name == other.name
    assert plugin.description == other.description
    assert plugin.version == other.version
    assert plugin.plugin_id == other.plugin_id
    assert len(plugin.tags) == len(other.tags)
    assert all(tag in other.tags for tag in plugin.tags)


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
            return all(
                filter_matches_plugin(filter_dict, plugin) for filter_dict in and_filters
            )
        case {"or": or_filters}:
            return any(
                filter_matches_plugin(filter_dict, plugin) for filter_dict in or_filters
            )
        case {"not": not_filter}:
            return not filter_matches_plugin(not_filter, plugin)
        case _:
            return False
