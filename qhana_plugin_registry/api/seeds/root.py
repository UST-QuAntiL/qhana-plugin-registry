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

"""Module containing the root endpoint of the seeds API."""

from http import HTTPStatus
from typing import List

from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort

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
from ..models.seeds import SeedSchema
from ...db.db import DB
from ...db.models.seeds import Seed

SEEDS_API = Blueprint(
    name="api-seeds",
    import_name=__name__,
    description="The basic seed url API.",
    url_prefix=current_app.config.get("URL_PREFIX", "/api") + "/seeds",
)


@SEEDS_API.route("/")
class SeedsRootView(MethodView):
    """Root endpoint of the seed api."""

    @SEEDS_API.arguments(CursorPageArgumentsSchema, location="query", as_kwargs=True)
    @SEEDS_API.response(HTTPStatus.OK, get_api_response_schema(CursorPageSchema))
    def get(self, **kwargs):
        """Get a list of seeds."""
        # abort(HTTPStatus.NOT_IMPLEMENTED, message="WIP, currently not implemented")

        pagination_options: PaginationOptions = prepare_pagination_query_args(
            **kwargs, _sort_default="id"
        )

        pagination_info = default_get_page_info(Seed, tuple(), pagination_options)

        seeds: List[Seed] = DB.session.execute(pagination_info.page_items_query).scalars()

        embedded_responses = (
            ApiResponseGenerator.get_api_response(EmbeddedResource(item))
            for item in seeds
        )
        embedded_items = [response for response in embedded_responses if response]
        items = [
            link for r in embedded_items if (link := LinkGenerator.get_link_of(r.data))
        ]

        last_page = pagination_info.last_page

        page_resource = PageResource(
            Seed,
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

    @SEEDS_API.arguments(SeedSchema(only=("url",)))
    @SEEDS_API.response(HTTPStatus.OK, get_api_response_schema(NewApiObjectSchema))
    def post(self, seed_data):
        seed_url = seed_data.get("url")
        existing: bool = Seed.exists([Seed.url == seed_url])
        if existing:
            abort(HTTPStatus.CONFLICT, message=f"URL {seed_url} is already used!")

        created_seed = Seed(url=seed_url)
        DB.session.add(created_seed)
        DB.session.commit()

        # FIXME kick of plugin discovery

        return ApiResponseGenerator.get_api_response(
            NewApiObjectRaw(self=PageResource(Seed), new=created_seed)
        )
