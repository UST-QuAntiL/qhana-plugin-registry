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

"""Module containing base models for building api models."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Type, Union

import marshmallow as ma
from marshmallow.validate import Length, Range

from ..util import camelcase

MAX_PAGE_ITEM_COUNT = 100


class MaBaseSchema(ma.Schema):
    """Base schema that automatically changes python snake case to camelCase in json."""

    # Uncomment to get ordered output
    # class Meta:
    #    ordered: bool = True

    def on_bind_field(self, field_name: str, field_obj: ma.fields.Field):
        field_obj.data_key = camelcase(field_obj.data_key or field_name)

    @classmethod
    def schema_name(cls) -> str:
        name = cls.__name__
        if name.endswith(("schema", "Schema", "SCHEMA")):
            name = name[:-6]
        return name


class ApiLinkBaseSchema(MaBaseSchema):
    """Schema for (non templated) api links."""

    href = ma.fields.Url(reqired=True, allow_none=False, dump_only=True)
    rel = ma.fields.List(
        ma.fields.String(allow_none=False, dump_only=True),
        validate=Length(min=1, error="At least one ref must be provided!"),
        reqired=True,
        allow_none=False,
        dump_only=True,
    )
    resource_type = ma.fields.String(reqired=True, allow_none=False, dump_only=True)
    doc = ma.fields.Url(allow_none=True, dump_only=True)
    schema = ma.fields.Url(allow_none=True, dump_only=True)
    name = ma.fields.String(allow_none=True, dump_only=True)

    @ma.post_dump()
    def remove_empty_attributes(
        self, data: Dict[str, Optional[Union[str, List[str]]]], **kwargs
    ):
        """Remove empty attributes from serialized links for a smaller and more readable output."""
        for key in ("doc", "schema", "resourceKey", "name"):
            value = data.get(key, False)
            if value is None or key == "resourceKey" and not value and value is not False:
                del data[key]
        if not data.get("queryKey", True):  # return True if not in dict
            del data["queryKey"]
        return data


class ApiLinkSchema(ApiLinkBaseSchema):
    resource_key = ma.fields.Mapping(
        ma.fields.String,
        ma.fields.String,
        reqired=False,
        allow_none=True,
        dump_only=True,
        metadata={
            "_jsonschema_type_mapping": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            }
        },
    )


class KeyedApiLinkSchema(ApiLinkSchema):
    """Schema for templated api links.

    The key attribute is a list of variable names that must be replaced in
    the url template to get a working url.
    """

    key = ma.fields.List(
        ma.fields.String(allow_none=False, dump_only=True),
        validate=Length(min=1, error="At least one ref must be provided!"),
        reqired=True,
        allow_none=False,
        dump_only=True,
    )
    query_key = ma.fields.List(
        ma.fields.String(allow_none=False, dump_only=True),
        validate=Length(min=1, error="At least one ref must be provided!"),
        reqired=True,
        allow_none=False,
        dump_only=True,
    )


class ApiObjectSchema(MaBaseSchema):
    self = ma.fields.Nested(ApiLinkSchema, allow_none=False, dump_only=True)


class NewApiObjectSchema(ApiObjectSchema):
    new = ma.fields.Nested(ApiLinkSchema, allow_none=False, dump_only=True)


class ChangedApiObjectSchema(ApiObjectSchema):
    changed = ma.fields.Nested(ApiLinkSchema, allow_none=False, dump_only=True)


class DeletedApiObjectSchema(ApiObjectSchema):
    deleted = ma.fields.Nested(ApiLinkSchema, allow_none=False, dump_only=True)
    redirect_to = ma.fields.Nested(ApiLinkSchema, allow_none=False, dump_only=True)


def _load_dynamic_api_response():
    """Model loader function with late import to avoid circular references."""
    from .dynamic_base_model import DynamicApiResponseSchema

    return DynamicApiResponseSchema(exclude=("embedded",))


class ApiResponseSchema(MaBaseSchema):
    links = ma.fields.Nested(
        ApiLinkSchema, many=True, reqired=True, allow_none=False, dump_only=True
    )
    keyed_links = ma.fields.Nested(
        KeyedApiLinkSchema, many=True, reqired=False, allow_none=True, dump_only=True
    )
    embedded = ma.fields.List(
        ma.fields.Nested(lambda: _load_dynamic_api_response()),
        reqired=False,
        allow_none=True,
        dump_only=True,
    )
    data = ma.fields.Nested(lambda: ApiObjectSchema(), reqired=True, allow_none=False)

    @ma.post_dump()
    def remove_empty_attributes(
        self, data: Dict[str, Optional[Union[str, List[str]]]], **kwargs
    ):
        """Remove empty attributes from serialized api response for a smaller and more readable output."""
        for key in ("keyedLinks", "key", "embedded"):
            if data.get(key, False) is None:
                del data[key]
        return data


_api_response_schema_cache = {}


def get_api_response_schema(
    schema: Union[ApiObjectSchema, Type[ApiObjectSchema]], name: Optional[str] = None
):
    assert isinstance(schema, ApiObjectSchema) or issubclass(
        schema, ApiObjectSchema
    ), "Only allow ApiObjects with a self link inside an ApiResponse!"
    if name is None:
        name = schema.schema_name()
    key = f"{name}ApiResponseSchema"
    if key not in _api_response_schema_cache:
        _api_response_schema_cache[key] = type(
            key,
            (ApiResponseSchema,),
            {"data": ma.fields.Nested(schema, reqired=True, allow_none=False)},
        )
    return _api_response_schema_cache[key]


class CollectionResourceSchema(ApiObjectSchema):
    collection_size = ma.fields.Integer(required=True, allow_none=False, dump_only=True)
    items = ma.fields.List(
        ma.fields.Nested(ApiLinkSchema),
        dump_default=tuple(),
        required=True,
        dump_only=True,
    )


class CursorPageSchema(ApiObjectSchema):
    collection_size = ma.fields.Integer(required=True, allow_none=False, dump_only=True)
    page = ma.fields.Integer(required=True, allow_none=False, dump_only=True)
    items = ma.fields.List(
        ma.fields.Nested(ApiLinkSchema),
        dump_default=tuple(),
        required=True,
        dump_only=True,
    )


class CursorPageArgumentsSchema(MaBaseSchema):
    cursor = ma.fields.String(allow_none=True, load_only=True)
    item_count = ma.fields.Integer(
        data_key="item-count",
        allow_none=True,
        load_only=True,
        load_default=25,
        validate=Range(1, MAX_PAGE_ITEM_COUNT, min_inclusive=True, max_inclusive=True),
    )
    sort = ma.fields.String(allow_none=True, load_only=True)


@dataclass(init=False)
class ApiLinkBase:
    # manual slots (and init) for smaller instances (links are used a lot)
    __slots__ = ("href", "rel", "resource_type", "doc", "schema", "name")

    href: str
    rel: Sequence[str]
    resource_type: str
    doc: Optional[str]
    schema: Optional[str]
    name: Optional[str]

    def __init__(
        self,
        href: str,
        rel: Sequence[str],
        resource_type: str,
        doc: Optional[str] = None,
        schema: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        self.href = href
        self.rel = rel
        self.resource_type = resource_type
        self.doc = doc
        self.schema = schema
        self.name = name


@dataclass(init=False)
class ApiLink(ApiLinkBase):
    # manual slots (and init) for smaller instances (links are used a lot)
    __slots__ = ("resource_key",)

    resource_key: Optional[Dict[str, str]]

    def __init__(
        self,
        href: str,
        rel: Sequence[str],
        resource_type: str,
        doc: Optional[str] = None,
        schema: Optional[str] = None,
        name: Optional[str] = None,
        resource_key: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(
            href=href,
            rel=rel,
            resource_type=resource_type,
            doc=doc,
            schema=schema,
            name=name,
        )
        self.resource_key = resource_key

    def copy_with(self, **kwargs):
        new_kwargs = {
            k: (kwargs[k] if k in kwargs else getattr(self, k))
            for k in self.__dataclass_fields__.keys()
        }
        return ApiLink(**new_kwargs)


@dataclass(init=False)
class KeyedApiLink(ApiLinkBase):
    # manual slots (and init) for smaller instances (links are used a lot)
    __slots__ = ("key", "query_key")

    key: Sequence[str]
    query_key: Sequence[str]

    def __init__(
        self,
        href: str,
        rel: Sequence[str],
        resource_type: str,
        doc: Optional[str] = None,
        schema: Optional[str] = None,
        name: Optional[str] = None,
        key: Sequence[str] = tuple(),
        query_key: Sequence[str] = tuple(),
    ) -> None:
        super().__init__(
            href=href,
            rel=rel,
            resource_type=resource_type,
            doc=doc,
            schema=schema,
            name=name,
        )
        self.key = key
        self.query_key = query_key


@dataclass
class BaseApiObject:
    self: ApiLink


@dataclass
class NewApiObjectRaw:
    self: Any
    new: Any


@dataclass
class NewApiObject(BaseApiObject):
    new: ApiLink


@dataclass
class ChangedApiObjectRaw:
    self: Optional[Any]
    changed: Any


@dataclass
class ChangedApiObject(BaseApiObject):
    changed: ApiLink


@dataclass
class DeletedApiObjectRaw:
    deleted: Any
    redirect_to: Union[ApiLink, Any]


@dataclass
class DeletedApiObject(BaseApiObject):
    deleted: ApiLink
    redirect_to: Optional[ApiLink]


@dataclass
class ApiResponse:
    links: Sequence[ApiLink]
    data: Any
    embedded: Optional[Sequence[Any]] = None
    keyed_links: Optional[Sequence[KeyedApiLink]] = None


@dataclass
class CollectionResource(BaseApiObject):
    collection_size: int
    items: Sequence[ApiLink]


@dataclass
class CursorPage(BaseApiObject):
    collection_size: int
    page: int
    items: Sequence[ApiLink]
