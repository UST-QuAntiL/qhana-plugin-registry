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

from typing import Dict, Sequence, Tuple, TypedDict, Union
from typing_extensions import TypeAlias

DataItemTuple: TypeAlias = Union[Tuple[str, str], Tuple[str, str, str]]
"""Either (data_type, content_type) or (data_type, content_type, name)."""


class DataItem(TypedDict, total=False):
    name: str
    data_type: str
    content_type: str


class RecommendationContext(TypedDict, total=False):
    current_plugin: int
    """The plugin registry id of the plugin last used for which to get recommendations."""
    current_data: Sequence[Union[DataItemTuple, DataItem]]
    """The list of data for which to get recommendations."""
    step_input_data: Sequence[Union[DataItemTuple, DataItem]]
    """The list of data consumed by a step for which to get recommendations."""
    step_output_data: Sequence[Union[DataItemTuple, DataItem]]
    """The list of data produced by a step for which to get recommendations."""
    available_data: Dict[str, Sequence[str]]
    """The list of all available data."""
    experiment: Union[str, int]
    """Url to the experiment in the QHAna backend."""
    current_step: Union[str, int]
    """Url to the current step in a QHAna experiment (may not be the latest step)."""
    step_success: bool
    """True if successful, False if not."""
    step_error: bool
    """True if step was not successful."""
    step_data_quality: str
    """The data quality of the step."""
