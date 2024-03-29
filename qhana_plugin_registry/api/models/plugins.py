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

from dataclasses import dataclass, field
from typing import Any, Dict, List

import marshmallow as ma
from marshmallow.validate import Regexp

from .base_models import (
    ApiObjectSchema,
    BaseApiObject,
    CursorPageArgumentsSchema,
    MaBaseSchema,
)

__all__ = [
    "PluginSchema",
    "PluginData",
]


class PluginsPageArgumentsSchema(CursorPageArgumentsSchema):
    plugin_id = ma.fields.String(data_key="plugin-id", allow_none=True, load_only=True)
    name = ma.fields.String(allow_none=True, load_only=True)
    version = ma.fields.String(allow_none=True, load_only=True)
    url = ma.fields.String(allow_none=True, load_only=True)
    type_ = ma.fields.String(data_key="type", allow_none=True, load_only=True)
    tags = ma.fields.String(allow_none=True, load_only=True)
    last_available_period = ma.fields.Integer(
        data_key="last-available-period", allow_none=True, load_only=True
    )
    input_data_type = ma.fields.String(
        data_key="input-data-type", allow_none=True, load_only=True
    )
    input_content_type = ma.fields.String(
        data_key="input-content-type", allow_none=True, load_only=True
    )
    template_tab = ma.fields.Integer(
        data_key="template-tab", allow_none=True, load_only=True
    )


class PluginsPOSTArgumentsSchema(MaBaseSchema):
    url = ma.fields.String(allow_none=False, load_only=True)


class DataMetadataSchema(MaBaseSchema):
    data_type = ma.fields.String(
        required=True,
        allow_none=False,
        metadata={"description": "The type of the output (e.g. distance-matrix)."},
    )
    content_type = ma.fields.List(
        ma.fields.String,
        required=True,
        allow_none=False,
        metadata={
            "description": "The media type (mime type) of the output data (e.g. application/json)."
        },
    )
    required = ma.fields.Boolean(
        required=True,
        allow_none=False,
        metadata={"description": "If the data is required or not."},
    )


class InputDataMetadataSchema(DataMetadataSchema):
    parameter = ma.fields.String(
        required=False,  # FIXME make this required once all plugins use this
        allow_none=False,
        metadata={"description": "The parameter where the input should be available at."},
    )


class PluginDependencyMetadataSchema(MaBaseSchema):
    parameter = ma.fields.String(
        required=True,
        allow_none=False,
        metadata={
            "description": "The parameter where the plugin url should be available at."
        },
    )
    plugin_type = ma.fields.String(
        required=False,
        allow_none=False,
        metadata={"description": "Type of the plugin dependency."},
    )
    tags = ma.fields.List(
        ma.fields.String,
        required=False,
        allow_none=False,
        metadata={
            "description": "A list of tags required to match a plugin. Tags startign with '!' must not be present on the plugin."
        },
    )
    name = ma.fields.String(
        required=False,
        allow_none=False,
        metadata={
            "description": "The name of the plugin dependency. Must be an exact match."
        },
    )
    version = ma.fields.String(
        required=False,
        allow_none=False,
        validate=Regexp(
            r"(>=?)?(v?[0-9]+(\.[0-9]+(\.[0-9]+)))(?:\s+(<=?)(v?[0-9]+(\.[0-9]+(\.[0-9]+))))?"
        ),
        metadata={
            "description": "The version of the plugin dependency. Examples: 'v1' (matches v1.?.?), 'v1.2.0', '>=v1.1.3', '>=v1.1.3 <v2.0.0'"
        },
    )
    required = ma.fields.Boolean(
        required=True,
        allow_none=False,
        metadata={"description": "If the data is required or not."},
    )

    @ma.post_dump()
    def remove_empty_attributes(self, data: Dict[str, Any], **kwargs):
        """Remove result attributes from serialized tasks that have not finished."""
        for attr in ("name", "type", "version", "tags"):
            if data[attr] == None:
                del data[attr]
        return data


class ProgressMetadataSchema(MaBaseSchema):
    value = ma.fields.Integer(
        required=True, allow_none=False, metadata={"description": "The progress value."}
    )
    start = ma.fields.Integer(
        required=False,
        allow_none=False,
        metadata={"description": "The progress start value."},
    )
    target = ma.fields.Integer(
        required=False,
        allow_none=False,
        metadata={"description": "The progress target value."},
    )
    unit = ma.fields.String(
        required=False,
        allow_none=False,
        metadata={"description": "The progress unit."},
    )


class StepMetadataSchema(MaBaseSchema):
    href = ma.fields.String(
        required=True,
        allow_none=False,
        metadata={"description": "The URL of the REST entry point resource."},
    )
    uiHref = ma.fields.String(
        required=True,
        allow_none=False,
        metadata={
            "description": "The URL of the micro frontend that corresponds to the REST entry point resource."
        },
    )
    stepId = ma.fields.String(
        required=False,
        allow_none=False,
        metadata={"description": 'ID of step, e.g., ``"step1"`` or ``"step1.step2b"``.'},
    )
    cleared = ma.fields.Boolean(
        required=False,
        allow_none=False,
        metadata={
            "description": "``false`` if step is awaiting input, only last step in list can be marked as ``false``."
        },
    )


class EntryPointSchema(MaBaseSchema):
    href = ma.fields.Url(
        required=True,
        allow_none=False,
        metadata={"description": "The URL of the REST entry point resource."},
    )
    ui_href = ma.fields.Url(
        required=True,
        allow_none=False,
        metadata={
            "description": "The URL of the micro frontend that corresponds to the REST entry point resource."
        },
    )
    plugin_dependencies = ma.fields.List(
        ma.fields.Nested(
            PluginDependencyMetadataSchema,
            required=True,
            allow_none=False,
            metadata={"description": "A list of possible plugin dependencies inputs."},
        )
    )
    data_input = ma.fields.List(
        ma.fields.Nested(
            InputDataMetadataSchema,
            required=True,
            allow_none=False,
            metadata={"description": "A list of possible data inputs."},
        )
    )
    data_output = ma.fields.List(
        ma.fields.Nested(
            DataMetadataSchema,
            required=True,
            allow_none=False,
            metadata={"description": "A list of possible data outputs."},
        )
    )


class PluginSchema(ApiObjectSchema):
    href = ma.fields.Url(
        required=True,
        allow_none=False,
        metadata={"description": "The root URL of the plugin API."},
    )
    title = ma.fields.String(
        required=True,
        allow_none=False,
        dump_only=True,
        metadata={"description": "Human readable plugin title."},
    )
    description = ma.fields.String(
        required=True,
        allow_none=False,
        dump_only=True,
        metadata={"description": "Human readable plugin description."},
    )
    identifier = ma.fields.String(
        required=True,
        allow_none=False,
        dump_only=True,
        metadata={"description": "Unique identifier ('name') of the plugin."},
    )
    version = ma.fields.String(
        required=True,
        allow_none=False,
        dump_only=True,
        metadata={"description": "Version of the plugin."},
    )
    plugin_type = ma.fields.String(
        required=True,
        allow_none=False,
        dump_only=True,
        metadata={"description": "Type of the plugin"},
    )
    entry_point = ma.fields.Nested(
        EntryPointSchema,
        required=True,
        allow_none=False,
        dump_only=True,
        metadata={"description": "The entry point of the plugin"},
    )
    tags = ma.fields.List(
        ma.fields.String(),
        required=True,
        allow_none=False,
        dump_only=True,
        metadata={
            "description": "A list of tags describing the plugin (e.g. classical-algorithm, quantum-algorithm, hybrid-algorithm)."
        },
    )


@dataclass
class DataMetadata:
    data_type: str
    content_type: List[str]
    required: bool


@dataclass
class InputDataMetadata(DataMetadata):
    parameter: str


@dataclass
class PluginDependencyMetadata:
    parameter: str
    name: str
    version: str
    tags: List[str]
    plugin_type: str
    required: bool


@dataclass
class EntryPoint:
    href: str
    ui_href: str
    data_input: List[InputDataMetadata] = field(default_factory=list)
    data_output: List[DataMetadata] = field(default_factory=list)
    plugin_dependencies: List[PluginDependencyMetadata] = field(default_factory=list)


@dataclass
class PluginData(BaseApiObject):
    href: str
    title: str
    description: str
    identifier: str
    version: str
    # TODO replace literal with PluginType after removing deprecated values
    plugin_type: str
    entry_point: EntryPoint
    tags: List[str] = field(default_factory=list)
