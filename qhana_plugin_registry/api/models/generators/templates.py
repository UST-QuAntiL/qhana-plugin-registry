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

"""Generators for all Template resources."""

from typing import Dict, Iterable, Optional, Set

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
    PAGE_REL,
    POST_REL,
    PUT_REL,
    ROOT_RESOURCE_DUMMY,
    TEMPLATE_ID_KEY,
    UP_REL,
)
from .type_map import TYPE_TO_METADATA
from ..base_models import ApiLink, ApiResponse, CursorPageSchema
from ..request_helpers import (
    ApiObjectGenerator,
    ApiResponseGenerator,
    KeyGenerator,
    LinkGenerator,
    PageResource,
)
from ..templates import TemplateData
from ..templates_raw import TemplateGroupRaw
from ....db.models.templates import UiTemplate

# Template Page ################################################################


class TemplatePageKeyGenerator(KeyGenerator, resource_type=UiTemplate, page=True):
    def update_key(self, key: Dict[str, str], resource: PageResource) -> Dict[str, str]:
        parent_resource = resource.resource or ROOT_RESOURCE_DUMMY
        parent_key = KeyGenerator.generate_key(parent_resource)
        key.update(parent_key)
        return key


class TemplatePageLinkGenerator(LinkGenerator, resource_type=UiTemplate, page=True):
    def generate_link(
        self, resource: PageResource, *, query_params: Optional[Dict[str, str]]
    ) -> Optional[ApiLink]:
        if query_params is None:
            query_params = {ITEM_COUNT_QUERY_KEY: ITEM_COUNT_DEFAULT}

        meta = TYPE_TO_METADATA[UiTemplate]

        endpoint = meta.collection_endpoint
        assert endpoint is not None

        return ApiLink(
            href=url_for(endpoint, **query_params, _external=True),
            rel=(COLLECTION_REL, PAGE_REL),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource, query_params=query_params),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True)}#/components/schemas/{CursorPageSchema.schema_name()}",
        )


class TemplatePageUpLinkGenerator(
    LinkGenerator, resource_type=UiTemplate, page=True, relation=UP_REL
):
    def generate_link(
        self, resource: PageResource, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        parent_resource = resource.resource or ROOT_RESOURCE_DUMMY
        link = LinkGenerator.get_link_of(parent_resource, query_params=query_params)
        assert link is not None
        link.rel = (UP_REL,)
        return link


class TemplatePageCreateTemplateLinkGenerator(
    LinkGenerator, resource_type=UiTemplate, page=True, relation=CREATE_REL
):
    def generate_link(
        self, resource: PageResource, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        link = LinkGenerator.get_link_of(resource)
        assert link is not None
        link.rel = (CREATE_REL, POST_REL)
        return link


# Template #####################################################################


class TemplateKeyGenerator(KeyGenerator, resource_type=UiTemplate):
    def update_key(self, key: Dict[str, str], resource: UiTemplate) -> Dict[str, str]:
        assert isinstance(resource, UiTemplate)
        parent_key = KeyGenerator.generate_key(PageResource(UiTemplate, page_number=1))
        key.update(parent_key)
        key[TEMPLATE_ID_KEY] = str(resource.id)
        return key


class TemplateSelfLinkGenerator(LinkGenerator, resource_type=UiTemplate):
    def generate_link(
        self,
        resource: UiTemplate,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        meta = TYPE_TO_METADATA[UiTemplate]

        return ApiLink(
            href=url_for(meta.endpoint, template_id=str(resource.id), _external=True),
            rel=tuple(),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True)}#/components/schemas/{meta.schema_id}",
            name=resource.name,
        )


class TemplateUpLinkGenerator(LinkGenerator, resource_type=UiTemplate, relation=UP_REL):
    def generate_link(
        self,
        resource: UiTemplate,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            PageResource(UiTemplate, page_number=1),
            extra_relations=(UP_REL,),
        )


class UpdateTemplateLinkGenerator(
    LinkGenerator, resource_type=UiTemplate, relation=UPDATE_REL
):  # TODO check action relation
    def generate_link(
        self,
        resource: UiTemplate,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        link = LinkGenerator.get_link_of(resource)
        if link is None:
            return None
        link.rel = (UPDATE_REL, PUT_REL)  # TODO check rels
        return link


class DeleteTemplateLinkGenerator(
    LinkGenerator, resource_type=UiTemplate, relation=DELETE_REL
):
    def generate_link(
        self,
        resource: UiTemplate,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        link = LinkGenerator.get_link_of(resource)
        if link is None:
            return None
        link.rel = (DELETE_REL,)
        return link


class TemplateApiObjectGenerator(ApiObjectGenerator, resource_type=UiTemplate):
    def generate_api_object(
        self,
        resource: UiTemplate,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[TemplateData]:
        assert isinstance(resource, UiTemplate)

        self_link = LinkGenerator.get_link_of(resource)

        assert self_link is not None

        group_locations: Set[str] = {t.location for t in resource.tabs}
        groups = (
            TemplateGroupRaw(
                template=resource,
                location=loc,
                items=[],
            )
            for loc in group_locations
        )
        group_links = [l for g in groups if (l := LinkGenerator.get_link_of(g))]

        return TemplateData(
            self=self_link,
            name=resource.name,
            description=resource.description,
            tags=[t.tag for t in resource.tags],
            groups=group_links,
        )


class TemplateDataApiResponseGenerator(ApiResponseGenerator, resource_type=UiTemplate):
    def generate_api_response(
        self,
        resource: UiTemplate,
        *,
        link_to_relations: Optional[Iterable[str]],
        **kwargs,
    ) -> Optional[ApiResponse]:
        meta = TYPE_TO_METADATA[UiTemplate]
        link_to_relations = (
            meta.extra_link_rels if link_to_relations is None else link_to_relations
        )

        return ApiResponseGenerator.default_generate_api_response(
            resource, link_to_relations=link_to_relations, **kwargs
        )
