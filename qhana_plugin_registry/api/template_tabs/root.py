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

"""Module containing the root endpoint of the template tabs/groups API."""

from http import HTTPStatus
from typing import List, cast, Optional, Union

from flask.views import MethodView
from flask_smorest import abort
from flask_smorest import Blueprint

from ..models.base_models import (
    CursorPageSchema,
    NewApiObjectRaw,
    NewApiObjectSchema,
    get_api_response_schema,
)
from ..models.request_helpers import (
    ApiResponseGenerator,
    EmbeddedResource,
    LinkGenerator,
    PageResource,
    CollectionResource,
)
from ..models.templates_raw import TemplateGroupRaw
from ..models.templates import TemplateTabSchema, TemplateTabCollectionArgumentsSchema
from ...db.db import DB
from ...db.models.templates import TemplateTab, UiTemplate
from ...tasks.plugin_filter import apply_filter_for_tab

TEMPLATE_TABS_API = Blueprint(
    name="api-template-tabs",
    import_name=__name__,
    description="The basic template tabs API.",
    url_prefix="/api/templates/<string:template_id>/tabs/",
)


@TEMPLATE_TABS_API.route("/")
class TemplateTabsRootView(MethodView):
    """Root endpoint of the template tab api."""

    @TEMPLATE_TABS_API.arguments(
        TemplateTabCollectionArgumentsSchema, location="query", as_kwargs=True
    )
    @TEMPLATE_TABS_API.response(HTTPStatus.OK, get_api_response_schema(CursorPageSchema))
    def get(self, template_id: str, **kwargs):
        """Get a list of templates."""
        if not template_id or not template_id.isdecimal():
            abort(
                HTTPStatus.BAD_REQUEST, message="The template id is in the wrong format!"
            )

        found_template = cast(
            Optional[UiTemplate], UiTemplate.get_by_id(int(template_id))
        )
        if not found_template:
            abort(HTTPStatus.NOT_FOUND, message="Template not found.")

        group: Optional[str] = kwargs.get("group", None)

        tabs: List[TemplateTab]

        if group:
            tabs = [t for t in found_template.tabs if t.location == group]
        else:
            tabs = list(found_template.tabs)
        tabs = sorted(tabs, key=lambda t: t.sort_key)

        embedded_responses = (
            ApiResponseGenerator.get_api_response(EmbeddedResource(item)) for item in tabs
        )
        embedded_items = [response for response in embedded_responses if response]

        resource: Union[CollectionResource, TemplateGroupRaw]

        if group:
            resource = TemplateGroupRaw(
                template=found_template,
                location=group,
                items=tabs,
            )
        else:
            items = [
                link
                for r in embedded_items
                if (link := LinkGenerator.get_link_of(r.data))
            ]
            resource = CollectionResource(
                TemplateTab,
                resource=found_template,
                item_links=items,
                collection_size=len(items),
            )

        query_params = {}

        if group:
            query_params["group"] = group

        return ApiResponseGenerator.get_api_response(
            resource,
            query_params=query_params,
            extra_embedded=embedded_items,
        )

    @TEMPLATE_TABS_API.arguments(TemplateTabSchema(exclude=("self", "plugins")))
    @TEMPLATE_TABS_API.response(
        HTTPStatus.OK, get_api_response_schema(NewApiObjectSchema)
    )
    def post(self, tab_data, template_id: str):
        if not template_id or not template_id.isdecimal():
            abort(
                HTTPStatus.BAD_REQUEST, message="The template id is in the wrong format!"
            )
        found_template = cast(
            Optional[UiTemplate], UiTemplate.get_by_id(int(template_id))
        )
        if not found_template:
            abort(HTTPStatus.NOT_FOUND, message="Template not found.")

        created_tab = TemplateTab(
            template=found_template,
            name=tab_data["name"],
            description=tab_data["description"],
            sort_key=tab_data["sort_key"],
            location=tab_data["location"],
            filter_string=tab_data["filter_string"],
        )
        DB.session.add(created_tab)
        DB.session.commit()
        DB.session.refresh(created_tab)
        apply_filter_for_tab.delay(created_tab.id)

        DB.session.refresh(found_template)
        extra_embedded = []

        # embed the template as well, as template groups might have changed
        embedded = ApiResponseGenerator.get_api_response(EmbeddedResource(found_template))
        if embedded:
            extra_embedded.append(embedded)

        return ApiResponseGenerator.get_api_response(
            NewApiObjectRaw(self=PageResource(UiTemplate), new=created_tab),
            extra_embedded=extra_embedded,
        )
