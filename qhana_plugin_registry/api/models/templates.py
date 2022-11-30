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
    CollectionResource,
    CollectionResourceSchema,
    MaBaseSchema,
    CursorPageArgumentsSchema
)

__all__ = [
    "TemplateTabSchema",
    "TemplateGroupSchema",
    "TemplateSchema",
    "TemplateTabData",
    "TemplateGroupData",
    "TemplateData",
]


class TemplatePageArgumentsSchema(CursorPageArgumentsSchema):
    template_id = ma.fields.Integer(data_key="template-id", allow_none=True, load_only=True)


class TemplateTabCollectionArgumentsSchema(MaBaseSchema):
    group = ma.fields.String(allow_none=True, load_only=True)


class TemplateTabSchema(ApiObjectSchema):
    name = ma.fields.String(required=True, allow_none=False, validate=Length(max=255))
    description = ma.fields.String(required=True, allow_none=False)
    location = ma.fields.String(required=True, allow_none=False, validate=Length(max=255))
    sort_key = ma.fields.Integer(required=True, allow_none=False, default=0)
    plugin_filter = ma.fields.String(required=True, allow_none=False)
    plugins = ma.fields.Nested(ApiLinkSchema)


class TemplateGroupSchema(CollectionResourceSchema):
    location = ma.fields.String(
        required=True, allow_none=False, dump_only=True, validate=Length(max=255)
    )


class TemplateSchema(ApiObjectSchema):
    name = ma.fields.String(required=True, allow_none=False, validate=Length(max=255))
    description = ma.fields.String(required=True, allow_none=False)
    tags = ma.fields.List(ma.fields.String(), required=True, allow_none=False)
    groups = ma.fields.List(
        ma.fields.Nested(ApiLinkSchema), required=True, allow_none=False, dump_only=True
    )


@dataclass
class TemplateTabData(BaseApiObject):
    name: str
    description: str
    location: str
    sort_key: int
    plugin_filter: str
    plugins: ApiLink


@dataclass
class TemplateGroupData(CollectionResource):
    location: str


@dataclass
class TemplateData(BaseApiObject):
    name: str
    description: str
    tags: Sequence[str]
    groups: Sequence[ApiLink]
