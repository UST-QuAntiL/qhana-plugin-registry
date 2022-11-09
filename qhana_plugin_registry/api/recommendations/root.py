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

"""Module containing the root endpoint of the env API."""

from http import HTTPStatus
from typing import Tuple, cast

from flask.views import MethodView
from flask_smorest import Blueprint
from sqlalchemy.sql.expression import ColumnElement, select

from ..models.base_models import get_api_response_schema
from ..models.recommendations import (
    RecommendationArgumentsSchema,
    RecommendationCollectionSchema,
    RecommendationDataRaw,
)
from ..models.request_helpers import ApiResponseGenerator
from ...db.db import DB
from ...db.models.plugins import RAMP
from ...recommendations.main import get_recommendations
from ...recommendations.util import DataItem, RecommendationContext

RECOMMENDATIONS_API = Blueprint(
    name="api-recommendations",
    import_name=__name__,
    description="The basic recommendations API.",
    url_prefix="/api/recommendations",
)


@RECOMMENDATIONS_API.route("/")
class RecommendationsRootView(MethodView):
    """Root endpoint of the recommendations api."""

    @RECOMMENDATIONS_API.arguments(
        RecommendationArgumentsSchema, location="query", as_kwargs=True
    )
    @RECOMMENDATIONS_API.response(
        HTTPStatus.OK, get_api_response_schema(RecommendationCollectionSchema)
    )
    def get(self, **kwargs):
        """Get a list of plugin recommendations."""
        timeout = 5  # TODO read from config
        limit = 5  # TODO read from query
        recommendation_context: RecommendationContext = {
        }  
        if "data_type" in kwargs or "content_type" in kwargs:
            data_item: DataItem = {
                "data_type": kwargs.get("data_type", "*"),
                "content_type": kwargs.get("content_type", "*"),
            }
            if "data_name" in kwargs:
                data_item["name"] = kwargs["data_name"]
            recommendation_context["current_data"] = [data_item]
        # TODO read in other query args

        # TODO expand context with backend information

        votes = get_recommendations(recommendation_context, timeout)[:limit]

        plugins_ids, weights = cast(
            Tuple[Tuple[int, ...], Tuple[float, ...]], tuple(zip(*votes))
        )

        q = select(RAMP).filter(cast(ColumnElement, RAMP.id).in_(plugins_ids))
        plugins = DB.session.execute(q).scalars().all()

        query_params = cast(dict, RecommendationArgumentsSchema().dump(kwargs))

        response = ApiResponseGenerator.get_api_response(
            RecommendationDataRaw(weights=weights, plugins=plugins),
            query_params=query_params,
        )

        assert response is not None

        return response
