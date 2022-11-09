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

"""Useful constants for building requests."""

from ..root_raw import RootDataRaw

ROOT_RESOURCE_DUMMY = RootDataRaw("dummy")

# special relations ############################################################

API_REL = "api"

COLLECTION_REL = "collection"

PAGE_REL = "page"

FIRST_REL = "first"
LAST_REL = "last"

PREV_REL = "prev"
NEXT_REL = "next"

UP_REL = "up"
NAV_REL = "nav"

GET_REL = "get"
PUT_REL = "put"
POST_REL = "post"
DELETE_REL = "delete"

CREATE_REL = "create"
UPDATE_REL = "update"
RESTORE_REL = "restore"

NEW_REL = "new"
CHANGED_REL = "changed"
DELETED_REL = "deleted"

DANGER_REL = "danger"
PERMANENT_REL = "permanent"


# key variables ################################################################

# normal keys
PLUGIN_ID_KEY = "pluginId"
PLUGIN_VERSION_KEY = "pluginVersion"

ENV_ID_KEY = "envId"

SERVICE_ID_KEY = "serviceId"

TEMPLATE_ID_KEY = "wsTemplateId"

SEED_ID_KEY = "seedId"

PLUGIN_ID_KEY = "pluginId"


# query keys
ITEM_COUNT_QUERY_KEY = "item-count"


# key defaults
ITEM_COUNT_DEFAULT = "25"


# relation types ###############################################################

ROOT_REL_TYPE = "api-root"

ENV_REL_TYPE = "env"

SERVICE_REL_TYPE = "service"

TEMPLATE_REL_TYPE = "ws-template"

SEED_REL_TYPE = "seed"

PLUGIN_REL_TYPE = "plugin"

RECOMMENDATION_REL_TYPE = "plugin-recommendation"

# link to relations ############################################################

ROOT_EXTRA_LINK_RELATIONS = (
    SEED_REL_TYPE,
    SERVICE_REL_TYPE,
    ENV_REL_TYPE,
    PLUGIN_REL_TYPE,
    RECOMMENDATION_REL_TYPE,
)

ENV_EXTRA_LINK_RELATIONS = tuple()

SERVICE_EXTRA_LINK_RELATIONS = tuple()

TEMPLATE_EXTRA_LINK_RELATIONS = tuple()

SEED_EXTRA_LINK_RELATIONS = tuple()

PLUGIN_EXTRA_LINK_RELATIONS = tuple()


# endpoints ####################################################################

API_SPEC_RESOURCE = "api-docs.openapi_json"
