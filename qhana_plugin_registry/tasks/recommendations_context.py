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

from typing import Optional, Union

from celery.utils.log import get_task_logger
from requests import get
from requests.exceptions import RequestException
from sqlalchemy.sql.expression import select

from ..celery import CELERY
from ..db.db import DB
from ..db.models.plugins import RAMP
from ..db.models.services import Service
from ..recommendations.util import DataItem, RecommendationContext

_name = "qhana-plugin-registry.tasks.recommendations_context"

TASK_LOGGER = get_task_logger(_name)

DEFAULT_BATCH_SIZE = 20

BACKEND_DATA_REF_KEYS = {"type", "contentType"}


def backend_data_ref_to_data_item(data_ref: dict) -> Optional[DataItem]:
    if data_ref.keys() < BACKEND_DATA_REF_KEYS:
        return None  # no type information available
    data_item: DataItem = {
        "data_type": data_ref["type"],
        "content_type": data_ref["contentType"],
    }
    if "name" in data_ref:
        data_item["name"] = data_ref["name"]
    return data_item


@CELERY.task(name=f"{_name}.fetch_available_data", bind=True)
def fetch_available_data(
    self, experiment_id: Union[str, int], timeout: float = 1
) -> RecommendationContext:
    """Fetch the data summarry of an experiment."""
    timeout = max(0, min(20, timeout))
    q = select(Service.url).filter(Service.service_id == "qhana-backend").limit(1)
    backend_url: Optional[str] = DB.session.execute(q).scalar_one_or_none()
    if backend_url is None:
        TASK_LOGGER.warning(
            "No qhana backend configured, could not fetch additional context"
        )
        return {}

    try:
        response = get(
            f"{backend_url.rstrip('/')}/experiments/{experiment_id}/data-summary",
            timeout=timeout,
        )
        return {"available_data": response.json()}
    except RequestException as err:
        TASK_LOGGER.warning(
            f"Error fetching experiment summarry for experiment {experiment_id}: {err}"
        )
        return {}


@CELERY.task(name=f"{_name}.fetch_step_details", bind=True)
def fetch_step_details(
    self, experiment_id: Union[str, int], step: Union[str, int], timeout: float = 1
) -> RecommendationContext:
    """Fetch details of an experiment step."""
    timeout = max(0, min(20, timeout))
    q = select(Service.url).filter(Service.service_id == "qhana-backend").limit(1)
    backend_url: Optional[str] = DB.session.execute(q).scalar_one_or_none()
    if backend_url is None:
        TASK_LOGGER.warning(
            "No qhana backend configured, could not fetch additional context"
        )
        return {}

    try:
        response = get(
            f"{backend_url.rstrip('/')}/experiments/{experiment_id}/timeline/{step}",
            timeout=timeout,
        )
        step_data = response.json()
    except RequestException as err:
        TASK_LOGGER.warning(
            f"Error fetching experiment summarry for experiment {experiment_id}: {err}"
        )
        return {}

    ramp_id: Optional[int] = None
    try:
        ramp_q = select(RAMP.id).filter(
            RAMP.plugin_type == step_data["processorName"],
            RAMP.version == step_data["processorVersion"],
        )
        ramp_id: Optional[int] = DB.session.execute(ramp_q).scalar_one_or_none()
    except KeyError:
        pass
    result_context: RecommendationContext

    input_data = [
        data
        for data_ref in step_data.get("inputData", [])
        if (data := backend_data_ref_to_data_item(data_ref))
    ]

    status = step_data.get("status", "PENDING")
    if status in ("PENDING", "UNKNOWN"):
        return {}
    if status == "FAILURE":
        result_context = {
            "step_success": False,
            "step_error": True,
        }
        if ramp_id is not None:
            result_context["current_plugin"] = ramp_id

        if input_data:
            result_context["step_input_data"] = input_data

        return result_context

    result_context = {
        "step_success": True,
        "step_error": False,
        "step_data_quality": step_data.get("resultQuality", "UNKNOWN"),
    }
    if ramp_id is not None:
        result_context["current_plugin"] = ramp_id

    if input_data:
        result_context["step_input_data"] = input_data

    output_data = [
        data
        for data_ref in step_data.get("outputData", [])
        if (data := backend_data_ref_to_data_item(data_ref))
    ]

    if output_data:
        result_context["step_output_data"] = output_data

    return result_context
