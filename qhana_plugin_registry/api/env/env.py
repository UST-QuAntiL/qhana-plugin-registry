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

"""Module containing the resource endpoint of the env API."""

from http import HTTPStatus

from flask.views import MethodView
from flask_smorest import abort

from .root import ENV_API
from ..models.base_models import (
    DeletedApiObjectRaw,
    DeletedApiObjectSchema,
    get_api_response_schema,
)
from ..models.request_helpers import ApiResponseGenerator, CollectionResource
from ..models.env import EnvSchema
from ...db.db import DB
from ...db.models.env import Env


@ENV_API.route("/<string:env>/")
class EnvView(MethodView):
    """Detail endpoint of the env api."""

    @ENV_API.response(HTTPStatus.OK, get_api_response_schema(EnvSchema))
    def get(self, env: str):
        """Get a single env resource."""
        if not env:
            abort(HTTPStatus.BAD_REQUEST, message="The env name must not be empty!")
        found_env = Env.get(env)
        if not found_env:
            abort(HTTPStatus.NOT_FOUND, message="Env not found.")

        return ApiResponseGenerator.get_api_response(found_env)

    @ENV_API.response(HTTPStatus.OK, get_api_response_schema(DeletedApiObjectSchema))
    def delete(self, env: str):
        if not env:
            abort(HTTPStatus.BAD_REQUEST, message="The env name must not be empty!")
        Env.remove(env)
        DB.session.commit()

        deleted_env = Env(env, "")

        return ApiResponseGenerator.get_api_response(
            DeletedApiObjectRaw(deleted=deleted_env, redirect_to=CollectionResource(Env))
        )
