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

from celery.utils.log import get_task_logger
from ..celery import CELERY

_name = "qhana-plugin-registry.tasks.tabs"

TASK_LOGGER = get_task_logger(_name)


@CELERY.task(name=f"{_name}.apply_filter_for_tab", bind=True, ignore_result=True)
def apply_filter_for_tab(self, tab_id):
    # TODO: evaluate plugin filter and set tab plugins accordingly
    pass


@CELERY.task(name=f"{_name}.update_plugin_lists", bind=True, ignore_result=True)
def update_plugin_lists(self, plugin_id):
    # TODO: reevaluate plugin filters and update corresponding plugins lists
    pass
