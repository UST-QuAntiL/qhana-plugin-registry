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

"""Module containing the root endpoint of the v1 API."""

from http import HTTPStatus

from flask.views import MethodView
from flask_smorest import abort

from . import PLUGINS_API
from ..models.base_models import get_api_response_schema
from ..models.plugins import PluginSchema
from ..models.request_helpers import ApiResponseGenerator
from ...db.models.plugins import RAMP


@PLUGINS_API.route("/<string:plugin_id>/")
class PluginView(MethodView):
    """Detail endpoint of the plugin api."""

    @PLUGINS_API.response(HTTPStatus.OK, get_api_response_schema(PluginSchema))
    def get(self, plugin_id: str):
        """Get a single plugin resource."""
        if not plugin_id or not plugin_id.isdecimal():
            abort(HTTPStatus.BAD_REQUEST, message="The pluginId is in the wrong format!")
        found_plugin = RAMP.get_by_id(int(plugin_id))
        if not found_plugin:
            abort(HTTPStatus.NOT_FOUND, "Plugin not found.")

        return ApiResponseGenerator.get_api_response(found_plugin)
