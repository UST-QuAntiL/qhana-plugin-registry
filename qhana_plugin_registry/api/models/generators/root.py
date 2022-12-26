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

from .constants import (
    API_REL,
    API_SPEC_RESOURCE,
    ENV_REL_TYPE,
    NAV_REL,
    PLUGIN_REL_TYPE,
    RECOMMENDATION_REL_TYPE,
    SEED_REL_TYPE,
    SERVICE_REL_TYPE,
    TEMPLATE_REL_TYPE,
)
from .type_map import TYPE_TO_METADATA
from ..base_models import ApiLink, ApiResponse
from ..recommendations import RecommendationDataRaw
from ..request_helpers import (
    ApiObjectGenerator,
    ApiResponseGenerator,
    CollectionResource,
    KeyGenerator,
    LinkGenerator,
    PageResource,
)
from ..root import RootData
from ..root_raw import RootDataRaw
from ....db.models.env import Env
from ....db.models.plugins import RAMP
from ....db.models.seeds import Seed
from ....db.models.services import Service
from ....db.models.templates import UiTemplate

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
    LinkGenerator, resource_type=RootDataRaw, relation=SEED_REL_TYPE
):
    def generate_link(
        self, resource: RootDataRaw, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            PageResource(Seed, resource=resource, page_number=1),
            extra_relations=(NAV_REL, API_REL),
        )


class RootDataEnvNavLinkGenerator(
    LinkGenerator, resource_type=RootDataRaw, relation=ENV_REL_TYPE
):
    def generate_link(
        self, resource: RootDataRaw, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            CollectionResource(Env, resource=resource),
            extra_relations=(NAV_REL, API_REL),
        )


class RootDataServicesNavLinkGenerator(
    LinkGenerator, resource_type=RootDataRaw, relation=SERVICE_REL_TYPE
):
    def generate_link(
        self, resource: RootDataRaw, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            PageResource(Service, resource=resource, page_number=1),
            extra_relations=(NAV_REL, API_REL),
        )


class RootDataPluginsNavLinkGenerator(
    LinkGenerator, resource_type=RootDataRaw, relation=PLUGIN_REL_TYPE
):
    def generate_link(
        self, resource: RootDataRaw, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            PageResource(RAMP, resource=resource, page_number=1),
            extra_relations=(NAV_REL, API_REL),
        )


class RootDataRecommendationsNavLinkGenerator(
    LinkGenerator, resource_type=RootDataRaw, relation=RECOMMENDATION_REL_TYPE
):
    def generate_link(
        self, resource: RootDataRaw, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            RecommendationDataRaw([], []),
            extra_relations=(NAV_REL, API_REL),
        )


class RootDataTemplatesNavLinkGenerator(
    LinkGenerator, resource_type=RootDataRaw, relation=TEMPLATE_REL_TYPE
):
    def generate_link(
        self, resource: RootDataRaw, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            PageResource(UiTemplate, resource=resource, page_number=1),
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
