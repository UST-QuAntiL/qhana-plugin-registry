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
from typing import Sequence, Optional
import json
from packaging.specifiers import InvalidSpecifier, SpecifierSet
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
    CursorPageArgumentsSchema,
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
    template_id = ma.fields.Integer(
        data_key="template-id", allow_none=True, load_only=True
    )


class TemplateTabCollectionArgumentsSchema(MaBaseSchema):
    group = ma.fields.String(allow_none=True, load_only=True)


class TemplateTabSchema(ApiObjectSchema):
    name = ma.fields.String(required=True, allow_none=False, validate=Length(max=255))
    description = ma.fields.String(required=True, allow_none=False)
    icon = ma.fields.String(
        required=False, allow_none=True, missing=None, validate=Length(max=64)
    )
    location = ma.fields.String(required=True, allow_none=False, validate=Length(max=255))
    sort_key = ma.fields.Integer(required=True, allow_none=False, default=0)
    group_key = ma.fields.String(
        required=False, allow_none=False, missing="", validate=Length(max=32)
    )
    filter_string = ma.fields.String(required=True, allow_none=False, default="{}")
    plugins = ma.fields.Nested(ApiLinkSchema)

    @staticmethod
    def validate_filter(filter_dict: dict, path: str = ""):
        if len(filter_dict) == 0:
            return
        if len(filter_dict) > 1:
            raise ma.ValidationError(
                f"Invalid plugin filter: Only one filter key allowed per level. (Path: {path})"
            )
        key = next(iter(filter_dict.keys()))
        current_path = path + f".{key}"
        match filter_dict:
            case {"and": l} | {"or": l}:
                if not isinstance(l, list):
                    raise ma.ValidationError(
                        f"Invalid plugin filter: 'and' and 'or' must be lists, not '{type(l)}'. (Path: {current_path})"
                    )
                for f in l:
                    TemplateTabSchema.validate_filter(f, current_path)
            case {"not": f}:
                TemplateTabSchema.validate_filter(f, current_path)
            case {"name": f} | {"tag": f} | {"id": f} | {"type": f}:
                if not isinstance(f, str):
                    raise ma.ValidationError(
                        f"Invalid plugin filter: Name and tag must be strings '{f}'. (Path: {current_path})"
                    )
            case {"version": v}:
                if not isinstance(v, str):
                    raise ma.ValidationError(
                        f"Invalid plugin filter: Invalid version '{v}'. Version must be a PEP 440 specifier (string). (Path: {current_path})"
                    )
                try:
                    SpecifierSet(v)
                except InvalidSpecifier:
                    raise ma.ValidationError(
                        f"Invalid plugin filter: Invalid version '{v}'. Version must be a valid PEP 440 specifier. (Path: {current_path})"
                    )
            case _:
                raise ma.ValidationError(
                    f"Invalid plugin filter: Unknown key '{key}'. (Path: {current_path}))"
                )

    @ma.validates("filter_string")
    def validate_filter_string(self, value):
        if value == "":
            return
        try:
            filter_dict = json.loads(value)
        except json.JSONDecodeError:
            raise ma.ValidationError("Invalid plugin filter: Not a valid JSON string.")
        TemplateTabSchema.validate_filter(filter_dict)

    @ma.validates_schema
    def validate_leaf_flag(self, data, **kwargs):
        if data.get("group_key", ""):
            if data.get("filter_string", ""):
                raise ma.ValidationError(
                    "Filter string must be empty for non leaf nodes!", "filter_string"
                )
            if data.get("location", "").startswith("workspace"):
                raise ma.ValidationError(
                    "Tab goups cannot be used in the experiment workspace!", "group_key"
                )


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
    icon: Optional[str]
    location: str
    group_key: str
    sort_key: int
    filter_string: str
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
