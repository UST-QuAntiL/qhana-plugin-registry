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

from conftests import tmp_app, tmp_db, client
from tests.plugin_filter.util import (
    create_plugin,
    filter_strategy,
    filter_matches_plugin,
    update_plugin_filter,
)
from qhana_plugin_registry.db.models.templates import TemplateTab, UiTemplate
from qhana_plugin_registry.db.models.plugins import RAMP, PluginTag

from hypothesis import given, settings, HealthCheck, strategies as st
import random
from packaging.specifiers import Specifier
from packaging.version import Version
import pytest
from sqlalchemy.sql import exists


@pytest.fixture(scope="function")
def template(tmp_db):
    template = UiTemplate(
        name="test_template",
        description="test template",
    )
    tmp_db.session.add(template)
    tmp_db.session.commit()
    yield tmp_db.session.query(UiTemplate).filter(
        UiTemplate.name == template.name
    ).first()


@pytest.fixture(scope="function")
def template_tab(tmp_db, template):
    template_tab = TemplateTab(
        name="test_tab",
        description="test tab",
        template=template,
        location="workspace",
    )
    tmp_db.session.add(template_tab)
    tmp_db.session.commit()
    return (
        tmp_db.session.query(TemplateTab)
        .filter(TemplateTab.name == template_tab.name)
        .first()
    )


@pytest.fixture(scope="function")
def plugins(tmp_db):
    # add plugins generated by hypothesis
    plugin_names = st.lists(st.text(min_size=1), min_size=1).example()
    plugin_versions = st.lists(st.from_regex(Version._regex), min_size=1).example()
    plugin_tag_names = tuple(set(st.lists(st.text(min_size=1), min_size=1).example()))
    plugin_tags = PluginTag.get_or_create_all(plugin_tag_names)

    for tag in plugin_tags:
        p_tags = random.sample(plugin_tags, random.randint(0, len(plugin_tags) - 1))
        if tag not in p_tags:
            p_tags.append(tag)
        for name in plugin_names:
            for version in plugin_versions:
                plugin_exists = tmp_db.session.query(
                    exists().where(RAMP.name == name).where(RAMP.version == version)
                ).scalar()
                if not plugin_exists:
                    create_plugin(tmp_db, name=name, version=version, tags=p_tags)

    # add fixed plugins
    plugin_names = {f"test_plugin_{i}" for i in range(5)}
    plugin_versions = {"1.0.0", "1.0.1", "1.1.0", "2.0.0"}
    plugin_tag_names = tuple(f"test_tag_{i}" for i in range(5))
    plugin_tags = PluginTag.get_or_create_all(plugin_tag_names)

    for name, version, tag in zip(plugin_names, plugin_versions, plugin_tags):
        plugin_exists = tmp_db.session.query(
            exists().where(RAMP.name == name).where(RAMP.version == version)
        ).scalar()
        if not plugin_exists:
            create_plugin(tmp_db, name=name, version=version)

    yield tmp_db.session.query(RAMP).all()


"""
Test plugin filtering by name.

The health check is disabled because the test database and client fixtures are not reset between examples generated by `@given(...)`. 
See https://hypothesis.readthedocs.io/en/latest/healthchecks.html#hypothesis.HealthCheck.function_scoped_fixture for more information.
"""


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=500)
@given(name=st.text(min_size=1))
def test_plugin_filter_name(tmp_db, client, template_tab, plugins, name: str):
    # create plugin
    plugin_exists = tmp_db.session.query(exists().where(RAMP.name == name)).scalar()
    if not plugin_exists:
        create_plugin(tmp_db, name=name)

    # test single name filter
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, {"name": name})
    filtered_plugin_ids = {
        p_id for p_id, in tmp_db.session.query(RAMP.id).filter(RAMP.name == name).all()
    }
    assert len(tab_plugin_ids) > 0
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids

    # test single name excluded filter
    tab_plugin_ids = update_plugin_filter(
        tmp_db, client, template_tab, {"not": {"name": name}}
    )
    filtered_plugin_ids = {
        p_id for p_id, in tmp_db.session.query(RAMP.id).filter(RAMP.name != name).all()
    }
    assert len(tab_plugin_ids) > 0
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids

    # test multiple name filters
    additional_name = random.choice(plugins).name
    tab_plugin_ids = update_plugin_filter(
        tmp_db, client, template_tab, {"or": [{"name": name}, {"name": additional_name}]}
    )
    filtered_plugin_ids = {
        p_id
        for p_id, in tmp_db.session.query(RAMP.id)
        .filter(RAMP.name.in_([name, additional_name]))
        .all()
    }
    assert len(tab_plugin_ids) > 0
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids


"""
Test plugin filtering by tags.

The health check is disabled because the test database and client fixtures are not reset between examples generated by `@given(...)`. 
See https://hypothesis.readthedocs.io/en/latest/healthchecks.html#hypothesis.HealthCheck.function_scoped_fixture for more information.
"""


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(tag_name=st.text(min_size=1))
def test_plugin_filter_tag(tmp_db, client, template_tab, plugins, tag_name: str):
    # add/update plugin with tag
    additional_tag = (
        tmp_db.session.query(PluginTag).filter(PluginTag.tag == "test_tag_1").first()
    )
    tag = PluginTag.get_or_create(tag_name)

    n_plugins = tmp_db.session.query(RAMP).count()
    plugin_name = f"test_tag_plugin_{n_plugins}"
    create_plugin(tmp_db, name=plugin_name, tags=[tag, additional_tag])

    # test single tag filter
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, {"tag": tag_name})
    filtered_plugin_ids = {
        p_id
        for p_id, in tmp_db.session.query(RAMP.id)
        .filter(RAMP.tags.any(PluginTag.tag == tag_name))
        .all()
    }
    assert len(tab_plugin_ids) > 0
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids

    # test single tag excluded filter
    tab_plugin_ids = update_plugin_filter(
        tmp_db, client, template_tab, {"not": {"tag": tag_name}}
    )
    filtered_plugin_ids = {
        p_id
        for p_id, in tmp_db.session.query(RAMP.id)
        .filter(~RAMP.tags.any(PluginTag.tag == tag_name))
        .all()
    }
    assert len(tab_plugin_ids) > 0
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids

    # test multiple tag filters
    tab_plugin_ids = update_plugin_filter(
        tmp_db,
        client,
        template_tab,
        {"or": [{"tag": tag_name}, {"tag": additional_tag.tag}]},
    )
    filtered_plugin_ids = {
        p_id
        for p_id, in tmp_db.session.query(RAMP.id)
        .filter(RAMP.tags.any(PluginTag.tag.in_([tag_name, additional_tag.tag])))
        .all()
    }
    assert len(tab_plugin_ids) > 0
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids

    tab_plugin_ids = update_plugin_filter(
        tmp_db,
        client,
        template_tab,
        {"and": [{"tag": tag_name}, {"tag": additional_tag.tag}]},
    )
    filtered_plugin_ids = {
        p_id
        for p_id, in tmp_db.session.query(RAMP.id)
        .filter(
            RAMP.tags.any(PluginTag.tag == tag_name)
            & RAMP.tags.any(PluginTag.tag == additional_tag.tag)
        )
        .all()
    }
    assert len(tab_plugin_ids) > 0
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids


"""
Test plugin filtering by versions.

The health check is disabled because the test database and client fixtures are not reset between examples generated by `@given(...)`. 
See https://hypothesis.readthedocs.io/en/latest/healthchecks.html#hypothesis.HealthCheck.function_scoped_fixture for more information.
"""


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=500)
@given(version_spec=st.from_regex(Specifier._regex))
def test_plugin_filter_version(tmp_db, client, template_tab, plugins, version_spec: str):
    spec = Specifier(version_spec)
    db_plugins = tmp_db.session.query(RAMP).all()

    # test single version filter
    tab_plugin_ids = update_plugin_filter(
        tmp_db, client, template_tab, {"version": version_spec}
    )
    filtered_plugin_ids = {p.id for p in db_plugins if spec.contains(p.version)}
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids

    # test single version excluded filter
    tab_plugin_ids = update_plugin_filter(
        tmp_db, client, template_tab, {"not": {"version": version_spec}}
    )
    filtered_plugin_ids = {p.id for p in db_plugins if not spec.contains(p.version)}
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids

    # test multiple version filters
    zero_spec = Specifier(f"=={plugins[-1].version}")
    tab_plugin_ids = update_plugin_filter(
        tmp_db,
        client,
        template_tab,
        {"or": [{"version": version_spec}, {"version": str(zero_spec)}]},
    )
    filtered_plugin_ids = {
        p.id
        for p in db_plugins
        if spec.contains(p.version) or zero_spec.contains(p.version)
    }
    assert len(tab_plugin_ids) > 0
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids

    zero_spec = Specifier(f"!={plugins[-1].version}")
    tab_plugin_ids = update_plugin_filter(
        tmp_db,
        client,
        template_tab,
        {"and": [{"version": version_spec}, {"version": str(zero_spec)}]},
    )
    filtered_plugin_ids = {
        p.id
        for p in db_plugins
        if spec.contains(p.version) and zero_spec.contains(p.version)
    }
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids


"""
Test general plugin filtering.

The health check is disabled because the test database and client fixtures are not reset between examples generated by `@given(...)`.
See https://hypothesis.readthedocs.io/en/latest/healthchecks.html#hypothesis.HealthCheck.function_scoped_fixture for more information.
"""


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=500)
@given(filter_dict=st.deferred(filter_strategy))
def test_plugin_filter(tmp_db, client, template_tab, plugins, filter_dict: dict):
    # test single tag filter
    db_plugins = tmp_db.session.query(RAMP).all()

    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)
    filtered_plugin_ids = {
        p.id for p in db_plugins if filter_matches_plugin(filter_dict, p)
    }
    assert len(tab_plugin_ids) == len(filtered_plugin_ids)
    for plugin_id in tab_plugin_ids:
        assert plugin_id in filtered_plugin_ids
