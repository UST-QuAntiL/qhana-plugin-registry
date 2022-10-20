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

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, cast

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from packaging.version import parse as parse_version
from sqlalchemy.sql.expression import (
    ColumnElement,
    ColumnOperators,
    Select,
    distinct,
    select,
)
from sqlalchemy.sql.functions import count

from .db import DB
from .models.plugins import (
    DATA_RELATION_CONSUMED,
    DATA_RELATION_PRODUCED,
    RAMP,
    ContentTypeToData,
    DataToRAMP,
    DependencyToRAMP,
    PluginTag,
    TagToDependency,
    TagToRAMP,
)
from .models.seeds import Seed
from .models.services import Service


def filter_ramps_by_id_and_version(
    ramp_id: Optional[str] = None,
    version: Optional[str] = None,
    plugin_id_column: ColumnElement = cast(ColumnElement, RAMP.plugin_id),
    plugin_version_column: ColumnElement = cast(ColumnElement, RAMP.version),
) -> List[ColumnOperators]:
    """Generate a query filter to filter by plugin identifier string and version.

    Args:
        ramp_id (Optional[str], optional): the plugin identifier name (not the human readable title!) to filter for. Defaults to None.
        version (Optional[str], optional): a single version number or a version requirement to filter by (if a version requirement like >=1.0 is used ramp_id must also be set!). Defaults to None.
        plugin_id_column (ColumnElement, optional): the column to apply the ramp_id filter to (use only if aliases are used in the query). Defaults to RAMP.plugin_id.
        plugin_version_column (ColumnElement, optional): the column to apply the version filter to (use only if aliases are used in the query). Defaults to RAMP.version.

    Raises:
        ValueError: If a version filter with version requirements is set without a ramp_id filter

    Returns:
        List[ColumnOperators]: the filter expressions (to be joined by an and)
    """
    filter_: List[ColumnOperators] = []
    if ramp_id is not None:
        filter_.append(plugin_id_column == ramp_id)
    if version is None:
        return filter_
    is_single_version = isinstance(parse_version(version), Version)
    if is_single_version:
        filter_.append(plugin_version_column == version)
        return filter_

    if ramp_id is None:
        # filtering version numbers must happen on python side => we need to execute a quere beforehand
        # filtering for versions is only allowed for a single ramp ID to limit performance bottlenecks here
        raise ValueError(
            "The ramp_id must not be None if the version is a specifier string matching potentially multiple versions!"
        )

    specifier_str = re.sub(
        r"([^\s,])(\s+)", r"\1,\2", version
    )  # add commas to whitespace
    specifier = SpecifierSet(specifier_str)
    versions: List[str] = (
        DB.session.execute(select(RAMP.version).filter(RAMP.plugin_id == ramp_id))
        .scalars()
        .all()
    )
    allowed_versions = specifier.filter(versions)
    filter_.append(plugin_version_column.in_(allowed_versions))
    return filter_


def filter_ramps_by_tags(
    must_have_tags: Optional[Sequence[Union[PluginTag, int]]] = None,
    forbidden_tags: Optional[Sequence[Union[PluginTag, int]]] = None,
    ramp_id_column: ColumnElement = cast(ColumnElement, RAMP.id),
) -> List[ColumnOperators]:
    """Generate query filter expression to filter ramps by tags.

    Args:
        must_have_tags (Sequence[Union[PluginTag, int]], optional): a set of tags (or IDs) that must be present in the plugin. Defaults to None.
        forbidden_tags (Sequence[Union[PluginTag, int]], optional): a set of tags (or IDs) that must not be present in the plugin. Defaults to None.
        ramp_id_column (ColumnElement, optional): the column to apply the filter to (use only if aliases are used in the query). Defaults to RAMP.id.

    Returns:
        List[ColumnOperators]: the filter expressions (to be joined by an and)
    """
    filter_: List[ColumnOperators] = []
    if must_have_tags:
        # select all ramp ids that where the number of tags == the number of must have tags
        # and only must_have tags are counted
        q = (
            select(TagToRAMP.ramp_id)
            .filter(
                cast(ColumnElement, TagToRAMP.tag_id).in_(
                    [t if isinstance(t, int) else t.id for t in must_have_tags]
                )
            )
            .group_by(TagToRAMP.ramp_id)
            .having(count(TagToRAMP.tag_id) == len(must_have_tags))
        )
        filter_.append(ramp_id_column.in_(q))  # append a IN filter
    if forbidden_tags:
        # select all ramp ids that have one of the forbidden tags
        q = select(distinct(TagToRAMP.ramp_id)).filter(
            cast(ColumnElement, TagToRAMP.ramp_id).in_(
                [t if isinstance(t, int) else t.id for t in forbidden_tags]
            )
        )
        filter_.append(~ramp_id_column.in_(q))  # append a NOT IN filter
    return filter_


def filter_services_by_service_id(
    service_id: Optional[Union[str,Sequence[str]]] = None,
    service_id_column: ColumnElement = cast(ColumnElement, Service.service_id),
) -> List[ColumnOperators]:
    """Generate a query filter to filter by one or more service ids.

    Args:
        service_id (Optional[Union[str,Sequence[str]]], optional): the service id(s) (not the database ids!) to filter for. Defaults to None.
        service_id_column (ColumnElement, optional): the column to apply the filter to (use only if aliases are used in the query). Defaults to Service.service_id.

    Returns:
        List[ColumnOperators]: the filter expression (to be joined by an and)
    """
    if service_id is None:
        return []
    if isinstance(service_id, str):
        return [service_id_column == service_id]
    return [service_id_column.in_(service_id)]
