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
from qhana_plugin_registry.tasks.plugin_filter import PLUGIN_NAME_MATCHING_THREASHOLD

from hypothesis import given, settings, HealthCheck, strategies as st
import random
from packaging.specifiers import Specifier
from packaging.version import Version
import pytest
from sqlalchemy.sql import exists
from difflib import SequenceMatcher


@pytest.fixture(scope="function")
def template(tmp_db):
    """Fixture for the test template."""

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
    """Fixture for the test template tab."""

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
    """Fixture for dummy plugins."""

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
    plugin_versions = {"1.0.0", "1.0.1", "1.1.0", "2.0.0", "2.0.1"}
    plugin_tag_names = tuple(f"test_tag_{i}" for i in range(5))
    plugin_tags = PluginTag.get_or_create_all(plugin_tag_names)

    for name, version, tag in zip(plugin_names, plugin_versions, plugin_tags):
        plugin_exists = tmp_db.session.query(
            exists().where(RAMP.name == name).where(RAMP.version == version)
        ).scalar()
        if not plugin_exists:
            create_plugin(tmp_db, name=name, version=version)

    yield tmp_db.session.query(RAMP).all()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=500)
@given(plugin_id=st.text(min_size=1))
def test_plugin_filter_id(tmp_db, client, template_tab, plugins, plugin_id: str):
    """
    Test plugin filtering by id.

    The health check is disabled because the test database and client fixtures are not reset between examples generated by `@given(...)`.
    See https://hypothesis.readthedocs.io/en/latest/healthchecks.html#hypothesis.HealthCheck.function_scoped_fixture for more information.
    """

    # create plugin
    plugin_exists = tmp_db.session.query(
        exists().where(RAMP.plugin_id == plugin_id)
    ).scalar()
    if not plugin_exists:
        create_plugin(tmp_db, plugin_id=plugin_id)

    # test single id filter
    filter_dict = {"id": plugin_id}
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)
    filtered_plugin_ids = {
        p_id
        for p_id, in tmp_db.session.query(RAMP.id)
        .filter(RAMP.plugin_id == plugin_id)
        .all()
    }
    assert (
        len(tab_plugin_ids) > 0
    ), f"filtering by a single plugin id failed (filter: '{filter_dict}')"
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by a single plugin id failed (filter: '{filter_dict}')"

    # test multiple id filters
    additional_id = random.choice(plugins).plugin_id
    filter_dict = {"or": [{"id": plugin_id}, {"id": additional_id}]}
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)
    filtered_plugin_ids = {
        p_id
        for p_id, in tmp_db.session.query(RAMP.id)
        .filter(RAMP.plugin_id.in_([plugin_id, additional_id]))
        .all()
    }
    assert (
        len(tab_plugin_ids) > 0
    ), f"filtering by multiple plugin ids failed (filter: '{filter_dict}')"
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by multiple plugin ids failed (filter: '{filter_dict}')"


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=500)
@given(
    plugin_id_without_version=st.text(min_size=1), version=st.from_regex(Version._regex)
)
def test_plugin_filter_id_without_version(
    tmp_db, client, template_tab, plugins, plugin_id_without_version: str, version: str
):
    """
    Test plugin filtering by id (without version).

    The health check is disabled because the test database and client fixtures are not reset between examples generated by `@given(...)`.
    See https://hypothesis.readthedocs.io/en/latest/healthchecks.html#hypothesis.HealthCheck.function_scoped_fixture for more information.
    """

    # create plugin
    plugin_id = f"{plugin_id_without_version}@{version}"
    plugin_exists = tmp_db.session.query(
        exists().where(RAMP.plugin_id == plugin_id)
    ).scalar()
    if not plugin_exists:
        create_plugin(
            tmp_db, plugin_id=plugin_id, name=plugin_id_without_version, version=version
        )

    # test single id filter
    filter_dict = {"id": plugin_id_without_version}
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)

    filtered_plugin_ids = set()
    # plugin ids must be compared in python because the test database is not configured for utf-8 characters
    for p_id, compare_id in tmp_db.session.query(RAMP.id, RAMP.plugin_id).all():
        compare_id_without_version = "@".join(compare_id.split("@")[:-1])
        if compare_id_without_version == plugin_id_without_version:
            filtered_plugin_ids.add(p_id)

    assert (
        len(tab_plugin_ids) > 0
    ), f"filtering by a single plugin id (without version) failed (filter: '{filter_dict}')"
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by a single plugin id (without version) failed (filter: '{filter_dict}')"


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=500)
@given(name=st.text(min_size=1))
def test_plugin_filter_name(tmp_db, client, template_tab, plugins, name: str):
    """
    Test plugin filtering by name.

    The health check is disabled because the test database and client fixtures are not reset between examples generated by `@given(...)`.
    See https://hypothesis.readthedocs.io/en/latest/healthchecks.html#hypothesis.HealthCheck.function_scoped_fixture for more information.
    """

    # create plugin
    plugin_exists = tmp_db.session.query(exists().where(RAMP.name == name)).scalar()
    if not plugin_exists:
        create_plugin(tmp_db, name=name)

    # test single name filter
    filter_dict = {"name": name}
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)
    filtered_plugin_ids = set()
    for p_id, p_name in tmp_db.session.query(RAMP.id, RAMP.name).all():
        sm = SequenceMatcher(None, p_name, name)
        if sm.ratio() > PLUGIN_NAME_MATCHING_THREASHOLD:
            filtered_plugin_ids.add(p_id)

    assert (
        len(tab_plugin_ids) > 0
    ), f"filtering by a single name failed (filter: '{filter_dict}')"
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by a single name failed (filter: '{filter_dict}')"

    # test single name excluded filter
    filter_dict = {"not": {"name": name}}
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)
    filtered_plugin_ids = set()
    for p_id, p_name in tmp_db.session.query(RAMP.id, RAMP.name).all():
        sm = SequenceMatcher(None, p_name, name)
        if sm.ratio() <= PLUGIN_NAME_MATCHING_THREASHOLD:
            filtered_plugin_ids.add(p_id)

    assert (
        len(tab_plugin_ids) > 0
    ), f"filtering by a single name failed (filter: '{filter_dict}')"
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by a single name failed (filter: '{filter_dict}')"

    # test multiple name filters
    additional_name = random.choice(plugins).name
    filter_dict = {"or": [{"name": name}, {"name": additional_name}]}
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)
    filtered_plugin_ids = set()
    for p_id, p_name in tmp_db.session.query(RAMP.id, RAMP.name).all():
        sm1 = SequenceMatcher(None, p_name, name)
        sm2 = SequenceMatcher(None, p_name, additional_name)
        if (
            sm1.ratio() > PLUGIN_NAME_MATCHING_THREASHOLD
            or sm2.ratio() > PLUGIN_NAME_MATCHING_THREASHOLD
        ):
            filtered_plugin_ids.add(p_id)

    assert (
        len(tab_plugin_ids) > 0
    ), f"filtering by multiple names failed (filter: '{filter_dict}')"
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by multiple names failed (filter: '{filter_dict}')"


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(tag_name=st.text(min_size=1))
def test_plugin_filter_tag(tmp_db, client, template_tab, plugins, tag_name: str):
    """
    Test plugin filtering by tags.

    The health check is disabled because the test database and client fixtures are not reset between examples generated by `@given(...)`.
    See https://hypothesis.readthedocs.io/en/latest/healthchecks.html#hypothesis.HealthCheck.function_scoped_fixture for more information.
    """

    # add/update plugin with tag
    additional_tag = (
        tmp_db.session.query(PluginTag).filter(PluginTag.tag == "test_tag_1").first()
    )
    tag = PluginTag.get_or_create(tag_name)

    n_plugins = tmp_db.session.query(RAMP).count()
    plugin_name = f"test_tag_plugin_{n_plugins}"
    create_plugin(tmp_db, name=plugin_name, tags=[tag, additional_tag])

    # test single tag filter
    filter_dict = {"tag": tag_name}
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)
    filtered_plugin_ids = {
        p_id
        for p_id, in tmp_db.session.query(RAMP.id)
        .filter(RAMP.tags.any(PluginTag.tag == tag_name))
        .all()
    }
    assert (
        len(tab_plugin_ids) > 0
    ), f"filtering by a single tag failed (filter: '{filter_dict}')"
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by a single tag failed (filter: '{filter_dict}')"

    # test single tag excluded filter
    filter_dict = {"not": {"tag": tag_name}}
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)
    filtered_plugin_ids = {
        p_id
        for p_id, in tmp_db.session.query(RAMP.id)
        .filter(~RAMP.tags.any(PluginTag.tag == tag_name))
        .all()
    }
    assert (
        len(tab_plugin_ids) > 0
    ), f"filtering by a single tag failed (filter: '{filter_dict}')"
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by a single tag failed (filter: '{filter_dict}')"

    # test multiple tag filters
    filter_dict = {"or": [{"tag": tag_name}, {"tag": additional_tag.tag}]}
    tab_plugin_ids = update_plugin_filter(
        tmp_db,
        client,
        template_tab,
        filter_dict,
    )
    filtered_plugin_ids = {
        p_id
        for p_id, in tmp_db.session.query(RAMP.id)
        .filter(RAMP.tags.any(PluginTag.tag.in_([tag_name, additional_tag.tag])))
        .all()
    }
    assert (
        len(tab_plugin_ids) > 0
    ), f"filtering by multiple tags failed (filter: '{filter_dict}')"
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by multiple tags failed (filter: '{filter_dict}')"

    filter_dict = {"and": [{"tag": tag_name}, {"tag": additional_tag.tag}]}
    tab_plugin_ids = update_plugin_filter(
        tmp_db,
        client,
        template_tab,
        filter_dict,
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
    assert (
        len(tab_plugin_ids) > 0
    ), f"filtering by multiple tags failed (filter: '{filter_dict}')"
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by multiple tags failed (filter: '{filter_dict}')"


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=500)
@given(version_spec=st.from_regex(Specifier._regex))
def test_plugin_filter_version(tmp_db, client, template_tab, plugins, version_spec: str):
    """
    Test plugin filtering by versions.

    The health check is disabled because the test database and client fixtures are not reset between examples generated by `@given(...)`.
    See https://hypothesis.readthedocs.io/en/latest/healthchecks.html#hypothesis.HealthCheck.function_scoped_fixture for more information.
    """

    spec = Specifier(version_spec)
    db_plugins = tmp_db.session.query(RAMP).all()

    # test single version filter
    filter_dict = {"version": version_spec}
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)
    filtered_plugin_ids = {p.id for p in db_plugins if spec.contains(p.version)}
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by a single version failed (filter: '{filter_dict}')"

    # test single version excluded filter
    filter_dict = {"not": {"version": version_spec}}
    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)
    filtered_plugin_ids = {p.id for p in db_plugins if not spec.contains(p.version)}
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by a single version failed (filter: '{filter_dict}')"

    # test multiple version filters
    zero_spec = Specifier(f"=={plugins[-1].version}")
    filter_dict = {"or": [{"version": version_spec}, {"version": str(zero_spec)}]}
    tab_plugin_ids = update_plugin_filter(
        tmp_db,
        client,
        template_tab,
        filter_dict,
    )
    filtered_plugin_ids = {
        p.id
        for p in db_plugins
        if spec.contains(p.version) or zero_spec.contains(p.version)
    }
    assert (
        len(tab_plugin_ids) > 0
    ), f"filtering by multiple versions failed (filter: '{filter_dict}')"
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by multiple versions failed (filter: '{filter_dict}')"

    zero_spec = Specifier(f"!={plugins[-1].version}")
    filter_dict = {"and": [{"version": version_spec}, {"version": str(zero_spec)}]}
    tab_plugin_ids = update_plugin_filter(
        tmp_db,
        client,
        template_tab,
        filter_dict,
    )
    filtered_plugin_ids = {
        p.id
        for p in db_plugins
        if spec.contains(p.version) and zero_spec.contains(p.version)
    }
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering by multiple versions failed (filter: '{filter_dict}')"


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=500)
@given(filter_dict=st.deferred(filter_strategy))
def test_plugin_filter(tmp_db, client, template_tab, plugins, filter_dict: dict):
    """
    Test general plugin filtering.

    The health check is disabled because the test database and client fixtures are not reset between examples generated by `@given(...)`.
    See https://hypothesis.readthedocs.io/en/latest/healthchecks.html#hypothesis.HealthCheck.function_scoped_fixture for more information.
    """

    # test single tag filter
    db_plugins = tmp_db.session.query(RAMP).all()

    tab_plugin_ids = update_plugin_filter(tmp_db, client, template_tab, filter_dict)
    filtered_plugin_ids = {
        p.id for p in db_plugins if filter_matches_plugin(filter_dict, p)
    }
    assert (
        tab_plugin_ids == filtered_plugin_ids
    ), f"filtering failed (filter: '{filter_dict}')"
