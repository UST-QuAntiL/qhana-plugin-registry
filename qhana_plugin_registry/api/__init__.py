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

"""Module containing all API related code of the project."""

from flask import Flask

from .blueprint import API, ROOT_ENDPOINT
from .plugins import PLUGINS_API
from .env import ENV_API
from .seeds import SEEDS_API
from .services import SERVICES_API
from .templates import TEMPLATES_API

from . import root  # noqa

"""A single API instance. All api versions should be blueprints."""


def register_root_api(app: Flask):
    """Register the API with the flask app."""
    API.init_app(app)

    # register API blueprints (only do this after the API is registered with flask!)
    API.register_blueprint(ROOT_ENDPOINT)
    API.register_blueprint(PLUGINS_API)
    API.register_blueprint(ENV_API)
    API.register_blueprint(SEEDS_API)
    API.register_blueprint(SERVICES_API)
    API.register_blueprint(TEMPLATES_API)
