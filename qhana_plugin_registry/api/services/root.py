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

"""Module containing the root endpoint of the services API."""

from http import HTTPStatus
from typing import List, Optional, cast

from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.sql.expression import ColumnElement

from ..models.base_models import (
    CursorPageArgumentsSchema,
    CursorPageSchema,
    NewApiObjectRaw,
    NewApiObjectSchema,
    get_api_response_schema,
)
from ..models.pagination_util import (
    PaginationOptions,
    default_get_page_info,
    generate_page_links,
    prepare_pagination_query_args,
)
from ..models.request_helpers import (
    ApiResponseGenerator,
    EmbeddedResource,
    LinkGenerator,
    PageResource,
)
from ..models.service import ServiceSchema, ServicesPageArgumentsSchema
from ...db.db import DB
from ...db.filters import filter_services_by_service_id
from ...db.models.services import Service

SERVICES_API = Blueprint(
    name="api-services",
    import_name=__name__,
    description="The basic services url API.",
    url_prefix="/services",
)


@SERVICES_API.route("/")
class ServicesRootView(MethodView):
    """Root endpoint of the service api."""

    @SERVICES_API.arguments(ServicesPageArgumentsSchema, location="query", as_kwargs=True)
    @SERVICES_API.response(HTTPStatus.OK, get_api_response_schema(CursorPageSchema))
    def get(self, service_id: Optional[str] = None, **kwargs):
        """Get a list of services."""

        pagination_options: PaginationOptions = prepare_pagination_query_args(
            **kwargs, _sort_default="service_id"
        )

        service_id_filter = service_id
        if service_id and "," in service_id:
            service_id_filter = [i.strip() for i in service_id.split(",") if i.strip()]

        pagination_info = default_get_page_info(
            Service,
            filter_services_by_service_id(
                service_id_filter if service_id_filter else None
            ),
            pagination_options,
            {"service_id": cast(ColumnElement, Service.service_id)},
        )

        services: List[Service] = DB.session.execute(
            pagination_info.page_items_query
        ).scalars()

        embedded_responses = (
            ApiResponseGenerator.get_api_response(EmbeddedResource(item))
            for item in services
        )
        embedded_items = [response for response in embedded_responses if response]
        items = [
            link for r in embedded_items if (link := LinkGenerator.get_link_of(r.data))
        ]

        last_page = pagination_info.last_page

        page_resource = PageResource(
            Service,
            page_number=pagination_info.cursor_page,
            active_page=pagination_info.cursor_page,
            last_page=last_page.page if last_page else None,
            collection_size=pagination_info.collection_size,
            item_links=items,
        )

        extra_query_params = {}

        if service_id_filter:
            if isinstance(service_id_filter, str):
                extra_query_params["service-id"] = service_id_filter
            else:
                extra_query_params["service-id"] = ",".join(service_id_filter)

        self_link = LinkGenerator.get_link_of(
            page_resource,
            query_params=pagination_options.to_query_params(
                extra_params=extra_query_params
            ),
        )
        assert self_link is not None

        extra_links = generate_page_links(
            page_resource,
            pagination_info,
            pagination_options,
            extra_query_params=extra_query_params,
        )

        first_page_link = LinkGenerator.get_link_of(
            page_resource.get_page(1),
            query_params=pagination_options.to_query_params(
                cursor=None, extra_params=extra_query_params
            ),
        )
        assert first_page_link is not None

        return ApiResponseGenerator.get_api_response(
            page_resource,
            query_params=pagination_options.to_query_params(
                extra_params=extra_query_params
            ),
            extra_links=[
                first_page_link,
                self_link,
                *extra_links,
            ],
            extra_embedded=embedded_items,
        )

    @SERVICES_API.arguments(
        ServiceSchema(only=("service_id", "name", "description", "url"))
    )
    @SERVICES_API.response(HTTPStatus.OK, get_api_response_schema(NewApiObjectSchema))
    def post(self, service_data):
        service_id = service_data.get("service_id")
        existing: bool = Service.exists([Service.service_id == service_id])
        if existing:
            abort(
                HTTPStatus.CONFLICT, message=f"Service id '{service_id}' is already used!"
            )

        created_service = Service(
            service_id=service_id,
            url=service_data["url"],
            name=service_data["name"],
            description=service_data["description"],  # TODO: test
        )
        DB.session.add(created_service)
        DB.session.commit()

        return ApiResponseGenerator.get_api_response(
            NewApiObjectRaw(self=PageResource(Service), new=created_service)
        )
