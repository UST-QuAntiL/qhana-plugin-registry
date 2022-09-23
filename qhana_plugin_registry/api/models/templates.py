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
from marshmallow.validate import Length

from .base_models import (
    ApiLink,
    ApiLinkSchema,
    ApiObjectSchema,
    BaseApiObject,
    MaBaseSchema,
)

__all__ = [
    "TemplateSchema",
    "TemplateTabData",
    "TemplateData",
]


class TemplateTabSchema(MaBaseSchema):
    name = ma.fields.String(required=True, allow_none=False, validate=Length(max=255))
    description = ma.fields.String(required=True, allow_none=False)
    plugin_filter = ma.fields.String(required=True, allow_none=False)
    plugins = ma.fields.List(ma.fields.Nested(ApiLinkSchema))


class TemplateSchema(ApiObjectSchema):
    name = ma.fields.String(required=True, allow_none=False, validate=Length(max=255))
    description = ma.fields.String(required=True, allow_none=False)
    tags = ma.fields.List(ma.fields.String(), required=True, allow_none=False)
    tabs = ma.fields.List(
        ma.fields.Nested(TemplateTabSchema()), required=True, allow_none=False
    )


@dataclass
class TemplateTabData:
    name: str
    description: str
    plugin_filter: str
    plugins: Sequence[ApiLink]


@dataclass
class TemplateData(BaseApiObject):
    name: str
    description: str
    tags: Sequence[str]
    tabs: Sequence[TemplateTabData]
