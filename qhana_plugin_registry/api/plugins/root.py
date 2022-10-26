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
from typing import List, Optional, Sequence, Union, cast

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.sql.expression import ColumnElement, ColumnOperators

from qhana_plugin_registry.api.models.plugins import PluginsPageArgumentsSchema

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
from ...db.models.plugins import RAMP, PluginTag
from ...db.filters import (
    filter_ramps_by_id,
    filter_ramps_by_identifier_and_version,
    filter_ramps_by_tags,
)

PLUGINS_API = Blueprint(
    name="api-plugins",
    import_name=__name__,
    description="The basic plugins API.",
    url_prefix="/api/plugins",
)


def get_tag_filter_sets(tags: Optional[str]):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    must_have = {t for t in tag_list if not t.startswith("!")}
    forbidden = {t.lstrip("!") for t in tag_list if t.startswith("!")}
    tags_to_load = [t.lstrip("!") for t in tag_list]
    found_tags = PluginTag.get_all(tags_to_load)
    must_have_tags = [t for t in found_tags if t.tag in must_have]
    forbidden_tags = [t for t in found_tags if t.tag in forbidden]
    return must_have_tags, forbidden_tags


@PLUGINS_API.route("/")
class PluginsRootView(MethodView):
    """Root endpoint of the plugins api."""

    @PLUGINS_API.arguments(PluginsPageArgumentsSchema, location="query", as_kwargs=True)
    @PLUGINS_API.response(HTTPStatus.OK, get_api_response_schema(CursorPageSchema))
    def get(
        self,
        plugin_id: Optional[str] = None,
        name: Optional[str] = None,
        version: Optional[str] = None,
        type_: Optional[str] = None,
        tags: Optional[str] = None,
        **kwargs,
    ):
        """Get a list of plugins."""

        parsed_plugin_ids: Union[int, Sequence[int], None] = None
        if plugin_id:
            if "," in plugin_id:
                try:
                    parsed_plugin_ids = [
                        int(p_id.strip()) for p_id in plugin_id.split(",")
                    ]
                except ValueError:
                    abort(
                        HTTPStatus.BAD_REQUEST,
                        message="The plugin-id must be a comma separated list of valid plugin ids!",
                    )
            else:
                if not plugin_id.isdecimal():
                    abort(
                        HTTPStatus.BAD_REQUEST,
                        message="The plugin-id parameter is in the wrong format!",
                    )
                parsed_plugin_ids = int(plugin_id)

        pagination_options: PaginationOptions = prepare_pagination_query_args(
            **kwargs, _sort_default="name,-version"
        )

        filter_: List[ColumnOperators] = filter_ramps_by_id(parsed_plugin_ids)

        filter_ += filter_ramps_by_identifier_and_version(
            ramp_identifier=name, version=version
        )

        must_have, forbidden = get_tag_filter_sets(tags)

        filter_ += filter_ramps_by_tags(must_have, forbidden)

        if type_:
            filter_.append(cast(ColumnElement, RAMP.plugin_type) == type_)

        pagination_info = default_get_page_info(
            RAMP,
            filter_,
            pagination_options,
            sort_columns={
                "id": cast(ColumnElement, RAMP.id),
                "name": cast(ColumnElement, RAMP.plugin_id),
                "version": cast(ColumnElement, RAMP.sort_version),
            },
        )

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

        extra_query_params = {}
        if plugin_id is not None:
            extra_query_params["plugin-id"] = plugin_id
        if name is not None:
            extra_query_params["name"] = name
        if version is not None:
            extra_query_params["version"] = version
        if type_ is not None:
            extra_query_params["type"] = type_
        if tags is not None:
            extra_query_params["tags"] = tags

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
