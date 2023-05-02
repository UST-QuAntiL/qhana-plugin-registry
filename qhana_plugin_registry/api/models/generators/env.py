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

"""Generators for all Env resources."""

from typing import Dict, Iterable, Optional

from flask import url_for, current_app

from .constants import (
    API_SPEC_RESOURCE,
    COLLECTION_REL,
    CREATE_REL,
    DELETE_REL,
    NAV_REL,
    POST_REL,
    PUT_REL,
    ROOT_RESOURCE_DUMMY,
    ENV_ID_KEY,
    UP_REL,
    UPDATE_REL,
)
from .type_map import TYPE_TO_METADATA
from ..base_models import ApiLink, ApiResponse, CursorPageSchema
from ..request_helpers import (
    ApiObjectGenerator,
    ApiResponseGenerator,
    KeyGenerator,
    LinkGenerator,
    CollectionResource,
)
from ..env import EnvData
from ....db.models.env import Env

# Env Collection ###############################################################


class EnvCollectionKeyGenerator(KeyGenerator, resource_type=Env, page=True):
    def update_key(
        self, key: Dict[str, str], resource: CollectionResource
    ) -> Dict[str, str]:
        parent_resource = resource.resource or ROOT_RESOURCE_DUMMY
        parent_key = KeyGenerator.generate_key(parent_resource)
        key.update(parent_key)
        return key


class EnvCollectionLinkGenerator(LinkGenerator, resource_type=Env, page=True):
    def generate_link(
        self, resource: CollectionResource, *, query_params: Optional[Dict[str, str]]
    ) -> Optional[ApiLink]:
        meta = TYPE_TO_METADATA[Env]

        endpoint = meta.collection_endpoint
        assert endpoint is not None

        if query_params is None:
            query_params = {}

        scheme = current_app.config.get("PREFERRED_URL_SCHEME", "http")

        return ApiLink(
            href=url_for(endpoint, **query_params, _external=True, _scheme=scheme),
            rel=(COLLECTION_REL,),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource, query_params=query_params),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True, _scheme=scheme)}#/components/schemas/{CursorPageSchema.schema_name()}",
        )


class EnvCollectionUpLinkGenerator(
    LinkGenerator, resource_type=Env, page=True, relation=UP_REL
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


class EnvCollectionCreateEnvLinkGenerator(
    LinkGenerator, resource_type=Env, page=True, relation=CREATE_REL
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


# Env ##########################################################################


class EnvKeyGenerator(KeyGenerator, resource_type=Env):
    def update_key(self, key: Dict[str, str], resource: Env) -> Dict[str, str]:
        assert isinstance(resource, Env)
        parent_key = KeyGenerator.generate_key(CollectionResource(Env))
        key.update(parent_key)
        key[ENV_ID_KEY] = str(resource.name)
        return key


class EnvSelfLinkGenerator(LinkGenerator, resource_type=Env):
    def generate_link(
        self, resource: Env, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        meta = TYPE_TO_METADATA[Env]

        scheme = current_app.config.get("PREFERRED_URL_SCHEME", "http")

        return ApiLink(
            href=url_for(
                meta.endpoint, env=str(resource.name), _external=True, _scheme=scheme
            ),
            rel=tuple(),
            resource_type=meta.rel_type,
            resource_key=KeyGenerator.generate_key(resource),
            schema=f"{url_for(API_SPEC_RESOURCE, _external=True, _scheme=scheme)}#/components/schemas/{meta.schema_id}",
            name=resource.name,
        )


class EnvUpLinkGenerator(LinkGenerator, resource_type=Env, relation=UP_REL):
    def generate_link(
        self, resource: Env, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        return LinkGenerator.get_link_of(
            CollectionResource(Env), extra_relations=(UP_REL,)
        )


class UpdateEnvLinkGenerator(LinkGenerator, resource_type=Env, relation=UPDATE_REL):
    def generate_link(
        self, resource: Env, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        link = LinkGenerator.get_link_of(resource)
        if link is None:
            return None
        link.rel = (UPDATE_REL, PUT_REL)
        return link


class DeleteEnvLinkGenerator(LinkGenerator, resource_type=Env, relation=DELETE_REL):
    def generate_link(
        self, resource: Env, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        link = LinkGenerator.get_link_of(resource)
        if link is None:
            return None
        link.rel = (DELETE_REL,)
        return link


class EnvApiObjectGenerator(ApiObjectGenerator, resource_type=Env):
    def generate_api_object(
        self, resource: Env, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[EnvData]:
        assert isinstance(resource, Env)

        self_link = LinkGenerator.get_link_of(resource)

        assert self_link is not None

        return EnvData(self=self_link, name=resource.name, value=resource.value)


class EnvDataApiResponseGenerator(ApiResponseGenerator, resource_type=Env):
    def generate_api_response(
        self, resource: Env, *, link_to_relations: Optional[Iterable[str]], **kwargs
    ) -> Optional[ApiResponse]:
        meta = TYPE_TO_METADATA[Env]
        link_to_relations = (
            meta.extra_link_rels if link_to_relations is None else link_to_relations
        )
        return ApiResponseGenerator.default_generate_api_response(
            resource, link_to_relations=link_to_relations, **kwargs
        )
