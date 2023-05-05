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
from typing import List, cast, Sequence, Optional

from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint
from sqlalchemy.sql.expression import ColumnElement

from ..models.base_models import (
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
from ..models.templates import TemplateSchema, TemplatePageArgumentsSchema
from ...db.db import DB
from ...db.models.templates import UiTemplate, TemplateTag
from ...db.filters import filter_templates_by_template_id

TEMPLATES_API = Blueprint(
    name="api-templates",
    import_name=__name__,
    description="The basic templates url API.",
    url_prefix=current_app.config.get("URL_PREFIX", "/api") + "/templates",
)


@TEMPLATES_API.route("/")
class TemplatesRootView(MethodView):
    """Root endpoint of the template api."""

    @TEMPLATES_API.arguments(
        TemplatePageArgumentsSchema, location="query", as_kwargs=True
    )
    @TEMPLATES_API.response(HTTPStatus.OK, get_api_response_schema(CursorPageSchema))
    def get(self, **kwargs):
        """Get a list of templates."""

        template_id: Optional[int] = kwargs.pop("template_id", None)

        pagination_options: PaginationOptions = prepare_pagination_query_args(
            **kwargs, _sort_default="name"
        )

        filter_ = filter_templates_by_template_id(template_id=template_id)

        pagination_info = default_get_page_info(
            UiTemplate,
            filter_,
            pagination_options,
            {
                "id": cast(ColumnElement, UiTemplate.id),
                "name": cast(ColumnElement, UiTemplate.name),
            },
        )

        templates: List[UiTemplate] = DB.session.execute(
            pagination_info.page_items_query
        ).scalars()

        embedded_responses = (
            ApiResponseGenerator.get_api_response(EmbeddedResource(item))
            for item in templates
        )
        embedded_items = [response for response in embedded_responses if response]
        items = [
            link for r in embedded_items if (link := LinkGenerator.get_link_of(r.data))
        ]

        last_page = pagination_info.last_page

        extra_query = {}
        if template_id is not None:
            extra_query["template-id"] = str(template_id)

        page_resource = PageResource(
            UiTemplate,
            page_number=pagination_info.cursor_page,
            active_page=pagination_info.cursor_page,
            last_page=last_page.page if last_page else None,
            collection_size=pagination_info.collection_size,
            item_links=items,
        )
        self_link = LinkGenerator.get_link_of(
            page_resource,
            query_params=pagination_options.to_query_params(extra_params=extra_query),
        )
        assert self_link is not None

        extra_links = generate_page_links(
            page_resource, pagination_info, pagination_options, extra_query
        )

        first_page_link = LinkGenerator.get_link_of(
            page_resource.get_page(1),
            query_params=pagination_options.to_query_params(
                cursor=None, extra_params=extra_query
            ),
        )
        assert first_page_link is not None

        return ApiResponseGenerator.get_api_response(
            page_resource,
            query_params=pagination_options.to_query_params(extra_params=extra_query),
            extra_links=[
                first_page_link,
                self_link,
                *extra_links,
            ],
            extra_embedded=embedded_items,
        )

    @TEMPLATES_API.arguments(TemplateSchema(exclude=("self", "groups")))
    @TEMPLATES_API.response(HTTPStatus.OK, get_api_response_schema(NewApiObjectSchema))
    def post(self, template_data):
        tags: Sequence[str] = (*template_data.get("tags", []),)

        created_template = UiTemplate(
            name=template_data["name"],
            description=template_data["description"],
            tags=TemplateTag.get_or_create_all(tags),
            tabs=[],  # TODO: figure out tabs
        )
        DB.session.add(created_template)
        DB.session.commit()

        return ApiResponseGenerator.get_api_response(
            NewApiObjectRaw(self=PageResource(UiTemplate), new=created_template)
        )
