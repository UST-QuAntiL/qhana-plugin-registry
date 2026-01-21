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

from typing import Any

import marshmallow as ma
from marshmallow.schema import Schema
from marshmallow.utils import is_collection

from . import base_models as bm
from . import request_helpers as rh
from .generators import type_map as tm


class DynamicApiResponseSchema(bm.ApiResponseSchema):
    data = ma.fields.Method("dump_data", required=True, allow_none=False, dump_only=True)

    def dump_data(self, obj: Any) -> Any:
        attr: Any = super().get_attribute(obj, "data", None)
        many: bool = is_collection(attr)
        assert not many, "Collections are not supported!"
        attr_type = type(attr)
        schema = tm.TYPE_TO_METADATA[attr_type].schema
        if issubclass(schema, Schema):
            schema = schema()
        return schema.dump(rh.ApiObjectGenerator.get_api_object(attr))
