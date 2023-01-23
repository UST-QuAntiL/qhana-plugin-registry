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
from typing import Dict, Optional, cast, Sequence, TypedDict

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
from ..models.request_helpers import ApiResponseGenerator, PageResource
from ..models.templates import TemplateTabSchema
from ...db.db import DB
from ...db.models.templates import TemplateTab, UiTemplate
from ...tasks.plugin_filter import apply_filter_for_tab


class TemplateTabData(TypedDict):
    name: str
    description: str
    sort_key: int
    location: str
    plugin_filter: str


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

    @TEMPLATE_TABS_API.arguments(TemplateTabSchema(exclude=("self", "plugins")))
    @TEMPLATE_TABS_API.response(
        HTTPStatus.OK, get_api_response_schema(ChangedApiObjectSchema)
    )
    def put(self, template_tab_data: TemplateTabData, template_id: str, tab_id: str):
        """Create or change a single template tab resource."""
        if not template_id or not template_id.isdecimal():
            abort(
                HTTPStatus.BAD_REQUEST, message="The template id is in the wrong format!"
            )
        found_template = cast(
            Optional[UiTemplate], UiTemplate.get_by_id(int(template_id))
        )
        if not found_template:
            abort(HTTPStatus.NOT_FOUND, message="Template not found.")
        if not tab_id or not tab_id.isdecimal():
            abort(HTTPStatus.BAD_REQUEST, message="The tab id is in the wrong format!")
        found_tab = cast(Optional[TemplateTab], TemplateTab.get_by_id(int(tab_id)))
        if not found_tab:
            abort(HTTPStatus.NOT_FOUND, message="Template tab not found.")

        found_tab.template = found_template
        found_tab.name = template_tab_data["name"]
        found_tab.description = template_tab_data["description"]
        found_tab.sort_key = template_tab_data["sort_key"]
        found_tab.location = template_tab_data["location"]
        found_tab.plugin_filter = template_tab_data["plugin_filter"]

        DB.session.commit()
        apply_filter_for_tab.delay(found_tab.id)

        return ApiResponseGenerator.get_api_response(
            ChangedApiObjectRaw(changed=found_tab)
        )

    @TEMPLATE_TABS_API.response(
        HTTPStatus.OK, get_api_response_schema(DeletedApiObjectSchema)
    )
    def delete(self, template_id: str, tab_id: str):
        if not template_id or not template_id.isdecimal():
            abort(
                HTTPStatus.BAD_REQUEST, message="The template id is in the wrong format!"
            )
        found_template = cast(
            Optional[UiTemplate], UiTemplate.get_by_id(int(template_id))
        )
        if not found_template:
            abort(HTTPStatus.NOT_FOUND, message="Template not found.")
        if not tab_id or not tab_id.isdecimal():
            abort(HTTPStatus.BAD_REQUEST, message="The tab id is in the wrong format!")
        found_tab = TemplateTab.get_by_id(int(tab_id))
        if found_tab:
            DB.session.delete(found_tab)
            DB.session.commit()
        else:
            # Deleted dummy resource
            found_tab = TemplateTab(
                name=tab_id,
                description="DELETED",
                template=found_template,
            )

        return ApiResponseGenerator.get_api_response(
            DeletedApiObjectRaw(
                deleted=found_tab,
                redirect_to=PageResource(UiTemplate, page_number=1),
            )
        )
