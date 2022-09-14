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

"""Map(s) containing relations of types to api constants"""

from dataclasses import dataclass
from typing import Optional, Sequence, Type

from marshmallow.base import SchemaABC

from . import constants as c
from ..plugins import PluginSchema
from ..root import RootSchema
from ..root_raw import RootDataRaw
from ..seeds import SeedSchema
from ....db.models.plugins import RAMP
from ....db.models.seeds import Seed


@dataclass(frozen=True, slots=True)
class ResourceMetadata:
    rel_type: str
    extra_link_rels: Sequence[str]
    endpoint: str
    schema: Type[SchemaABC]
    schema_id: str
    collection_endpoint: Optional[str]


TYPE_TO_METADATA = {
    RootDataRaw: ResourceMetadata(
        rel_type=c.ROOT_REL_TYPE,
        extra_link_rels=c.ROOT_EXTRA_LINK_RELATIONS,
        endpoint=c.ROOT_RESOURCE,
        schema=RootSchema,
        schema_id=RootSchema.schema_name(),
        collection_endpoint=None,
    ),
    Seed: ResourceMetadata(
        rel_type=c.SEED_REL_TYPE,
        extra_link_rels=c.SEED_EXTRA_LINK_RELATIONS,
        endpoint=c.SEED_RESOURCE,
        schema=SeedSchema,
        schema_id=SeedSchema.schema_name(),
        collection_endpoint=c.SEED_PAGE_RESOURCE,
    ),
    RAMP: ResourceMetadata(
        rel_type=c.PLUGIN_REL_TYPE,
        extra_link_rels=c.PLUGIN_EXTRA_LINK_RELATIONS,
        endpoint=c.PLUGIN_RESOURCE,
        schema=PluginSchema,
        schema_id=PluginSchema.schema_name(),
        collection_endpoint=c.PLUGIN_PAGE_RESOURCE,
    ),
}
