# Copyright 2026 University of Stuttgart
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

from typing import TypedDict, NotRequired, Sequence, Union, cast
from collections import Counter
from itertools import chain

from celery.canvas import Signature
from sqlalchemy.sql.expression import ColumnElement, select, literal, union_all
from sqlalchemy.sql.functions import count, sum as sum_

from .base_recommender import PluginRecommender
from ..util import RecommendationContext
from ...celery import CELERY, FlaskTask
from ...db.db import DB
from ...db.models.plugins import RAMP, TagToRAMP, PluginTag


class PluginRecommendation(TypedDict):
    plugin_id: NotRequired[str]
    tags: NotRequired[tuple[str] | list[str]]
    weight: NotRequired[int]


class RecommendationRule(TypedDict):
    recommend: PluginRecommendation
    plugin_id: NotRequired[str]
    tags: NotRequired[tuple[str] | list[str]]


RULES: Sequence[RecommendationRule] = [
    {"plugin_id": "costume-loader", "recommend": {"plugin_id": "wu-palmer", "weight": 5}},
    {
        "plugin_id": "costume-loader",
        "recommend": {"tags": ["data-cleaning"]},
    },
    {
        "plugin_id": "muse-for-music-loader",
        "recommend": {"plugin_id": "wu-palmer", "weight": 5},
    },
    {
        "plugin_id": "muse-for-music-loader",
        "recommend": {"tags": ["data-cleaning"]},
    },
    {"tags": ["data-cleaning"], "recommend": {"plugin_id": "wu-palmer", "weight": 5}},
    {"plugin_id": "wu-palmer", "recommend": {"plugin_id": "sym-max-mean", "weight": 5}},
    {
        "plugin_id": "sym-max-mean",
        "recommend": {"plugin_id": "sim-to-dist-transformers", "weight": 5},
    },
    {
        "plugin_id": "sim-to-dist-transformers",
        "recommend": {"plugin_id": "distance-aggregator", "weight": 5},
    },
    {
        "plugin_id": "distance-aggregator",
        "recommend": {"plugin_id": "mds", "weight": 5},
    },
    {"plugin_id": "mds", "recommend": {"tags": ["clustering"], "weight": 2}},
]


class RuleBasedRecommender(PluginRecommender):
    def get_votes(
        self, context: RecommendationContext, timeout: float
    ) -> Union[Signature, Sequence[Signature], None]:
        current_plugin = context.get("current_plugin", None)
        success = context.get("step_success", False)

        if not success or current_plugin is None:
            return None  # only evaluate rules on successful executions

        task = cast(FlaskTask, evaluate_rules)

        return task.s(current_plugin_id=current_plugin)


def strip_version_from_plugin_id(plugin_id: str) -> str:
    pos = plugin_id.find("@")
    if pos < 0:
        return plugin_id
    return plugin_id[:pos]


@CELERY.task(name=f"{__name__}.evaluate_rules", bind=True)
def evaluate_rules(self, current_plugin_id: int):
    """Fetch plugins relevant for recommendations based on preprogrammed rules."""

    current_plugin = RAMP.get_by_id(current_plugin_id)
    if current_plugin is None:
        return []
    current_tags = {t.tag for t in current_plugin.tags}

    identifier_votes: Counter[str] = Counter()
    tag_votes: Counter[frozenset[str]] = Counter()

    for rule in RULES:
        match rule:
            case {
                "plugin_id": current_plugin.full_id | current_plugin.plugin_id,
                "recommend": vote,
            }:
                if "plugin_id" in vote:
                    identifier_votes[vote["plugin_id"]] += vote.get("weight", 1)
                if "tags" in vote:
                    tag_votes[frozenset(vote["tags"])] += vote.get("weight", 1)
                continue
            case {"tags": tags_to_match, "recommend": vote} if (
                set(tags_to_match) <= current_tags
            ):
                if "plugin_id" in vote:
                    identifier_votes[vote["plugin_id"]] += vote.get("weight", 1)
                if "tags" in vote:
                    tag_votes[frozenset(vote["tags"])] += vote.get("weight", 1)
                continue

    plugin_votes: dict[int, int] = {}

    plugin_votes = gather_votes_by_identifier(identifier_votes)

    for plugin_id, vote in gather_votes_by_tags(tag_votes).items():
        if plugin_votes.get(plugin_id, 0) < vote:
            plugin_votes[plugin_id] = vote

    return [(vote, id_) for id_, vote in plugin_votes.items()]


def gather_votes_by_identifier(identifier_votes: dict[str, int]) -> dict[int, int]:
    plugin_votes: dict[int, int] = {}

    if not identifier_votes:
        return plugin_votes

    plugin_ids = {strip_version_from_plugin_id(p) for p in identifier_votes}
    q = select(
        cast(ColumnElement[int], RAMP.id),
        cast(ColumnElement[str], RAMP.plugin_id),
        cast(ColumnElement[str], RAMP.version),
    ).where(cast(ColumnElement, RAMP.plugin_id).in_(plugin_ids))

    ids: Sequence[tuple[int, str, str]] = DB.session.execute(q).tuples().all()

    for db_id, identifier, version in ids:
        current_vote = plugin_votes.get(db_id, 0)
        new_vote_a = identifier_votes.get(identifier, 0)
        new_vote_b = identifier_votes.get(f"{identifier}@{version}", 0)
        max_vote = max(0, current_vote, new_vote_a, new_vote_b)
        if max_vote:
            plugin_votes[db_id] = max_vote

    return plugin_votes


def gather_votes_by_tags(tag_votes: dict[frozenset[str], int]) -> dict[int, int]:
    if not tag_votes:
        return {}

    used_tags = tuple(set(chain(*tag_votes.keys())))

    tag_to_id = {t.tag: t.id for t in PluginTag.get_all(used_tags) if t.id is not None}

    c_ramp__id = cast(ColumnElement[int], RAMP.id)
    c_tag__ramp_id = cast(ColumnElement[int], TagToRAMP.ramp_id)
    tag_queries = []
    for tag_set, weight in tag_votes.items():
        # select all ramp ids that have all the required tags
        filter_q = (
            select(c_tag__ramp_id)
            .where(
                # only look for the required tags
                cast(ColumnElement, TagToRAMP.tag_id).in_([tag_to_id[t] for t in tag_set])
            )
            .group_by(c_tag__ramp_id)
            .having(
                # make sure that all required tags are present
                count(cast(ColumnElement[int], TagToRAMP.tag_id))
                == len(tag_set)
            )
        )

        # select ramp_id, vote where ramp has all required tags
        q = select(c_ramp__id, literal(weight).label("vote")).where(
            c_ramp__id.in_(filter_q)
        )
        tag_queries.append(q)

    # merge all queries
    u = union_all(*tag_queries).subquery()
    # sum up votes
    q = select(u.c.id, sum_(u.c.vote)).group_by(u.c.id)

    return dict(DB.session.execute(q).tuples().all())
