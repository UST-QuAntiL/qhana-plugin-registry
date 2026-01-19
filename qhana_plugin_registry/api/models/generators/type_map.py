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

from marshmallow.schema import Schema


@dataclass()
class ResourceMetadata:
    rel_type: str
    extra_link_rels: Sequence[str]
    endpoint: str
    schema: Type[Schema]
    schema_id: str
    collection_endpoint: Optional[str]


TYPE_TO_METADATA = {}


def populate_metadata():
    """
    To prevent circular imports, the endpoints will be populated here and the necessary imports will be done here.
    """
    from . import constants as c
    from ..env import EnvSchema
    from ..plugins import PluginSchema
    from ..recommendations import RecommendationCollectionSchema, RecommendationDataRaw
    from ..root import RootSchema
    from ..root_raw import RootDataRaw
    from ..templates_raw import TemplateGroupRaw
    from ..seeds import SeedSchema
    from ..service import ServiceSchema
    from ..templates import TemplateSchema, TemplateGroupSchema, TemplateTabSchema
    from ... import (
        ENV_API,
        PLUGINS_API,
        RECOMMENDATIONS_API,
        ROOT_ENDPOINT,
        SEEDS_API,
        SERVICES_API,
        TEMPLATES_API,
        TEMPLATE_TABS_API,
    )
    from ...env.env import EnvView
    from ...env.root import EnvRootView
    from ...plugins.plugin import PluginView
    from ...plugins.root import PluginsRootView
    from ...recommendations.root import RecommendationsRootView
    from ...root import RootView
    from ...seeds.root import SeedsRootView
    from ...seeds.seed import SeedView
    from ...services.root import ServicesRootView
    from ...services.service import ServiceView
    from ...templates.root import TemplatesRootView
    from ...templates.template import TemplateView
    from ...template_tabs.root import TemplateTabsRootView
    from ...template_tabs.tab import TemplateTabView
    from ....db.models.env import Env
    from ....db.models.plugins import RAMP
    from ....db.models.seeds import Seed
    from ....db.models.services import Service
    from ....db.models.templates import UiTemplate, TemplateTab

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
    TYPE_TO_METADATA[UiTemplate] = ResourceMetadata(
        rel_type=c.TEMPLATE_REL_TYPE,
        extra_link_rels=c.TEMPLATE_EXTRA_LINK_RELATIONS,
        endpoint=f"{TEMPLATES_API.name}.{TemplateView.__name__}",
        schema=TemplateSchema,
        schema_id=TemplateSchema.schema_name(),
        collection_endpoint=f"{TEMPLATES_API.name}.{TemplatesRootView.__name__}",
    )
    TYPE_TO_METADATA[TemplateGroupRaw] = ResourceMetadata(
        rel_type=c.TEMPLATE_TAB_REL_TYPE,
        extra_link_rels=c.TEMPLATE_TAB_EXTRA_LINK_RELATIONS,
        endpoint="",
        schema=TemplateGroupSchema,
        schema_id=TemplateGroupSchema.schema_name(),
        collection_endpoint=f"{TEMPLATE_TABS_API.name}.{TemplateTabsRootView.__name__}",
    )
    TYPE_TO_METADATA[TemplateTab] = ResourceMetadata(
        rel_type=c.TEMPLATE_TAB_REL_TYPE,
        extra_link_rels=c.TEMPLATE_TAB_EXTRA_LINK_RELATIONS,
        endpoint=f"{TEMPLATE_TABS_API.name}.{TemplateTabView.__name__}",
        schema=TemplateTabSchema,
        schema_id=TemplateTabSchema.schema_name(),
        collection_endpoint=f"{TEMPLATE_TABS_API.name}.{TemplateTabsRootView.__name__}",
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
    TYPE_TO_METADATA[RecommendationDataRaw] = ResourceMetadata(
        rel_type=c.RECOMMENDATION_REL_TYPE,
        extra_link_rels=tuple(),
        endpoint="",
        schema=RecommendationCollectionSchema,
        schema_id=RecommendationCollectionSchema.schema_name(),
        collection_endpoint=f"{RECOMMENDATIONS_API.name}.{RecommendationsRootView.__name__}",
    )
