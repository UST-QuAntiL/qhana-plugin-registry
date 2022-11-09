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

from typing import Sequence, Tuple, TypeAlias, TypedDict, Union

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
    """The list of data last produced for which to get recommendations."""
    available_data: Sequence[Union[DataItemTuple, DataItem]]
    """The list of all available data."""
    experiment: str
    """Url to the experiment in the QHAna backend."""
    current_step: str
    """Url to the current step in a QHAna experiment (may not be the latest step)."""
