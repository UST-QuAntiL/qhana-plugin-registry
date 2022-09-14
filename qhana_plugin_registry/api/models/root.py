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

"""Module containing all API schemas for the root API endpoint."""

from dataclasses import dataclass

import marshmallow as ma

from . import base_models as bm

__all__ = [
    "RootSchema",
    "RootData",
]


class RootSchema(bm.ApiObjectSchema):
    title = ma.fields.String(required=True, allow_none=False, dump_only=True)


@dataclass
class RootData(bm.BaseApiObject):
    title: str
