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
from typing import List, Optional, Sequence, Union, cast, Tuple, Set
from urllib.parse import urlparse

from flask import Response
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.sql.expression import ColumnElement, ColumnOperators
from sqlalchemy.sql import select
from sqlalchemy.orm import selectinload

from qhana_plugin_registry.api.models.plugins import (
    PluginsPageArgumentsSchema,
    PluginsPOSTArgumentsSchema,
)

from ..models.base_models import (
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
from ...db.models.seeds import Seed
from ...db.models.plugins import RAMP, PluginTag
from ...db.filters import (
    filter_impossible,
    filter_ramps_by_id,
    filter_ramps_by_url,
    filter_ramps_by_identifier_and_version,
    filter_ramps_by_last_available,
    filter_ramps_by_tags,
    filter_ramps_by_input_data,
    filter_ramps_by_template_tab,
)
from ...tasks.plugin_discovery import discover_plugins_from_seeds

PLUGINS_API = Blueprint(
    name="api-plugins",
    import_name=__name__,
    description="The basic plugins API.",
    url_prefix="/api/plugins",
)


def get_tag_filter_sets(
    tags: Optional[str],
) -> Tuple[Sequence[PluginTag], Sequence[PluginTag], Set[str]]:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    if not tag_list:
        return [], [], set()
    must_have = {t for t in tag_list if not t.startswith("!")}
    forbidden = {t.lstrip("!") for t in tag_list if t.startswith("!")}
    tags_to_load = [t.lstrip("!") for t in tag_list]
    found_tags = PluginTag.get_all(tags_to_load)
    must_have_tags = [t for t in found_tags if t.tag in must_have]
    unknown_must_have_tags = must_have - {t.tag for t in must_have_tags}
    forbidden_tags = [t for t in found_tags if t.tag in forbidden]
    return must_have_tags, forbidden_tags, unknown_must_have_tags


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
        url: Optional[str] = None,
        type_: Optional[str] = None,
        tags: Optional[str] = None,
        input_data_type: Optional[str] = None,
        input_content_type: Optional[str] = None,
        last_available_period: Optional[int] = None,
        template_tab: Optional[int] = None,
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

        if last_available_period is not None and last_available_period <= 0:
            last_available_period = None

        pagination_options: PaginationOptions = prepare_pagination_query_args(
            **kwargs, _sort_default="name,-version", _cast_cursor=int
        )

        filter_: List[ColumnOperators] = filter_ramps_by_id(parsed_plugin_ids)

        filter_ += filter_ramps_by_last_available(last_available_period)

        filter_ += filter_ramps_by_identifier_and_version(
            ramp_identifier=name, version=version
        )

        filter_ += filter_ramps_by_url(url)

        must_have, forbidden, unknown_must_have = get_tag_filter_sets(tags)

        filter_ += filter_ramps_by_tags(must_have, forbidden)

        filter_ += filter_ramps_by_input_data(input_data_type, input_content_type)

        filter_ += filter_ramps_by_template_tab(template_tab)

        if type_:
            filter_.append(cast(ColumnElement, RAMP.plugin_type) == type_)

        if unknown_must_have:
            # required tags are are unknown => no plugin can have these tags
            filter_ = filter_impossible()

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
            pagination_info.page_items_query.options(
                selectinload(RAMP.data_consumed), selectinload(RAMP.data_produced)
            )
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
        if url is not None:
            extra_query_params["url"] = url
        if type_ is not None:
            extra_query_params["type"] = type_
        if tags is not None:
            extra_query_params["tags"] = tags
        if input_data_type is not None:
            extra_query_params["input-data-type"] = input_data_type
        if input_content_type is not None:
            extra_query_params["input-content-type"] = input_content_type
        if last_available_period is not None:
            extra_query_params["last-available-period"] = str(last_available_period)
        if template_tab is not None:
            extra_query_params["template-tab"] = str(template_tab)

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

    @PLUGINS_API.arguments(PluginsPOSTArgumentsSchema, location="query", as_kwargs=True)
    @PLUGINS_API.response(HTTPStatus.NO_CONTENT)
    def post(self, url: str):
        """Trigger discovery of a new plugin. The plugin must be reachable via a seed to trigger the discovery!"""

        _, netloc, path, *_ = urlparse(url)

        seed_q = select(Seed).where(Seed.url.contains(netloc))

        seeds = DB.session.execute(seed_q).scalars().all()

        for seed in sorted(seeds, key=lambda s: (len(s.url), s.url)):
            seed_url_components = urlparse(seed.url)
            if seed_url_components[1] == netloc and path.startswith(
                seed_url_components[2]
            ):
                # starting plugin discovery for plugin from found seed
                discover_plugins_from_seeds.s(
                    seed=url, root_seed=seed.url, delete_on_missing=True
                ).apply_async()
                break

        return Response(status=HTTPStatus.NO_CONTENT)
