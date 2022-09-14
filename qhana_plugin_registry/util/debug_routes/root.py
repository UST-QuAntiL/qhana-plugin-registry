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

"""Module for the root endpoint of the debug routes. 
Contains the blueprint to avoid circular dependencies."""

from flask import Blueprint, render_template

DEBUG_BLP = Blueprint(
    "debug-routes", __name__, template_folder="templates", url_prefix="/debug"
)


@DEBUG_BLP.route("/")
@DEBUG_BLP.route("/index")
def index():
    return render_template("debug/index.html", title="Flask Template – Debug")
