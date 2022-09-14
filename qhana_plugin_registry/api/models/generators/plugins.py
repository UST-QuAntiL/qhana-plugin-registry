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

"""Generators for all Plugin resources."""

from typing import Dict, Iterable, Optional

from flask import url_for

from .constants import (
    API_SPEC_RESOURCE,
    COLLECTION_REL,
    ITEM_COUNT_DEFAULT,
    ITEM_COUNT_QUERY_KEY,
    NAV_REL,
    PAGE_REL,
    PAGE_SCHEMA,
    PLUGIN_ID_KEY,
    ROOT_RESOURCE_DUMMY,
    UP_REL,
)
from .type_map import TYPE_TO_METADATA
from ..base_models import ApiLink, ApiResponse
from ..plugins import PluginData
from ..request_helpers import (
    ApiObjectGenerator,
    ApiResponseGenerator,
    KeyGenerator,
    LinkGenerator,
    PageResource,
)
from ....db.models.plugins import RAMP

# Plugin Page ##################################################################


class PluginPageKeyGenerator(KeyGenerator, resource_type=RAMP, page=True):
    def update_key(self, key: Dict[str, str], resource: PageResource) -> Dict[str, str]:
        parent_resource = resource.resource or ROOT_RESOURCE_DUMMY
        parent_key = KeyGenerator.generate_key(parent_resource)
        key.update(parent_key)
        return key


class PluginPageLinkGenerator(LinkGenerator, resource_type=RAMP, page=True):
    def generate_link(
        self,
        resource: PageResource,
        *,
        query_params: Optional[Dict[str, str]],
        ignore_deleted: bool = False,
    ) -> Optional[ApiLink]:
        if query_params is None:
            query_params = {ITEM_COUNT_QUERY_KEY: ITEM_COUNT_DEFAULT}

        meta = TYPE_TO_METADATA[RAMP]

        endpoint = meta.collection_endpoint
        assert endpoint is not None

        return ApiLink(
            href=url_for(endpoint, **query_params, _external=True),
            rel=(COLLECTION_REL, PAGE_REL),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource, query_params=query_params),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True)}#/components/schemas/{PAGE_SCHEMA}",
        )


class PluginPageUpLinkGenerator(
    LinkGenerator, resource_type=RAMP, page=True, relation=UP_REL
):
    def generate_link(
        self,
        resource: PageResource,
        *,
        query_params: Optional[Dict[str, str]] = None,
        ignore_deleted: bool = False,
    ) -> Optional[ApiLink]:
        parent_resource = resource.resource or ROOT_RESOURCE_DUMMY
        link = LinkGenerator.get_link_of(parent_resource, query_params=query_params)
        assert link is not None
        link.rel = (UP_REL,)
        return link


# Plugin #######################################################################


class PluginKeyGenerator(KeyGenerator, resource_type=RAMP):
    def update_key(self, key: Dict[str, str], resource: RAMP) -> Dict[str, str]:
        assert isinstance(resource, RAMP)
        parent_key = KeyGenerator.generate_key(PageResource(RAMP, page_number=1))
        key.update(parent_key)
        key[PLUGIN_ID_KEY] = str(resource.id)
        return key


class PluginSelfLinkGenerator(LinkGenerator, resource_type=RAMP):
    def generate_link(
        self,
        resource: RAMP,
        *,
        query_params: Optional[Dict[str, str]] = None,
        ignore_deleted: bool = False,
    ) -> Optional[ApiLink]:
        meta = TYPE_TO_METADATA[RAMP]

        return ApiLink(
            href=url_for(meta.endpoint, plugin_id=str(resource.id), _external=True),
            rel=tuple(),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True)}#/components/schemas/{meta.schema_id}",
        )


class PluginUpLinkGenerator(LinkGenerator, resource_type=RAMP, relation=UP_REL):
    def generate_link(
        self,
        resource: RAMP,
        *,
        query_params: Optional[Dict[str, str]] = None,
        ignore_deleted: bool = False,
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            PageResource(RAMP, page_number=1),
            extra_relations=(UP_REL,),
        )


class PluginApiObjectGenerator(ApiObjectGenerator, resource_type=RAMP):
    def generate_api_object(
        self,
        resource: RAMP,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[PluginData]:
        assert isinstance(resource, RAMP)

        self_link = LinkGenerator.get_link_of(resource)

        assert self_link is not None

        return PluginData(self=self_link, title=resource.name)  # FIXME, better conversion


class PluginApiResponseGenerator(ApiResponseGenerator, resource_type=RAMP):
    def generate_api_response(
        self, resource: RAMP, *, link_to_relations: Optional[Iterable[str]], **kwargs
    ) -> Optional[ApiResponse]:
        meta = TYPE_TO_METADATA[RAMP]
        link_to_relations = (
            meta.extra_link_rels if link_to_relations is None else link_to_relations
        )
        return ApiResponseGenerator.default_generate_api_response(
            resource, link_to_relations=link_to_relations, **kwargs
        )
