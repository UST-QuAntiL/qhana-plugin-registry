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

"""Generators for all Recommendation resources."""

from typing import Dict, Iterable, Optional

from flask import url_for

from .constants import (
    API_SPEC_RESOURCE,
    COLLECTION_REL,
    NAV_REL,
    ROOT_RESOURCE_DUMMY,
    UP_REL,
)
from .type_map import TYPE_TO_METADATA
from ..base_models import ApiLink, ApiResponse
from ..recommendations import (
    RecommendationCollection,
    RecommendationCollectionSchema,
    RecommendationDataRaw,
)
from ..request_helpers import (
    ApiObjectGenerator,
    ApiResponseGenerator,
    KeyGenerator,
    LinkGenerator,
)

# Recommendation Collection ####################################################


class RecommendationCollectionKeyGenerator(
    KeyGenerator, resource_type=RecommendationDataRaw
):
    def update_key(
        self, key: Dict[str, str], resource: RecommendationDataRaw
    ) -> Dict[str, str]:
        parent_resource = ROOT_RESOURCE_DUMMY
        parent_key = KeyGenerator.generate_key(parent_resource)
        key.update(parent_key)
        return key


class RecommendationCollectionLinkGenerator(
    LinkGenerator, resource_type=RecommendationDataRaw
):
    def generate_link(
        self,
        resource: RecommendationDataRaw,
        *,
        query_params: Optional[Dict[str, str]],
    ) -> Optional[ApiLink]:
        meta = TYPE_TO_METADATA[RecommendationDataRaw]

        endpoint = meta.collection_endpoint
        assert endpoint is not None

        if query_params is None:
            query_params = {}

        return ApiLink(
            href=url_for(endpoint, **query_params, _external=True),
            rel=(COLLECTION_REL,),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource, query_params=query_params),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True)}#/components/schemas/{RecommendationCollectionSchema.schema_name()}",
        )


class RecommendationCollectionUpLinkGenerator(
    LinkGenerator, resource_type=RecommendationDataRaw, relation=UP_REL
):
    def generate_link(
        self,
        resource: RecommendationDataRaw,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[ApiLink]:
        parent_resource = ROOT_RESOURCE_DUMMY
        link = LinkGenerator.get_link_of(parent_resource, query_params=query_params)
        assert link is not None
        link.rel = (UP_REL,)
        return link


class RecommendationApiObjectGenerator(
    ApiObjectGenerator, resource_type=RecommendationDataRaw
):
    def generate_api_object(
        self,
        resource: RecommendationDataRaw,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[RecommendationCollection]:
        assert isinstance(resource, RecommendationDataRaw)

        self_link = LinkGenerator.get_link_of(resource)

        assert self_link is not None

        items = [
            link
            for plugin in resource.plugins
            if (link := LinkGenerator.get_link_of(plugin))
        ]

        return RecommendationCollection(
            self=self_link,
            collection_size=len(items),
            items=items,
            weights=resource.weights,
        )


class RecommendationApiResponseGenerator(
    ApiResponseGenerator, resource_type=RecommendationDataRaw
):
    def generate_api_response(
        self, resource, *, link_to_relations: Optional[Iterable[str]], **kwargs
    ) -> Optional[ApiResponse]:
        meta = TYPE_TO_METADATA[RecommendationDataRaw]
        link_to_relations = (
            meta.extra_link_rels if link_to_relations is None else link_to_relations
        )
        return ApiResponseGenerator.default_generate_api_response(
            resource, link_to_relations=link_to_relations, **kwargs
        )
