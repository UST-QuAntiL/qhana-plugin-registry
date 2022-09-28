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


@dataclass()
class ResourceMetadata:
    rel_type: str
    extra_link_rels: Sequence[str]
    endpoint: str
    schema: Type[SchemaABC]
    schema_id: str
    collection_endpoint: Optional[str]


TYPE_TO_METADATA = {
}


def populate_metadata():
    """
    To prevent circular imports, the endpoints will be populated here and the necessary imports will be done here.
    """
    from . import constants as c
    from ..plugins import PluginSchema
    from ..root import RootSchema
    from ..root_raw import RootDataRaw
    from ..seeds import SeedSchema
    from ..env import EnvSchema
    from ..service import ServiceSchema
    from ..templates import TemplateSchema
    from ....db.models.plugins import RAMP
    from ....db.models.seeds import Seed
    from ....db.models.env import Env
    from ....db.models.services import Service
    from ....db.models.templates import WorkspaceTemplate
    from ... import ROOT_ENDPOINT, ENV_API, SERVICES_API, TEMPLATES_API, SEEDS_API, PLUGINS_API
    from ...root import RootView
    from ...env.env import EnvView
    from ...env.root import EnvRootView
    from ...services.service import ServiceView
    from ...services.root import ServicesRootView
    from ...templates.template import TemplateView
    from ...templates.root import TemplatesRootView
    from ...seeds.seed import SeedView
    from ...seeds.root import SeedsRootView
    from ...plugins.plugin import PluginView
    from ...plugins.root import PluginsRootView

    TYPE_TO_METADATA[RootDataRaw] = ResourceMetadata(
        rel_type=c.ROOT_REL_TYPE,
        extra_link_rels=c.ROOT_EXTRA_LINK_RELATIONS,
        endpoint=f"{ROOT_ENDPOINT.name}.{RootView.__name__}",
        schema=RootSchema,
        schema_id=RootSchema.schema_name(),
        collection_endpoint=None,
    )
    TYPE_TO_METADATA[Env] = ResourceMetadata(
        rel_type=c.ENV_REL_TYPE,
        extra_link_rels=c.ENV_EXTRA_LINK_RELATIONS,
        endpoint=f"{ENV_API.name}.{EnvView.__name__}",
        schema=EnvSchema,
        schema_id=EnvSchema.schema_name(),
        collection_endpoint=f"{ENV_API.name}.{EnvRootView.__name__}",
    )
    TYPE_TO_METADATA[Service] = ResourceMetadata(
        rel_type=c.SERVICE_REL_TYPE,
        extra_link_rels=c.SERVICE_EXTRA_LINK_RELATIONS,
        endpoint=f"{SERVICES_API.name}.{ServiceView.__name__}",
        schema=ServiceSchema,
        schema_id=ServiceSchema.schema_name(),
        collection_endpoint=f"{SERVICES_API.name}.{ServicesRootView.__name__}",
    )
    TYPE_TO_METADATA[WorkspaceTemplate] = ResourceMetadata(
        rel_type=c.TEMPLATE_REL_TYPE,
        extra_link_rels=c.TEMPLATE_EXTRA_LINK_RELATIONS,
        endpoint=f"{TEMPLATES_API.name}.{TemplateView.__name__}",
        schema=TemplateSchema,
        schema_id=TemplateSchema.schema_name(),
        collection_endpoint=f"{TEMPLATES_API.name}.{TemplatesRootView.__name__}",
    )
    TYPE_TO_METADATA[Seed] = ResourceMetadata(
        rel_type=c.SEED_REL_TYPE,
        extra_link_rels=c.SEED_EXTRA_LINK_RELATIONS,
        endpoint=f"{SEEDS_API.name}.{SeedView.__name__}",
        schema=SeedSchema,
        schema_id=SeedSchema.schema_name(),
        collection_endpoint=f"{SEEDS_API.name}.{SeedsRootView.__name__}",
    )
    TYPE_TO_METADATA[RAMP] = ResourceMetadata(
        rel_type=c.PLUGIN_REL_TYPE,
        extra_link_rels=c.PLUGIN_EXTRA_LINK_RELATIONS,
        endpoint=f"{PLUGINS_API.name}.{PluginView.__name__}",
        schema=PluginSchema,
        schema_id=PluginSchema.schema_name(),
        collection_endpoint=f"{PLUGINS_API.name}.{PluginsRootView.__name__}",
    )
