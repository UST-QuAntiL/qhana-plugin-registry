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

from typing import (
    Dict,
    Iterator,
    List,
    NamedTuple,
    Sequence,
    Tuple,
    TypeAlias,
    Union,
    cast,
)

from celery import group
from celery.canvas import Signature
from celery.exceptions import TimeoutError
from celery.result import AsyncResult, GroupResult

from .recommenders import PluginRecommender
from .util import RecommendationContext

Vote: TypeAlias = Tuple[float, int]


class VoteTuple(NamedTuple):
    recommender: str
    plugin_id: int
    vote: float


def flatten_results(
    results: Sequence[Tuple[str, Union[Vote, Sequence[Vote]]]]
) -> Iterator[VoteTuple]:
    for name, result in results:
        if (
            len(result) == 2
            and isinstance(result[0], (int, float))
            and isinstance(result[1], int)
        ):
            yield VoteTuple(name, result[1], result[0])
            continue
        result = cast(Sequence[Vote], result)
        for vote in result:
            yield VoteTuple(name, vote[1], vote[0])


def merge_results(
    results: Sequence[Tuple[str, Union[Vote, Sequence[Vote]]]],
    multipliers: Dict[str, float],
) -> Sequence[Tuple[int, float]]:
    plugins: Dict[int, float] = {}
    for recommender, plugin_id, vote in flatten_results(results):
        weight = multipliers.get(recommender, 1)
        old_vote = plugins.get(plugin_id, 0)
        plugins[plugin_id] = old_vote + (vote * weight)
    merged_results = ((p_id, votes) for p_id, votes in plugins.items())
    return sorted(merged_results, key=lambda r: r[1], reverse=True)


def get_recommendations(
    context: RecommendationContext, timeout: float
) -> Sequence[Tuple[int, float]]:
    recommenders = PluginRecommender.get_recommenders()
    tasks: Sequence[Tuple[str, Signature]] = []

    # get tasks from recommenders
    for name, rec in recommenders.items():
        try:
            sig = rec.get_votes(context, timeout)
            if sig is None:
                continue
            if isinstance(sig, Signature):
                tasks.append((name, sig))
            else:
                for s in sig:
                    tasks.append((name, s))
        except NotImplementedError:
            pass

    # group tasks and schedule group
    task_group = group([t[1] for t in tasks])
    group_result: GroupResult = task_group.apply_async(
        expires=timeout, soft_time_limit=timeout
    )

    # link individual task results back to recommenders
    children = group_result.children
    assert children is not None
    results: List[Tuple[str, AsyncResult]] = [
        (t[0], r) for (t, r) in zip(tasks, children)
    ]

    # wait for results (with timeout)
    try:
        group_result.get(timeout=timeout)
    except TimeoutError:
        pass  # gather all finished results instead

    # gather finished results
    votes = [(n, r.result) for n, r in results if r.successful()]
    merged_votes = merge_results(votes, {})  # TODO populate multipliers from settings
    return merged_votes
