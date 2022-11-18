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

from typing import Optional, Sequence, Tuple, Union, cast

from celery.canvas import Signature
from sqlalchemy.sql.expression import Select, and_, or_, select
from sqlalchemy.sql.functions import count

from .base_recommender import PluginRecommender
from ..util import DataItem, DataItemTuple, RecommendationContext
from ...celery import CELERY, FlaskTask
from ...db.db import DB
from ...db.filters import filter_data_to_ramp_by_data_types
from ...db.models.plugins import DATA_RELATION_CONSUMED, DataToRAMP


class CurrentDataRecommender(PluginRecommender):
    def get_votes(
        self, context: RecommendationContext, timeout: float
    ) -> Union[Signature, Sequence[Signature], None]:

        current_data = context.get("current_data", [])
        if not current_data:
            return None

        task = cast(FlaskTask, fetch_votes)

        return task.s(current_data=current_data)


def extract_mimetypes(
    data_item: Union[DataItemTuple, DataItem]
) -> Tuple[Optional[str], Optional[str]]:
    if isinstance(data_item, (tuple, list)):
        return data_item[:2]
    return data_item.get("data_type"), data_item.get("content_type")


@CELERY.task(name=f"{__name__}.fetch_votes", bind=True)
def fetch_votes(self, current_data: Sequence[Union[DataItemTuple, DataItem]]):
    """Fetch plugins relevant for recommendations based on current data."""

    data_filters = filter_data_to_ramp_by_data_types(
        required=True,
        relation=DATA_RELATION_CONSUMED,
    )

    data_filters.append(
        or_(
            *[
                and_(
                    *filter_data_to_ramp_by_data_types(
                        *extract_mimetypes(data_item),
                    )
                )
                for data_item in current_data
            ]
        )
    )

    required_q: Select = (
        select(DataToRAMP.ramp_id, count())
        .filter(
            *filter_data_to_ramp_by_data_types(
                required=True,
                relation=DATA_RELATION_CONSUMED,
            )
        )
        .group_by(DataToRAMP.ramp_id)
    )

    required_alias = required_q.subquery("required")

    q: Select = (
        select(DataToRAMP.ramp_id, count(), required_alias.c[1])
        .filter(*data_filters)
        .group_by(DataToRAMP.ramp_id)
    )

    q = q.join(
        required_alias,
        onclause=DataToRAMP.ramp_id == required_alias.c.ramp_id,
        isouter=True,
    )

    ids: Sequence[Tuple[int, int, int]] = DB.session.execute(q).all()

    return [
        (min(1, (available / required) if required not in (0, None) else 1), id_)
        for id_, available, required in ids
    ]
