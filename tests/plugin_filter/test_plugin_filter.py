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

from conftests import tmp_app, tmp_db, client
from tests.plugin_filter.util import (
    create_tags,
    create_plugins,
    create_or_update_plugin,
    compare_plugins,
    extract_key,
    filter_strategy,
    create_template,
    create_template_tab,
    filter_matches_plugin,
)
from qhana_plugin_registry.db.models.templates import TemplateTab
from qhana_plugin_registry.db.models.plugins import RAMP
from qhana_plugin_registry.tasks.plugin_filter import apply_filter_for_tab

from hypothesis import given, settings, HealthCheck, strategies as st
import random
from packaging.specifiers import Specifier
from packaging.version import Version, InvalidVersion


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=st.text())
def test_plugin_filter_name(tmp_db, client, name: str):
    template_id = create_template(tmp_db)
    create_plugins(tmp_db, [])
    plugin_id = create_or_update_plugin(tmp_db, name=name)
    plugin = tmp_db.session.query(RAMP).filter(RAMP.id == plugin_id).first()
    template_tab_id = create_template_tab(
        tmp_db, client, template_id=template_id, tab_name=name, filter_dict={"name": name}
    )
    template_tab = (
        tmp_db.session.query(TemplateTab)
        .filter(TemplateTab.id == template_tab_id)
        .first()
    )
    assert len(template_tab.plugins) == 1
    compare_plugins(template_tab.plugins[0], plugin)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(tag_name=st.text())
def test_plugin_filter_tag(tmp_db, client, tag_name: str):
    template_id = create_template(tmp_db)
    create_plugins(tmp_db, create_tags(tmp_db))
    tag = create_tags(tmp_db, [tag_name])[0]
    plugin_id = create_or_update_plugin(tmp_db, tags=[tag])
    plugin = tmp_db.session.query(RAMP).filter(RAMP.id == plugin_id).first()
    template_tab_id = create_template_tab(
        tmp_db, client, template_id=template_id, filter_dict={"tag": tag_name}
    )
    template_tab = (
        tmp_db.session.query(TemplateTab)
        .filter(TemplateTab.id == template_tab_id)
        .first()
    )
    assert len(template_tab.plugins) == 1
    compare_plugins(template_tab.plugins[0], plugin)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(version_spec=st.from_regex(Specifier._regex))
def test_plugin_filter_version(tmp_db, client, version_spec: str):
    spec = Specifier(version_spec)
    version = (
        version_spec.removeprefix("~=")
        .removeprefix("==")
        .removeprefix("!=")
        .removeprefix("<=")
        .removeprefix(">=")
        .removeprefix("<")
        .removeprefix(">")
        .removeprefix("===")
    )
    try:
        version = str(Version(version))
    except InvalidVersion:
        version = "0.0.0"
    template_id = create_template(tmp_db)
    create_plugins(tmp_db, [])
    plugin_id = create_or_update_plugin(tmp_db, version=version)
    plugin = tmp_db.session.query(RAMP).filter(RAMP.id == plugin_id).first()
    template_tab_id = create_template_tab(
        tmp_db, client, template_id=template_id, filter_dict={"version": version_spec}
    )
    template_tab = (
        tmp_db.session.query(TemplateTab)
        .filter(TemplateTab.id == template_tab_id)
        .first()
    )
    plugins = tmp_db.session.query(RAMP).all()
    plugin_ids = [p.id for p in template_tab.plugins]
    for plugin in plugins:
        if spec.contains(Version(plugin.version)):
            assert plugin.id in plugin_ids
        else:
            assert plugin.id not in plugin_ids


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(filter_dict=st.deferred(filter_strategy))
def test_plugin_filter(tmp_db, client, filter_dict: dict):
    template_id = create_template(tmp_db)

    # add tags
    tag_names = list(extract_key("tag", filter_dict))
    tags = create_tags(tmp_db, tag_names)

    # add plugins
    plugin_names = extract_key("name", filter_dict)
    versions = list(extract_key("version", filter_dict))
    for plugin in plugin_names:
        for version in versions:
            for tag in tags:
                plugin_tags = random.choices(tags, k=random.randint(0, len(tags)))
                create_or_update_plugin(
                    tmp_db,
                    name=plugin,
                    version=version,
                    tags=(plugin_tags + [tag]) if tag not in plugin_tags else plugin_tags,
                )

    # add template tab
    template_tab_id = create_template_tab(
        tmp_db, client, template_id=template_id, filter_dict=filter_dict
    )
    apply_filter_for_tab.apply(args=(template_tab_id,))

    template_tab = (
        tmp_db.session.query(TemplateTab)
        .filter(TemplateTab.id == template_tab_id)
        .first()
    )
    plugins = tmp_db.session.query(RAMP).all()
    plugin_ids = [p.id for p in template_tab.plugins]

    for plugin in plugins:
        if filter_matches_plugin(filter_dict, plugin):
            assert plugin.id in plugin_ids
        else:
            assert plugin.id not in plugin_ids
