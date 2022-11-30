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

"""Generators for all Template Tab resources."""

from typing import Dict, Iterable, Optional

from flask import url_for

from .constants import (
    API_SPEC_RESOURCE,
    COLLECTION_REL,
    CREATE_REL,
    UPDATE_REL,
    DELETE_REL,
    ITEM_COUNT_DEFAULT,
    ITEM_COUNT_QUERY_KEY,
    NAV_REL,
    POST_REL,
    PUT_REL,
    ROOT_RESOURCE_DUMMY,
    TEMPLATE_TAB_ID_KEY,
    UP_REL,
    PLUGIN_REL_TYPE,
)
from .type_map import TYPE_TO_METADATA
from ..base_models import ApiLink, ApiResponse, CursorPageSchema
from ..request_helpers import (
    ApiObjectGenerator,
    ApiResponseGenerator,
    KeyGenerator,
    LinkGenerator,
    CollectionResource,
    PageResource,
)
from ..templates import TemplateTabData
from ..templates_raw import TemplateGroupRaw
from ....db.models.templates import TemplateTab, WorkspaceTemplate
from ....db.models.plugins import RAMP

# Template Page ################################################################


class TemplateTabPageKeyGenerator(KeyGenerator, resource_type=TemplateTab, page=True):
    def update_key(
        self, key: Dict[str, str], resource: CollectionResource
    ) -> Dict[str, str]:
        assert (
            resource.resource is not None
        ), "Tabs must have a Template as a parent resource!"
        parent_resource = resource.resource
        parent_key = KeyGenerator.generate_key(parent_resource)
        key.update(parent_key)
        return key


class TemplateTabPageLinkGenerator(LinkGenerator, resource_type=TemplateTab, page=True):
    def generate_link(
        self, resource: CollectionResource, *, query_params: Optional[Dict[str, str]]
    ) -> Optional[ApiLink]:
        assert isinstance(resource.resource, WorkspaceTemplate)
        if query_params is None:
            query_params = {ITEM_COUNT_QUERY_KEY: ITEM_COUNT_DEFAULT}

        meta = TYPE_TO_METADATA[TemplateTab]

        endpoint = meta.collection_endpoint
        assert endpoint is not None

        return ApiLink(
            href=url_for(
                endpoint,
                template_id=str(resource.resource.id),
                **query_params,
                _external=True,
            ),
            rel=(COLLECTION_REL,),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource, query_params=query_params),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True)}#/components/schemas/{CursorPageSchema.schema_name()}",
        )


class TemplateTabPageUpLinkGenerator(
    LinkGenerator, resource_type=TemplateTab, page=True, relation=UP_REL
):
    def generate_link(
        self,
        resource: CollectionResource,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        parent_resource = resource.resource or ROOT_RESOURCE_DUMMY
        link = LinkGenerator.get_link_of(parent_resource, query_params=query_params)
        assert link is not None
        link.rel = (UP_REL,)
        return link


class TemplateTabPageCreateTemplateLinkGenerator(
    LinkGenerator, resource_type=TemplateTab, page=True, relation=CREATE_REL
):
    def generate_link(
        self,
        resource: CollectionResource,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        link = LinkGenerator.get_link_of(resource)
        assert link is not None
        link.rel = (CREATE_REL, POST_REL)
        return link


# Template #####################################################################


class TemplateTabKeyGenerator(KeyGenerator, resource_type=TemplateTab):
    def update_key(self, key: Dict[str, str], resource: TemplateTab) -> Dict[str, str]:
        assert isinstance(resource, TemplateTab)
        template = resource.template
        assert template is not None
        parent_resource = TemplateGroupRaw(template, resource.location, [])
        parent_key = KeyGenerator.generate_key(parent_resource)
        key.update(parent_key)
        key[TEMPLATE_TAB_ID_KEY] = str(resource.id)
        return key


class TemplateTabSelfLinkGenerator(LinkGenerator, resource_type=TemplateTab):
    def generate_link(
        self,
        resource: TemplateTab,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        meta = TYPE_TO_METADATA[TemplateTab]

        return ApiLink(
            href=url_for(
                meta.endpoint,
                template_id=str(resource.template_id),
                tab_id=str(resource.id),
                _external=True,
            ),
            rel=tuple(),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True)}#/components/schemas/{meta.schema_id}",
            name=resource.name,
        )


class TemplateTabUpLinkGenerator(
    LinkGenerator, resource_type=TemplateTab, relation=UP_REL
):
    def generate_link(
        self,
        resource: TemplateTab,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        template = resource.template
        assert template is not None
        parent_resource = TemplateGroupRaw(template, resource.location, [])
        return LinkGenerator.get_link_of(
            parent_resource,
            extra_relations=(UP_REL,),
        )


class UpdateTemplateTabLinkGenerator(
    LinkGenerator, resource_type=TemplateTab, relation=UPDATE_REL
):  # TODO check action relation
    def generate_link(
        self,
        resource: TemplateTab,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        link = LinkGenerator.get_link_of(resource)
        if link is None:
            return None
        link.rel = (UPDATE_REL, PUT_REL)  # TODO check rels
        return link


class DeleteTemplateTabLinkGenerator(
    LinkGenerator, resource_type=TemplateTab, relation=DELETE_REL
):
    def generate_link(
        self,
        resource: TemplateTab,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        link = LinkGenerator.get_link_of(resource)
        if link is None:
            return None
        link.rel = (DELETE_REL,)
        return link


class TemplateTabToPluginsNavLinkGenerator(
    LinkGenerator, resource_type=TemplateTab, relation=PLUGIN_REL_TYPE
):
    def generate_link(
        self,
        resource: TemplateTab,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            PageResource(RAMP),
            query_params={"template-tab": str(resource.id)},
            extra_relations=(NAV_REL,),
        )


class TemplateTabApiObjectGenerator(ApiObjectGenerator, resource_type=TemplateTab):
    def generate_api_object(
        self,
        resource: TemplateTab,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[TemplateTabData]:
        assert isinstance(resource, TemplateTab)

        self_link = LinkGenerator.get_link_of(resource)

        assert self_link is not None

        plugin_link = LinkGenerator.get_link_of(
            PageResource(RAMP), query_params={"template-tab": str(resource.id)}
        )

        assert plugin_link is not None

        return TemplateTabData(
            self=self_link,
            name=resource.name,
            description=resource.description,
            location=resource.location,
            sort_key=resource.sort_key,
            plugin_filter=resource.plugin_filter,
            plugins=plugin_link,
        )


class TemplateTabDataApiResponseGenerator(
    ApiResponseGenerator, resource_type=TemplateTab
):
    def generate_api_response(
        self,
        resource: TemplateTab,
        *,
        link_to_relations: Optional[Iterable[str]],
        **kwargs,
    ) -> Optional[ApiResponse]:
        meta = TYPE_TO_METADATA[TemplateTab]
        link_to_relations = (
            meta.extra_link_rels if link_to_relations is None else link_to_relations
        )

        return ApiResponseGenerator.default_generate_api_response(
            resource, link_to_relations=link_to_relations, **kwargs
        )
