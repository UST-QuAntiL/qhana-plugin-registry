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

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship
from sqlalchemy.sql import sqltypes as sql
from sqlalchemy.sql.schema import Column, ForeignKey, Index, UniqueConstraint

from .model_helpers import (
    FULLTEXT_INDEX_PARAMS,
    ExistsMixin,
    IdMixin,
    NameDescriptionMixin,
)
from .seeds import Seed
from ..db import REGISTRY

DATA_RELATION_CONSUMED = "consumed"
DATA_RELATION_PRODUCED = "produced"


@REGISTRY.mapped
@dataclass
class RAMP(IdMixin, NameDescriptionMixin, ExistsMixin):
    __tablename__ = "RAMP"

    __sa_dataclass_metadata_key__ = "sa"

    __table_args__ = (
        UniqueConstraint("plugin_id", "version", name=f"uix_{__tablename__}"),
        Index(
            f"ix_search_{__tablename__}", "name", "description", **FULLTEXT_INDEX_PARAMS
        ),
    )

    _seed_id: Optional[int] = field(
        default=None, metadata={"sa": Column(sql.Integer, ForeignKey(Seed.id))}
    )
    seed: Optional[Seed] = field(default=None, metadata={"sa": relationship(Seed, lazy="select")})

    plugin_id: str = field(default="", metadata={"sa": Column(sql.String(255))})
    version: str = field(default="v0", metadata={"sa": Column(sql.String(100))})
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
        default_factory=datetime.utcnow,
        metadata={"sa": Column(sql.TIMESTAMP(timezone=True))},
    )
    _tags = relationship(
        lambda: TagToRAMP,
        lazy="selectin",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
        back_populates="ramp",
    )

    tags = association_proxy("_tags", "tag")

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
    data_consumed = relationship(
        lambda: DataToRAMP,
        lazy="select",
        viewonly=True,
        primaryjoin=lambda: (
            (RAMP.id == DataToRAMP.ramp_id)
            & (DataToRAMP.relation == DATA_RELATION_CONSUMED)
        ),
    )
    data_produced = relationship(
        lambda: DataToRAMP,
        lazy="select",
        viewonly=True,
        primaryjoin=lambda: (
            (RAMP.id == DataToRAMP.ramp_id)
            & (DataToRAMP.relation == DATA_RELATION_PRODUCED)
        ),
    )


@REGISTRY.mapped
@dataclass
class PluginTag(IdMixin, ExistsMixin):
    __tablename__ = "PluginTag"

    __sa_dataclass_metadata_key__ = "sa"

    tag: str = field(default="", metadata={"sa": Column(sql.String(100))})
    description: str = field(default="", metadata={"sa": Column(sql.Text())})


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

    ramp = relationship(RAMP, innerjoin=True, lazy="select", back_populates="_tags")
    tag = relationship(PluginTag, innerjoin=True, lazy="joined")


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

    ramp = relationship(RAMP, innerjoin=True, lazy="select", back_populates="data")
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

    data = relationship(
        DataToRAMP, innerjoin=True, lazy="select", back_populates="content_types"
    )

    @property
    def content_type(self) -> str:
        return f"{self.content_type_start}/{self.content_type_end}"
