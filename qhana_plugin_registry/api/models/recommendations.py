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

from dataclasses import dataclass
from typing import Sequence

import marshmallow as ma

from .base_models import CollectionResource, CollectionResourceSchema, MaBaseSchema
from ...db.models.plugins import RAMP

__all__ = [
    "RecommendationCollectionSchema",
    "RecommendationCollection",
    "RecommendationDataRaw",
]


@dataclass()
class RecommendationDataRaw:
    weights: Sequence[float]
    plugins: Sequence[RAMP]


class RecommendationArgumentsSchema(MaBaseSchema):
    current_plugin = ma.fields.Integer(
        data_key="plugin-id", allow_none=True, load_only=True
    )
    experiment_id = ma.fields.Integer(
        data_key="experiment", allow_none=True, load_only=True
    )
    current_step_id = ma.fields.Integer(data_key="step", allow_none=True, load_only=True)
    data_type = ma.fields.String(data_key="data-type", allow_none=True, load_only=True)
    content_type = ma.fields.String(
        data_key="content-type", allow_none=True, load_only=True
    )
    data_name = ma.fields.String(data_key="data-name", allow_none=True, load_only=True)
    timeout = ma.fields.Float(data_key="timeout", allow_none=True, load_only=True)
    limit = ma.fields.Integer(data_key="limit", allow_none=True, load_only=True)


class RecommendationCollectionSchema(CollectionResourceSchema):
    weights = ma.fields.List(
        ma.fields.Float(), dump_default=tuple(), required=True, dump_only=True
    )


@dataclass
class RecommendationCollection(CollectionResource):
    weights: Sequence[float]
