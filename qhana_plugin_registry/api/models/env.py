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

import marshmallow as ma
from marshmallow.validate import Length

from .base_models import ApiObjectSchema, BaseApiObject

__all__ = [
    "EnvSchema",
    "EnvData",
]


class EnvPageArgumentsSchema(ApiObjectSchema):
    name = ma.fields.String(required=False, allow_none=True, missing=None)


class EnvSchema(ApiObjectSchema):
    name = ma.fields.String(required=True, allow_none=False, validate=Length(max=255))
    value = ma.fields.String(required=True, allow_none=False)


@dataclass
class EnvData(BaseApiObject):
    name: str
    value: str
