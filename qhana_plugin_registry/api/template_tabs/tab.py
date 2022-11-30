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

"""Module containing the resource endpoint of the service API."""

from http import HTTPStatus
from typing import Dict, Optional, cast, Sequence

from flask.views import MethodView
from flask_smorest import abort

from .root import TEMPLATE_TABS_API
from ..models.base_models import (
    DeletedApiObjectRaw,
    DeletedApiObjectSchema,
    ChangedApiObjectRaw,
    ChangedApiObjectSchema,
    get_api_response_schema,
)
from ..models.request_helpers import ApiResponseGenerator
from ..models.templates import TemplateTabSchema
from ...db.db import DB
from ...db.models.templates import TemplateTab


@TEMPLATE_TABS_API.route("/<string:tab_id>/")
class TemplateTabView(MethodView):
    """Detail endpoint of the template tab api."""

    @TEMPLATE_TABS_API.response(HTTPStatus.OK, get_api_response_schema(TemplateTabSchema))
    def get(self, template_id: str, tab_id: str):
        """Get a single template tab resource."""
        if not template_id or not template_id.isdecimal():
            abort(
                HTTPStatus.BAD_REQUEST, message="The template id is in the wrong format!"
            )
        if not tab_id or not tab_id.isdecimal():
            abort(HTTPStatus.BAD_REQUEST, message="The tab id is in the wrong format!")
        found_tab = TemplateTab.get_by_id(int(tab_id))
        if not found_tab:
            abort(HTTPStatus.NOT_FOUND, message="Template tab not found.")

        return ApiResponseGenerator.get_api_response(found_tab)

    # FIXME add put and delete!

    # FIXME keep plugin lists for tabs up to date on changes
