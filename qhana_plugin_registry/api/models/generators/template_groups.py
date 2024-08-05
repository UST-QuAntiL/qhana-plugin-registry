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

"""Generators for all Template Group resources."""

from typing import Dict, Iterable, Optional

from flask import url_for

from .constants import (
    API_SPEC_RESOURCE,
    COLLECTION_REL,
    UP_REL,
    TEMPLATE_GROUP_QUERY_KEY,
)
from .type_map import TYPE_TO_METADATA
from ..base_models import ApiLink, ApiResponse
from ..templates import TemplateGroupSchema, TemplateGroupData
from ..templates_raw import TemplateGroupRaw
from ..request_helpers import (
    ApiObjectGenerator,
    ApiResponseGenerator,
    KeyGenerator,
    LinkGenerator,
)

# Template Group Collection ####################################################


class TemplateGroupKeyGenerator(KeyGenerator, resource_type=TemplateGroupRaw):
    def update_key(
        self, key: Dict[str, str], resource: TemplateGroupRaw
    ) -> Dict[str, str]:
        parent_resource = resource.template
        parent_key = KeyGenerator.generate_key(
            parent_resource, query_params={TEMPLATE_GROUP_QUERY_KEY: resource.location}
        )
        key.update(parent_key)
        return key


class TemplateGroupLinkGenerator(LinkGenerator, resource_type=TemplateGroupRaw):
    def generate_link(
        self,
        resource: TemplateGroupRaw,
        *,
        query_params: Optional[Dict[str, str]],
    ) -> Optional[ApiLink]:
        meta = TYPE_TO_METADATA[TemplateGroupRaw]

        endpoint = meta.collection_endpoint
        assert endpoint is not None

        if query_params is None:
            query_params = {TEMPLATE_GROUP_QUERY_KEY: resource.location}
        else:
            query_params[TEMPLATE_GROUP_QUERY_KEY] = resource.location

        if resource.name:
            name = resource.name
        else:
            name = f"Tab Group: {resource.location}"

        return ApiLink(
            href=url_for(
                endpoint,
                template_id=str(resource.template.id),
                **query_params,
                _external=True,
            ),
            rel=(COLLECTION_REL,),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource, query_params=query_params),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True)}#/components/schemas/{TemplateGroupSchema.schema_name()}",
            name=name,
        )


class TemplateGroupUpLinkGenerator(
    LinkGenerator, resource_type=TemplateGroupRaw, relation=UP_REL
):
    def generate_link(
        self,
        resource: TemplateGroupRaw,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        parent_resource = resource.template
        link = LinkGenerator.get_link_of(parent_resource, query_params=query_params)
        assert link is not None
        link.rel = (UP_REL,)
        return link


class TemplateGroupApiObjectGenerator(ApiObjectGenerator, resource_type=TemplateGroupRaw):
    def generate_api_object(
        self,
        resource: TemplateGroupRaw,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[TemplateGroupData]:
        assert isinstance(resource, TemplateGroupRaw)

        self_link = LinkGenerator.get_link_of(resource)

        assert self_link is not None

        items = [
            link for tab in resource.items if (link := LinkGenerator.get_link_of(tab))
        ]

        return TemplateGroupData(
            self=self_link,
            collection_size=len(items),
            items=items,
            location=resource.location,
        )


class TemplateGroupApiResponseGenerator(
    ApiResponseGenerator, resource_type=TemplateGroupRaw
):
    def generate_api_response(
        self, resource, *, link_to_relations: Optional[Iterable[str]], **kwargs
    ) -> Optional[ApiResponse]:
        meta = TYPE_TO_METADATA[TemplateGroupRaw]
        link_to_relations = (
            meta.extra_link_rels if link_to_relations is None else link_to_relations
        )
        return ApiResponseGenerator.default_generate_api_response(
            resource, link_to_relations=link_to_relations, **kwargs
        )
