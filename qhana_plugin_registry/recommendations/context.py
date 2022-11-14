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

from typing import Optional, Sequence, cast

from celery import group
from celery.exceptions import TimeoutError
from celery.result import AsyncResult, GroupResult

from .util import RecommendationContext
from ..tasks.recommendations_context import fetch_available_data, fetch_step_details


def gather_context(
    context: RecommendationContext, timeout: float
) -> RecommendationContext:
    tasks = []

    if "experiment" in context:
        tasks.append(fetch_available_data.s(context["experiment"], timeout=timeout))
        if "current_step" in context:
            tasks.append(
                fetch_step_details.s(
                    context["experiment"], context["current_step"], timeout=timeout
                )
            )

    if not tasks:
        return context

    # group tasks and schedule group
    task_group = group(tasks)
    group_result: GroupResult = task_group.apply_async(
        expires=timeout, soft_time_limit=timeout
    )

    # wait for results (with timeout)
    try:
        group_result.get(timeout=timeout)
    except TimeoutError:
        pass  # gather all finished results instead

    children = cast(Optional[Sequence[AsyncResult]], group_result.children)

    if children is None:
        return context

    original_context = context.copy()

    for result in children:
        if result.successful():
            context.update(result.result)

    context.update(original_context)  # ensure that nothing was overridden

    return context
