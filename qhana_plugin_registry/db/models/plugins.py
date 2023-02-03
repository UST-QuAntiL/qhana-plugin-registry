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

import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import partial
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from packaging.version import LegacyVersion
from packaging.version import parse as parse_version
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select
from sqlalchemy.sql import sqltypes as sql
from sqlalchemy.sql.schema import Column, ForeignKey, Index, UniqueConstraint

from .model_helpers import (
    ExistsMixin,
    IdMixin,
    NameDescriptionMixin,
)
from .seeds import Seed
from ..db import DB, REGISTRY

DATA_RELATION_CONSUMED = "consumed"
DATA_RELATION_PRODUCED = "produced"


def get_version_sorting_string(version: str) -> str:
    """
    Formats a version number into a string that is more likely to be sorted
    correctly using lexicographical sort order.
    """
    parsed = parse_version(version)
    if isinstance(parsed, LegacyVersion):
        return version
    release = ".".join(f"{n:04}" for n in parsed.release)
    extra = []
    if parsed.pre is not None:
        extra.append("".join(str(x) for x in parsed.pre))
    if parsed.post is not None:
        extra.append(f".post{parsed.post}")
    if parsed.dev is not None:
        extra.append(f".dev{parsed.dev}")
    if parsed.local is not None:
        extra.append(f"+{parsed.local}")
    return f"{parsed.epoch:02}!{release}{''.join(extra)}"


@REGISTRY.mapped
@dataclass
class RAMP(IdMixin, NameDescriptionMixin, ExistsMixin):
    __tablename__ = "RAMP"

    __sa_dataclass_metadata_key__ = "sa"

    __table_args__ = (
        UniqueConstraint("plugin_id", "version", name=f"uix_{__tablename__}"),
    )

    _seed_id: Optional[int] = field(
        default=None,
        init=False,
        hash=False,
        repr=False,
        compare=False,
        metadata={"sa": Column(sql.Integer, ForeignKey(Seed.id))},
    )
    seed: Optional[Seed] = field(
        default=None,
        hash=False,
        repr=False,
        compare=False,
        metadata={"sa": relationship(Seed, lazy="select")},
    )

    plugin_id: str = field(default="", metadata={"sa": Column(sql.String(255))})
    version: str = field(default="v0", metadata={"sa": Column(sql.String(100))})
    sort_version: str = field(
        default="0", init=False, metadata={"sa": Column(sql.String(120))}
    )
    plugin_type: str = field(
        default="processing", metadata={"sa": Column(sql.String(100))}
    )
    url: str = field(default="", metadata={"sa": Column(sql.String(2048))})
    entry_url: str = field(default="", metadata={"sa": Column(sql.Text())})
    ui_url: str = field(default="", metadata={"sa": Column(sql.Text())})
    schema: Dict[str, Any] = field(
        default_factory=lambda: {"type": "object"}, metadata={"sa": Column(sql.JSON())}
    )
    last_available: datetime = field(
        default_factory=partial(datetime.now, timezone.utc),
        init=False,
        hash=False,
        repr=False,
        compare=False,
        metadata={"sa": Column(sql.TIMESTAMP(timezone=True))},
    )
    _tags: List["TagToRAMP"] = field(
        init=False,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(
                lambda: TagToRAMP,
                lazy="selectin",
                cascade="all, delete, delete-orphan",
                passive_deletes=True,
                back_populates="ramp",
            )
        },
    )

    tags: List["PluginTag"] = field(
        default_factory=list,
        metadata={
            "sa": association_proxy(
                "_tags", "tag", creator=lambda tag: TagToRAMP(tag=tag)
            )
        },
    )

    data: List["DataToRAMP"] = field(
        default_factory=list,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(
                lambda: DataToRAMP,
                lazy="select",
                cascade="all, delete, delete-orphan",
                passive_deletes=True,
                back_populates="ramp",
            )
        },
    )
    data_consumed: List["DataToRAMP"] = field(
        default_factory=list,
        init=False,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(
                lambda: DataToRAMP,
                lazy="select",
                viewonly=True,
                primaryjoin=lambda: (
                    (RAMP.id == DataToRAMP.ramp_id)
                    & (DataToRAMP.relation == DATA_RELATION_CONSUMED)
                ),
            )
        },
    )
    data_produced: List["DataToRAMP"] = field(
        default_factory=list,
        init=False,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(
                lambda: DataToRAMP,
                lazy="select",
                viewonly=True,
                primaryjoin=lambda: (
                    (RAMP.id == DataToRAMP.ramp_id)
                    & (DataToRAMP.relation == DATA_RELATION_PRODUCED)
                ),
            )
        },
    )

    dependencies: List["DependencyToRAMP"] = field(
        default_factory=list,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(
                lambda: DependencyToRAMP,
                primaryjoin=lambda: (RAMP.id == DependencyToRAMP.ramp_id),
                lazy="select",
                cascade="all, delete, delete-orphan",
                passive_deletes=True,
                back_populates="ramp",
            )
        },
    )

    def __post_init__(self):
        sort_version = get_version_sorting_string(self.version)
        if self.sort_version != sort_version:
            self.sort_version = sort_version


@REGISTRY.mapped
@dataclass
class PluginTag(IdMixin, ExistsMixin):
    __tablename__ = "PluginTag"

    __sa_dataclass_metadata_key__ = "sa"

    tag: str = field(default="", metadata={"sa": Column(sql.String(100), unique=True)})
    description: str = field(default="", metadata={"sa": Column(sql.Text())})

    @classmethod
    def get_by_name(cls, tag: str) -> "Optional[PluginTag]":
        q = select(cls).filter(cls.tag == tag)
        found_tag: Optional[PluginTag] = DB.session.execute(q).scalar_one_or_none()
        return found_tag

    @classmethod
    def get_or_create(cls, tag: str, description: str = "") -> "PluginTag":
        found_tag: Optional[PluginTag] = cls.get_by_name(tag)
        if found_tag is None:
            found_tag = cls(tag=tag, description=description)
            DB.session.add(found_tag)
        return found_tag

    @classmethod
    def get_or_create_all(
        cls, tags: Sequence[Union[str, Tuple[str, str]]]
    ) -> "List[PluginTag]":
        if not tags:
            return []
        return [
            (
                cls.get_or_create(tag=tag)
                if isinstance(tag, str)
                else cls.get_or_create(*tag)
            )
            for tag in set(tags)
        ]

    @classmethod
    def get_all(cls, tags: Sequence[str]) -> "List[PluginTag]":
        if not tags:
            return []
        q = select(cls).filter(cls.tag.in_(tags))
        return DB.session.execute(q).scalars().all()

    def __str__(self) -> str:
        return self.tag


@REGISTRY.mapped
@dataclass
class TagToRAMP:
    __tablename__ = "TagToRAMP"

    __sa_dataclass_metadata_key__ = "sa"

    ramp_id: int = field(
        init=False,
        metadata={
            "sa": Column(
                sql.Integer, ForeignKey(RAMP.id, ondelete="CASCADE"), primary_key=True
            )
        },
    )
    tag_id: int = field(
        init=False,
        metadata={"sa": Column(sql.Integer, ForeignKey(PluginTag.id), primary_key=True)},
    )

    ramp: Optional[RAMP] = field(
        default=None,
        repr=False,
        hash=False,
        compare=False,
        metadata={
            "sa": relationship(
                RAMP,
                innerjoin=True,
                lazy="select",
            )
        },
    )
    tag: Optional[PluginTag] = field(
        default=None,
        hash=False,
        compare=False,
        metadata={"sa": relationship(PluginTag, innerjoin=True, lazy="joined")},
    )


@REGISTRY.mapped
@dataclass
class DataToRAMP(IdMixin):
    __tablename__ = "DataToRamp"

    __sa_dataclass_metadata_key__ = "sa"

    ramp_id: int = field(
        init=False,
        metadata={
            "sa": Column(
                sql.Integer, ForeignKey(RAMP.id, ondelete="CASCADE"), nullable=False
            )
        },
    )
    identifier: str = field(default="", metadata={"sa": Column(sql.String(255))})
    required: bool = field(default=False, metadata={"sa": Column(sql.Boolean())})
    relation: str = field(
        default="", metadata={"sa": Column(sql.String(100))}
    )  # "produced"/"consumed"
    data_type_start: str = field(default="*", metadata={"sa": Column(sql.String(255))})
    data_type_end: str = field(default="*", metadata={"sa": Column(sql.String(255))})

    ramp: RAMP = field(
        init=False,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(RAMP, innerjoin=True, lazy="select", back_populates="data")
        },
    )
    content_types: List["ContentTypeToData"] = field(
        default_factory=list,
        metadata={
            "sa": relationship(
                lambda: ContentTypeToData,
                lazy="selectin",
                cascade="all, delete, delete-orphan",
                passive_deletes=True,
                back_populates="data",
            )
        },
    )

    @property
    def data_type(self) -> str:
        return f"{self.data_type_start}/{self.data_type_end}"


@REGISTRY.mapped
@dataclass
class ContentTypeToData(IdMixin):
    __tablename__ = "ContentTypeToData"

    __sa_dataclass_metadata_key__ = "sa"

    data_id: int = field(
        init=False,
        metadata={
            "sa": Column(
                sql.Integer, ForeignKey(DataToRAMP.id, ondelete="CASCADE"), nullable=False
            )
        },
    )
    content_type_start: str = field(default="*", metadata={"sa": Column(sql.String(255))})
    content_type_end: str = field(default="*", metadata={"sa": Column(sql.String(255))})

    data: DataToRAMP = field(
        init=False,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(
                DataToRAMP, innerjoin=True, lazy="select", back_populates="content_types"
            )
        },
    )

    @property
    def content_type(self) -> str:
        return f"{self.content_type_start}/{self.content_type_end}"


@REGISTRY.mapped
@dataclass
class DependencyToRAMP(IdMixin):
    __tablename__ = "DependencyToRAMP"

    __sa_dataclass_metadata_key__ = "sa"

    ramp_id: int = field(
        init=False,
        metadata={
            "sa": Column(
                sql.Integer, ForeignKey(RAMP.id, ondelete="CASCADE"), nullable=False
            )
        },
    )
    required: bool = field(default=True, metadata={"sa": Column(sql.Boolean())})
    parameter: str = field(default="", metadata={"sa": Column(sql.String(255))})

    plugin_id: Optional[str] = field(
        default=None, metadata={"sa": Column(sql.String(255), nullable=True)}
    )
    version: Optional[str] = field(
        default=None, metadata={"sa": Column(sql.String(512), nullable=True)}
    )
    plugin_type: Optional[str] = field(
        default=None, metadata={"sa": Column(sql.String(100))}
    )

    best_match_id: Optional[int] = field(
        init=False,
        metadata={
            "sa": Column(
                sql.Integer, ForeignKey(RAMP.id, ondelete="SET NULL"), nullable=True
            )
        },
    )

    ramp: RAMP = field(
        init=False,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(
                RAMP,
                primaryjoin=lambda: (RAMP.id == DependencyToRAMP.ramp_id),
                innerjoin=True,
                lazy="select",
                back_populates="dependencies",
            )
        },
    )

    best_match: Optional[RAMP] = field(
        init=False,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(
                RAMP,
                primaryjoin=lambda: (RAMP.id == DependencyToRAMP.best_match_id),
                innerjoin=True,
                lazy="select",
            )
        },
    )

    dependency_tags: List["TagToDependency"] = field(
        default_factory=list,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(
                lambda: TagToDependency,
                lazy="selectin",
                cascade="all, delete, delete-orphan",
                passive_deletes=True,
                back_populates="dependency",
            )
        },
    )

    @property
    def tags(self) -> Sequence[str]:
        return [
            (str(tag.tag) if not tag.exclude else f"!{tag.tag}")
            for tag in self.dependency_tags
        ]

    @property
    def is_fulfilled(self) -> bool:
        return self.best_match_id is not None

    def match_plugin(self, ramp: RAMP) -> bool:
        if self.plugin_id:
            if ramp.plugin_id != self.plugin_id:
                return False
            if self.version and ramp.version != self.version:
                # TODO proper version range matching
                return False
        if self.plugin_type and ramp.plugin_type != self.plugin_type:
            return False
        plugin_tags = {t.tag for t in ramp.tags}
        must_have_tags = {
            t.tag.tag for t in self.dependency_tags if t.tag and not t.exclude
        }
        forbidden_tags = {t.tag.tag for t in self.dependency_tags if t.tag and t.exclude}
        if must_have_tags & forbidden_tags:
            warnings.warn(
                "Plugin dependencies must not specify impossible tag requirements! "
                f"The must_have_tags and the forbidden_tags set have an overlap {must_have_tags & forbidden_tags}"
            )
        return plugin_tags >= must_have_tags and not (plugin_tags & forbidden_tags)


@REGISTRY.mapped
@dataclass
class TagToDependency:
    __tablename__ = "TagToDependency"

    __sa_dataclass_metadata_key__ = "sa"

    dependency_id: int = field(
        init=False,
        metadata={
            "sa": Column(
                sql.Integer,
                ForeignKey(DependencyToRAMP.id, ondelete="CASCADE"),
                primary_key=True,
            )
        },
    )
    tag_id: int = field(
        init=False,
        metadata={"sa": Column(sql.Integer, ForeignKey(PluginTag.id), primary_key=True)},
    )
    exclude: bool = field(default=False, metadata={"sa": Column(sql.Boolean())})

    dependency: Optional[DependencyToRAMP] = field(
        default=None,
        repr=False,
        hash=False,
        compare=False,
        metadata={
            "sa": relationship(
                DependencyToRAMP,
                innerjoin=True,
                lazy="select",
                back_populates="dependency_tags",
            )
        },
    )
    tag: Optional[PluginTag] = field(
        default=None,
        hash=False,
        compare=False,
        metadata={"sa": relationship(PluginTag, innerjoin=True, lazy="joined")},
    )
