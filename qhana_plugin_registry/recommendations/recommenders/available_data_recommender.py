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

from typing import Dict, Optional, Sequence, Tuple, Union, cast

from celery.canvas import Signature
from sqlalchemy.sql.expression import ColumnElement, and_, distinct, or_, select

from .base_recommender import PluginRecommender
from ..util import DataItem, DataItemTuple, RecommendationContext
from ...celery import CELERY, FlaskTask
from ...db.db import DB
from ...db.filters import filter_data_to_ramp_by_data_types
from ...db.models.plugins import DATA_RELATION_CONSUMED, RAMP, DataToRAMP


class AvailableDataRecommender(PluginRecommender):
    def get_votes(
        self, context: RecommendationContext, timeout: float
    ) -> Union[Signature, Sequence[Signature], None]:

        available_data = context.get("available_data", {})
        if not available_data:
            return None

        if context.get("current_data", {}):
            # if recommendation is requested for specific data then don't recommend on all data
            return None

        if context.get("step_output_data", {}):
            # if recommendation is requested for specific data then don't recommend on all data
            return None

        task = cast(FlaskTask, fetch_votes)

        return task.s(available_data=available_data)


def extract_mimetypes(
    data_item: Union[DataItemTuple, DataItem]
) -> Tuple[Optional[str], Optional[str]]:
    if isinstance(data_item, (tuple, list)):
        return data_item[:2]
    return data_item.get("data_type"), data_item.get("content_type")


@CELERY.task(name=f"{__name__}.fetch_votes", bind=True)
def fetch_votes(self, available_data: Dict[str, Sequence[str]]):
    """Fetch plugins relevant for recommendations based on available data."""

    data_type_filters = [
        and_(
            *filter_data_to_ramp_by_data_types(
                data_type=data_type,
                content_type=content_types,
            )
        )
        for data_type, content_types in available_data.items()
    ]

    # all data requirements that can be fulfilled
    inner_q = (
        select(distinct(DataToRAMP.id))
        .filter(
            *filter_data_to_ramp_by_data_types(
                required=True,
                relation=DATA_RELATION_CONSUMED,
            )
        )
        .filter(or_(*data_type_filters))
    )

    # plugins with data requirements that are not fulfilled
    data_q = (
        select(distinct(DataToRAMP.ramp_id))
        .filter(
            *filter_data_to_ramp_by_data_types(
                required=True,
                relation=DATA_RELATION_CONSUMED,
            )
        )
        .filter(cast(ColumnElement, DataToRAMP.id).not_in(inner_q))
    )

    # inverted plugin id list
    q = select(RAMP.id).filter(cast(ColumnElement, RAMP.id).not_in(data_q))

    ids = DB.session.execute(q).scalars().all()

    return [(1, id_) for id_ in ids]
