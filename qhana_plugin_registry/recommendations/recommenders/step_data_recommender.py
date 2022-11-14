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
from ...db.filters import filter_data_to_ramp_by_consumed_data
from ...db.models.plugins import DATA_RELATION_CONSUMED, DataToRAMP


class StepDataRecommender(PluginRecommender):
    def get_votes(
        self, context: RecommendationContext, timeout: float
    ) -> Union[Signature, Sequence[Signature], None]:
        if context.get("current_step") is None:
            return None
        step_success = context.get("step_success")
        step_error = context.get("step_error")

        task = cast(FlaskTask, fetch_votes)

        tasks = []

        input_data = context.get("step_input_data", [])
        if input_data:
            tasks.append(task.s(data=input_data))
        if step_success and not step_error:
            if context.get("step_data_quality") in {"UNKNOWN", "BAD", "NEUTRAL", "GOOD"}:
                output_data = context.get("step_output_data", [])
                if output_data:
                    tasks.append(task.s(data=output_data))

        if not tasks:
            return None

        return tasks


def extract_mimetypes(
    data_item: Union[DataItemTuple, DataItem]
) -> Tuple[Optional[str], Optional[str]]:
    if isinstance(data_item, (tuple, list)):
        return data_item[:2]
    return data_item.get("data_type"), data_item.get("content_type")


@CELERY.task(name=f"{__name__}.fetch_votes", bind=True)
def fetch_votes(self, data: Sequence[Union[DataItemTuple, DataItem]]):
    """Fetch plugins relevant for recommendations based on given data types."""

    data_filters = filter_data_to_ramp_by_consumed_data(
        required=True,
        relation=DATA_RELATION_CONSUMED,
    )

    data_filters.append(
        or_(
            *[
                and_(
                    *filter_data_to_ramp_by_consumed_data(
                        *extract_mimetypes(data_item),
                    )
                )
                for data_item in data
            ]
        )
    )

    required_q: Select = (
        select(DataToRAMP.ramp_id, count())
        .filter(
            *filter_data_to_ramp_by_consumed_data(
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
