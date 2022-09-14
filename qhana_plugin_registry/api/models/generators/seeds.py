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

"""Generators for all Seed resources."""

from typing import Dict, Iterable, Optional

from flask import url_for

from .constants import (
    API_SPEC_RESOURCE,
    COLLECTION_REL,
    CREATE_REL,
    DELETE_REL,
    ITEM_COUNT_DEFAULT,
    ITEM_COUNT_QUERY_KEY,
    NAV_REL,
    PAGE_REL,
    PAGE_SCHEMA,
    POST_REL,
    ROOT_RESOURCE_DUMMY,
    SEED_ID_KEY,
    UP_REL,
)
from .type_map import TYPE_TO_METADATA
from ..base_models import ApiLink, ApiResponse
from ..request_helpers import (
    ApiObjectGenerator,
    ApiResponseGenerator,
    KeyGenerator,
    LinkGenerator,
    PageResource,
)
from ..seeds import SeedData
from ....db.models.seeds import Seed

# Seed Page ###############################################################


class SeedPageKeyGenerator(KeyGenerator, resource_type=Seed, page=True):
    def update_key(self, key: Dict[str, str], resource: PageResource) -> Dict[str, str]:
        parent_resource = resource.resource or ROOT_RESOURCE_DUMMY
        parent_key = KeyGenerator.generate_key(parent_resource)
        key.update(parent_key)
        return key


class SeedPageLinkGenerator(LinkGenerator, resource_type=Seed, page=True):
    def generate_link(
        self, resource: PageResource, *, query_params: Optional[Dict[str, str]]
    ) -> Optional[ApiLink]:
        if query_params is None:
            query_params = {ITEM_COUNT_QUERY_KEY: ITEM_COUNT_DEFAULT}

        meta = TYPE_TO_METADATA[Seed]

        endpoint = meta.collection_endpoint
        assert endpoint is not None

        return ApiLink(
            href=url_for(endpoint, **query_params, _external=True),
            rel=(COLLECTION_REL, PAGE_REL),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource, query_params=query_params),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True)}#/components/schemas/{PAGE_SCHEMA}",
        )


class SeedPageUpLinkGenerator(
    LinkGenerator, resource_type=Seed, page=True, relation=UP_REL
):
    def generate_link(
        self, resource: PageResource, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        parent_resource = resource.resource or ROOT_RESOURCE_DUMMY
        link = LinkGenerator.get_link_of(parent_resource, query_params=query_params)
        assert link is not None
        link.rel = (UP_REL,)
        return link


class SeedPageCreateSeedLinkGenerator(
    LinkGenerator, resource_type=Seed, page=True, relation=CREATE_REL
):
    def generate_link(
        self, resource: PageResource, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        link = LinkGenerator.get_link_of(resource)
        assert link is not None
        link.rel = (CREATE_REL, POST_REL)
        return link


# Seed #########################################################################


class SeedKeyGenerator(KeyGenerator, resource_type=Seed):
    def update_key(self, key: Dict[str, str], resource: Seed) -> Dict[str, str]:
        assert isinstance(resource, Seed)
        parent_key = KeyGenerator.generate_key(PageResource(Seed, page_number=1))
        key.update(parent_key)
        key[SEED_ID_KEY] = str(resource.id)
        return key


class SeedSelfLinkGenerator(LinkGenerator, resource_type=Seed):
    def generate_link(
        self, resource: Seed, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        meta = TYPE_TO_METADATA[Seed]

        return ApiLink(
            href=url_for(meta.endpoint, seed_id=str(resource.id), _external=True),
            rel=tuple(),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True)}#/components/schemas/{meta.schema_id}",
        )


class SeedUpLinkGenerator(LinkGenerator, resource_type=Seed, relation=UP_REL):
    def generate_link(
        self, resource: Seed, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            PageResource(Seed, page_number=1),
            extra_relations=(UP_REL,),
        )


class DeleteSeedLinkGenerator(LinkGenerator, resource_type=Seed, relation=DELETE_REL):
    def generate_link(
        self, resource: Seed, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        link = LinkGenerator.get_link_of(resource)
        if link is None:
            return None
        link.rel = (DELETE_REL,)
        return link


class SeedApiObjectGenerator(ApiObjectGenerator, resource_type=Seed):
    def generate_api_object(
        self, resource: Seed, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[SeedData]:
        assert isinstance(resource, Seed)

        self_link = LinkGenerator.get_link_of(resource)

        assert self_link is not None

        return SeedData(self=self_link, url=resource.url)


class SeedDataApiResponseGenerator(ApiResponseGenerator, resource_type=Seed):
    def generate_api_response(
        self, resource: Seed, *, link_to_relations: Optional[Iterable[str]], **kwargs
    ) -> Optional[ApiResponse]:
        meta = TYPE_TO_METADATA[Seed]
        link_to_relations = (
            meta.extra_link_rels if link_to_relations is None else link_to_relations
        )
        return ApiResponseGenerator.default_generate_api_response(
            resource, link_to_relations=link_to_relations, **kwargs
        )
