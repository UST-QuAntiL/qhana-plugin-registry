# Copyright 2023 University of Stuttgart
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

"""Functions for opening files from external URLs."""

from re import Pattern
from typing import Literal

from flask import Flask
from flask.globals import current_app
from requests import Session
from requests.models import Response

REQUEST_SESSION = Session()


def map_url(
    url: str, config_key: Literal["URL_MAP_FROM_LOCALHOST", "URL_MAP_TO_LOCALHOST"]
) -> str:
    if current_app:
        # apply rewrite rules from the current app context in sequence
        app: Flask = current_app
        pattern: Pattern
        replacement: str
        for pattern, replacement in app.config.get(config_key, []):
            url = pattern.sub(replacement, url)

    return url


def open_url(url: str, raise_on_error_status=True, **kwargs) -> Response:
    """Open an url with request.

    (see :py:meth:`~requests.Session.request` for parameters)

    It is best to use this function in a ``with``-statement to get autoclosing behaviour
    for the returned response. The returned response acts as a context manager.

    For streaming access set ``stream=True``.

    An appropriate exception is raised for an error status. To ignore an error status set ``raise_on_error_status=False``.
    """

    url = map_url(url, "URL_MAP_FROM_LOCALHOST")

    url_data = REQUEST_SESSION.get(url, **kwargs)
    if raise_on_error_status:
        url_data.raise_for_status()
    return url_data
