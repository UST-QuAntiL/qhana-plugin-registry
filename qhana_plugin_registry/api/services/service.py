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

from flask.views import MethodView
from flask_smorest import abort

from .root import SERVICES_API
from ..models.base_models import (
    DeletedApiObjectRaw,
    DeletedApiObjectSchema,
    get_api_response_schema,
)
from ..models.request_helpers import ApiResponseGenerator, PageResource
from ..models.service import ServiceSchema
from ...db.db import DB
from ...db.models.services import Service


@SERVICES_API.route("/<string:service_id>/")
class ServiceView(MethodView):
    """Detail endpoint of the services api."""

    @SERVICES_API.response(HTTPStatus.OK, get_api_response_schema(ServiceSchema))
    def get(self, service_id: str):
        """Get a single seed resource."""
        if not service_id:
            abort(HTTPStatus.BAD_REQUEST, message="The service id must not be empty!")
        found_service = Service.get_by_service_id(service_id)
        if not found_service:
            abort(HTTPStatus.NOT_FOUND, message="Service not found.")

        return ApiResponseGenerator.get_api_response(found_service)

    # TODO: add put resource for updates!

    @SERVICES_API.response(HTTPStatus.OK, get_api_response_schema(DeletedApiObjectSchema))
    def delete(self, service_id: str):
        if not service_id:
            abort(HTTPStatus.BAD_REQUEST, message="The service id must not be empty!")
        found_service = Service.get_by_service_id(service_id)
        if found_service:
            DB.session.delete(found_service)
            DB.session.commit()
        else:
            # Deleted dummy resource
            found_service = Service(
                service_id=service_id,
                url="http://deleted.example.org",
                name=service_id,
                description="DELETED",
            )

        return ApiResponseGenerator.get_api_response(
            DeletedApiObjectRaw(
                deleted=found_service, redirect_to=PageResource(Service, page_number=1)
            )
        )
