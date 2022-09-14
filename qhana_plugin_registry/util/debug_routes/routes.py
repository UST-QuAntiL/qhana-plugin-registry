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

"""Module containing debug routes index page."""

from flask import current_app, render_template

from .root import DEBUG_BLP


@DEBUG_BLP.route("/routes")
def routes():
    """Render all registered routes."""
    output = []
    for rule in current_app.url_map.iter_rules():

        line = {
            "endpoint": rule.endpoint,
            "methods": ", ".join(rule.methods),
            "url": rule.rule,
        }
        output.append(line)
    output.sort(key=lambda x: x["url"])
    return render_template(
        "debug/routes/all.html", title="Flask Template – Routes", routes=output
    )
