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

from .root import TEMPLATES_API
from ..models.base_models import (
    DeletedApiObjectRaw,
    DeletedApiObjectSchema,
    ChangedApiObjectRaw,
    ChangedApiObjectSchema,
    get_api_response_schema,
)
from ..models.request_helpers import ApiResponseGenerator, PageResource
from ..models.templates import TemplateSchema
from ...db.db import DB
from ...db.models.templates import WorkspaceTemplate, TemplateTag


@TEMPLATES_API.route("/<string:template_id>/")
class TemplateView(MethodView):
    """Detail endpoint of the template api."""

    @TEMPLATES_API.response(HTTPStatus.OK, get_api_response_schema(TemplateSchema))
    def get(self, template_id: str):
        """Get a single template resource."""
        if not template_id or not template_id.isdecimal():
            abort(
                HTTPStatus.BAD_REQUEST, message="The template id is in the wrong format!"
            )
        found_service = WorkspaceTemplate.get_by_id(int(template_id))
        if not found_service:
            abort(HTTPStatus.NOT_FOUND, message="Template not found.")

        return ApiResponseGenerator.get_api_response(found_service)

    @TEMPLATES_API.arguments(TemplateSchema(exclude=("self", "groups")))
    @TEMPLATES_API.response(
        HTTPStatus.OK, get_api_response_schema(ChangedApiObjectSchema)
    )
    def put(self, template_data: Dict[str, str], template_id: str):
        """Update a template resource."""
        if not template_id or not template_id.isdecimal():
            abort(
                HTTPStatus.BAD_REQUEST, message="The template id is in the wrong format!"
            )

        found_template = cast(
            Optional[WorkspaceTemplate], WorkspaceTemplate.get_by_id(int(template_id))
        )
        if not found_template:
            abort(HTTPStatus.NOT_FOUND, message="Template not found.")

        found_template.name = template_data["name"]
        found_template.description = template_data["description"]
        tags: Sequence[str] = template_data.get("tags", [])

        new_tags = TemplateTag.get_or_create_all(tags)

        found_template.tags = new_tags

        DB.session.add(found_template)
        DB.session.commit()

        return ApiResponseGenerator.get_api_response(
            ChangedApiObjectRaw(changed=found_template)
        )

    @TEMPLATES_API.response(
        HTTPStatus.OK, get_api_response_schema(DeletedApiObjectSchema)
    )
    def delete(self, template_id: str):
        if not template_id or not template_id.isdecimal():
            abort(
                HTTPStatus.BAD_REQUEST, message="The template id is in the wrong format!"
            )
        found_template = WorkspaceTemplate.get_by_id(int(template_id))
        if found_template:
            DB.session.delete(found_template)
            DB.session.commit()
        else:
            # Deleted dummy resource
            found_template = WorkspaceTemplate(
                name=template_id,
                description="DELETED",
            )

        return ApiResponseGenerator.get_api_response(
            DeletedApiObjectRaw(
                deleted=found_template,
                redirect_to=PageResource(WorkspaceTemplate, page_number=1),
            )
        )
