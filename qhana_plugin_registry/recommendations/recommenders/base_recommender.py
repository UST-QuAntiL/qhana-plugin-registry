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

from typing import Dict, Optional, Sequence, Union

from celery.canvas import Signature

from ..util import RecommendationContext


class PluginRecommender:

    __recommenders: Dict[str, "PluginRecommender"] = {}

    def __init_subclass__(cls) -> None:
        PluginRecommender.__recommenders[cls.__name__] = cls()

    @staticmethod
    def get_recommenders():
        return PluginRecommender.__recommenders

    @staticmethod
    def get_recommender(key: str) -> "Optional[PluginRecommender]":
        return PluginRecommender.__recommenders.get(key)

    def get_votes(
        self, context: RecommendationContext, timeout: float
    ) -> Union[Signature, Sequence[Signature], None]:
        raise NotImplementedError
