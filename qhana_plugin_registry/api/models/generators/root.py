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

"""Generators for all api root related resources."""

from typing import Dict, Iterable, Optional

from flask import url_for

from .constants import API_REL, API_SPEC_RESOURCE, NAV_REL
from .type_map import TYPE_TO_METADATA
from ..base_models import ApiLink, ApiResponse
from ..request_helpers import (
    ApiObjectGenerator,
    ApiResponseGenerator,
    KeyGenerator,
    LinkGenerator,
    PageResource,
    CollectionResource,
)
from ..root import RootData
from ..root_raw import RootDataRaw
from ....db.models.env import Env
from ....db.models.seeds import Seed
from ....db.models.services import Service

# Root #########################################################################


class RootKeyGenerator(KeyGenerator, resource_type=RootDataRaw):
    def update_key(self, key: Dict[str, str], resource: RootDataRaw) -> Dict[str, str]:
        return {}


class RootDataLinkGenerator(LinkGenerator, resource_type=RootDataRaw):
    def generate_link(
        self, resource: RootDataRaw, *, query_params: Optional[Dict[str, str]]
    ) -> Optional[ApiLink]:
        meta = TYPE_TO_METADATA[RootDataRaw]

        return ApiLink(
            href=url_for(meta.endpoint, _external=True),
            rel=tuple(),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource, query_params=query_params),
            schema=url_for(API_SPEC_RESOURCE, _external=True)
            + f"#/components/schemas/{meta.schema_id}",
        )


class RootDataSeedsNavLinkGenerator(
    LinkGenerator, resource_type=RootDataRaw, relation=TYPE_TO_METADATA[Seed].rel_type
):
    def generate_link(
        self, resource: RootDataRaw, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            PageResource(Seed, resource=resource, page_number=1),
            extra_relations=(NAV_REL, API_REL),
        )


class RootDataEnvNavLinkGenerator(
    LinkGenerator, resource_type=RootDataRaw, relation=TYPE_TO_METADATA[Env].rel_type
):
    def generate_link(
        self, resource: RootDataRaw, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            CollectionResource(Env, resource=resource),
            extra_relations=(NAV_REL, API_REL),
        )


class RootDataServicesNavLinkGenerator(
    LinkGenerator, resource_type=RootDataRaw, relation=TYPE_TO_METADATA[Service].rel_type
):
    def generate_link(
        self, resource: RootDataRaw, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            PageResource(Service, resource=resource, page_number=1),
            extra_relations=(NAV_REL, API_REL),
        )


class RootDataApiObjectGenerator(ApiObjectGenerator, resource_type=RootDataRaw):
    def generate_api_object(
        self, resource: RootDataRaw, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[RootData]:
        assert isinstance(resource, RootDataRaw)

        self_link = LinkGenerator.get_link_of(resource)

        assert self_link is not None

        return RootData(self=self_link, title=resource.title)


class RootDataApiResponseGenerator(ApiResponseGenerator, resource_type=RootDataRaw):
    def generate_api_response(
        self, resource, *, link_to_relations: Optional[Iterable[str]], **kwargs
    ) -> Optional[ApiResponse]:
        meta = TYPE_TO_METADATA[RootDataRaw]
        link_to_relations = (
            meta.extra_link_rels if link_to_relations is None else link_to_relations
        )
        return ApiResponseGenerator.default_generate_api_response(
            resource, link_to_relations=link_to_relations, **kwargs
        )
