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

"""Configuration module for testing the qhana_plugin_registry."""

from logging import INFO
import pytest
from dotenv import load_dotenv

from qhana_plugin_registry.db.db import DB

load_dotenv(".flaskenv")
load_dotenv(".env")

MODULE_NAME = "qhana_plugin_registry"


from qhana_plugin_registry import create_app
from qhana_plugin_registry.db.cli import create_db_function
from qhana_plugin_registry.util.config.celery_config import CELERY_DEBUG_CONFIG


DEFAULT_TEST_CONFIG = {
    "SECRET_KEY": "test",
    "DEBUG": False,
    "TESTING": True,
    "JSON_SORT_KEYS": True,
    "JSONIFY_PRETTYPRINT_REGULAR": False,
    "DEFAULT_LOG_SEVERITY": INFO,
    "DEFAULT_LOG_FORMAT_STYLE": "{",
    "DEFAULT_LOG_FORMAT": "{asctime} [{levelname:^7}] [{module:<30}] {message}    <{funcName}, {lineno}; {pathname}>",
    "CELERY": CELERY_DEBUG_CONFIG,
    "DEFAULT_FILE_STORE": "local_filesystem",
    "FILE_STORE_ROOT_PATH": "files",
    "OPENAPI_VERSION": "3.0.2",
    "OPENAPI_JSON_PATH": "api-spec.json",
    "OPENAPI_URL_PREFIX": "",
}


@pytest.fixture(scope="function")
def tmp_app():
    test_config = {}
    test_config.update(DEFAULT_TEST_CONFIG)
    test_config.update({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    tmp_app = create_app(test_config)
    yield tmp_app


@pytest.fixture()
def client(tmp_app):
    return tmp_app.test_client()


@pytest.fixture(scope="function")
def tmp_db(tmp_app):
    with tmp_app.app_context():
        create_db_function(tmp_app)
        yield DB
