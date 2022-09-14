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

"""Module containing the root endpoint of the plugins API."""

from http import HTTPStatus
from typing import List

from flask.views import MethodView
from flask_smorest import Blueprint

from ..models.base_models import (
    CursorPageArgumentsSchema,
    CursorPageSchema,
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
from ...db.db import DB
from ...db.models.plugins import RAMP

PLUGINS_API = Blueprint(
    name="api-plugins",
    import_name=__name__,
    description="The basic plugins API.",
    url_prefix="/api/plugins",
)


@PLUGINS_API.route("/")
class PluginsRootView(MethodView):
    """Root endpoint of the plugins api."""

    @PLUGINS_API.arguments(CursorPageArgumentsSchema, location="query", as_kwargs=True)
    @PLUGINS_API.response(HTTPStatus.OK, get_api_response_schema(CursorPageSchema))
    def get(self, **kwargs):
        """Get a list of plugins."""
        pagination_options: PaginationOptions = prepare_pagination_query_args(
            **kwargs, _sort_default="name"
        )

        pagination_info = default_get_page_info(RAMP, tuple(), pagination_options)

        plugins: List[RAMP] = DB.session.execute(
            pagination_info.page_items_query
        ).scalars()

        embedded_responses = (
            ApiResponseGenerator.get_api_response(EmbeddedResource(item))
            for item in plugins
        )
        embedded_items = [response for response in embedded_responses if response]
        items = [
            link for r in embedded_items if (link := LinkGenerator.get_link_of(r.data))
        ]

        last_page = pagination_info.last_page

        page_resource = PageResource(
            RAMP,
            page_number=pagination_info.cursor_page,
            active_page=pagination_info.cursor_page,
            last_page=last_page.page if last_page else None,
            collection_size=pagination_info.collection_size,
            item_links=items,
        )
        self_link = LinkGenerator.get_link_of(
            page_resource, query_params=pagination_options.to_query_params()
        )
        assert self_link is not None

        extra_links = generate_page_links(
            page_resource, pagination_info, pagination_options
        )

        first_page_link = LinkGenerator.get_link_of(
            page_resource.get_page(1),
            query_params=pagination_options.to_query_params(cursor=None),
        )
        assert first_page_link is not None

        return ApiResponseGenerator.get_api_response(
            page_resource,
            query_params=pagination_options.to_query_params(),
            extra_links=[
                first_page_link,
                self_link,
                *extra_links,
            ],
            extra_embedded=embedded_items,
        )
