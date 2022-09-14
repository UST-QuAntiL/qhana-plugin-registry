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

from datetime import datetime

from celery.result import AsyncResult
from celery.utils.log import get_task_logger
from sqlalchemy.sql.expression import select

from .celery import CELERY
from .db.db import DB
from .db.models import plugins

_name = "qhana-plugin-registry"

TASK_LOGGER = get_task_logger(_name)


@CELERY.task(name=f"{_name}.discover_plugins", bind=True, ignore_result=True)
def add_step(self):
    TASK_LOGGER.debug("Discovery plugins...")  # TODO implement!
