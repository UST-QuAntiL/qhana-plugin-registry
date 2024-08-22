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

"""Module containing the root endpoint of the env API."""

from http import HTTPStatus
from typing import Sequence, Optional

from flask.views import MethodView
from flask_smorest import Blueprint

from ..models.base_models import (
    CollectionResourceSchema,
    ChangedApiObjectRaw,
    ChangedApiObjectSchema,
    get_api_response_schema,
)
from ..models.request_helpers import (
    ApiResponseGenerator,
    EmbeddedResource,
    LinkGenerator,
    CollectionResource,
)
from ..models.env import EnvSchema, EnvPageArgumentsSchema
from ...db.db import DB
from ...db.models.env import Env

ENV_API = Blueprint(
    name="api-env",
    import_name=__name__,
    description="The basic env url API.",
    url_prefix="/api/env",
)


@ENV_API.route("/")
class EnvRootView(MethodView):
    """Root endpoint of the env api."""

    @ENV_API.arguments(EnvPageArgumentsSchema, location="query", as_kwargs=True)
    @ENV_API.response(HTTPStatus.OK, get_api_response_schema(CollectionResourceSchema))
    def get(self, name: Optional[str] = None, **kwargs):
        """Get a list of env variables."""

        env_vars: Sequence[Env]
        count: Optional[int] = None

        if not name:
            env_vars = Env.get_items()
        else:
            env_var = Env.get(name)
            env_vars = [env_var] if env_var else []
            count = Env.get_count()

        embedded_responses = (
            ApiResponseGenerator.get_api_response(EmbeddedResource(item))
            for item in env_vars
        )
        embedded_items = [response for response in embedded_responses if response]
        items = [
            link for r in embedded_items if (link := LinkGenerator.get_link_of(r.data))
        ]

        if count is None:
            count = len(items)

        collection_resource = CollectionResource(
            Env,
            collection_size=count,
            item_links=items,
        )

        return ApiResponseGenerator.get_api_response(
            collection_resource,
            query_params={"name": name} if name is not None else {},
            extra_embedded=embedded_items,
        )

    @ENV_API.arguments(EnvSchema(only=("name", "value")))
    @ENV_API.response(HTTPStatus.OK, get_api_response_schema(ChangedApiObjectSchema))
    def post(self, env_data):
        env_var = Env.set(name=env_data["name"], value=env_data["value"])
        DB.session.commit()

        return ApiResponseGenerator.get_api_response(
            ChangedApiObjectRaw(self=CollectionResource(Env), changed=env_var)
        )
