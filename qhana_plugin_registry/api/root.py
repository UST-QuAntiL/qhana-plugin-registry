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

"""Module containing the root api endpoint."""

from http import HTTPStatus

from flask.views import MethodView

from qhana_plugin_registry.api.models.base_models import (
    ApiResponse,
    get_api_response_schema,
)

from .blueprint import API, ROOT_ENDPOINT
from .models.request_helpers import ApiResponseGenerator
from .models.root import RootSchema
from .models.root_raw import RootDataRaw


@ROOT_ENDPOINT.route("/")
class RootView(MethodView):
    @ROOT_ENDPOINT.response(HTTPStatus.OK, get_api_response_schema(RootSchema))
    def get(self) -> ApiResponse:
        """Get the Root API information containing the links to all versions of this api."""
        assert API.spec is not None

        response = ApiResponseGenerator.get_api_response(
            RootDataRaw(title=API.spec.title)
        )

        assert response is not None

        return response
