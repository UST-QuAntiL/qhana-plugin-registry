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

from flask_smorest import Api
from flask_smorest import Blueprint as SmorestBlueprint

API = Api(spec_kwargs={"title": "RAMP Registry API", "version": "v1"})


ROOT_ENDPOINT = SmorestBlueprint(
    "api-root",
    "root",
    url_prefix="/api",
    description="The API endpoint pointing towards all resources.",
)
