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
from typing import List, Optional, Tuple, Union

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship
from sqlalchemy.sql import sqltypes as sql, select
from sqlalchemy.sql.schema import Column, ForeignKey

from .model_helpers import ExistsMixin, IdMixin, NameDescriptionMixin
from .plugins import RAMP
from ..db import DB, REGISTRY


@REGISTRY.mapped
@dataclass
class WorkspaceTemplate(IdMixin, NameDescriptionMixin, ExistsMixin):
    """DB model of a plugin workspace template."""

    __tablename__ = "WorkspaceTemplate"

    __sa_dataclass_metadata_key__ = "sa"

    _tags: List["TagToTemplate"] = field(
        default_factory=list,
        init=False,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(
                lambda: TagToTemplate,
                lazy="selectin",
                cascade="all, delete, delete-orphan",
                passive_deletes=True,
                back_populates="template",
            )
        },
    )

    tabs: List["TemplateTab"] = field(
        default_factory=list,
        metadata={
            "sa": relationship(
                lambda: TemplateTab,
                lazy="selectin",
                cascade="all, delete, delete-orphan",
                passive_deletes=True,
                back_populates="template",
            )
        },
    )

    tags: List["TemplateTag"] = field(
        default_factory=list,
        metadata={
            "sa": association_proxy(
                "_tags", "tag", creator=lambda tag: TagToTemplate(tag=tag)
            )
        },
    )


@REGISTRY.mapped
@dataclass
class TemplateTag(IdMixin, ExistsMixin):
    __tablename__ = "TemplateTag"

    __sa_dataclass_metadata_key__ = "sa"

    tag: str = field(default="", metadata={"sa": Column(sql.String(100), unique=True)})
    description: str = field(default="", metadata={"sa": Column(sql.Text())})

    @classmethod
    def get_by_name(cls, tag: str) -> "Optional[TemplateTag]":
        q = select(cls).filter(cls.tag == tag)
        found_tag: Optional[TemplateTag] = DB.session.execute(q).scalar_one_or_none()
        return found_tag

    @classmethod
    def get_or_create(cls, tag: str, description: str = "") -> "TemplateTag":
        found_tag: Optional[TemplateTag] = cls.get_by_name(tag)
        if found_tag is None:
            found_tag = cls(tag=tag, description=description)
            DB.session.add(found_tag)
        return found_tag

    @classmethod
    def get_or_create_all(
        cls, tags: List[Union[str, Tuple[str, str]]]
    ) -> "List[TemplateTag]":
        return [
            (
                cls.get_or_create(tag=tag)
                if isinstance(tag, str)
                else cls.get_or_create(*tag)
            )
            for tag in tags
        ]


@REGISTRY.mapped
@dataclass
class TagToTemplate:
    __tablename__ = "TagToTemplate"

    __sa_dataclass_metadata_key__ = "sa"

    template_id: int = field(
        init=False,
        metadata={
            "sa": Column(
                sql.Integer,
                ForeignKey(WorkspaceTemplate.id, ondelete="CASCADE"),
                primary_key=True,
            )
        },
    )
    tag_id: int = field(
        init=False,
        metadata={
            "sa": Column(sql.Integer, ForeignKey(TemplateTag.id), primary_key=True)
        },
    )

    template: Optional[WorkspaceTemplate] = field(
        default=None,
        repr=False,
        hash=False,
        compare=False,
        metadata={
            "sa": relationship(
                WorkspaceTemplate, innerjoin=True, lazy="select", back_populates="_tags"
            )
        },
    )
    tag: Optional[TemplateTag] = field(
        default=None,
        hash=False,
        compare=False,
        metadata={"sa": relationship(TemplateTag, innerjoin=True, lazy="joined")},
    )


@REGISTRY.mapped
@dataclass
class TemplateTab(IdMixin, ExistsMixin, NameDescriptionMixin):
    __tablename__ = "TemplateTab"

    __sa_dataclass_metadata_key__ = "sa"

    template_id: int = field(
        init=False,
        metadata={
            "sa": Column(
                sql.Integer,
                ForeignKey(WorkspaceTemplate.id, ondelete="CASCADE"),
                nullable=False,
            )
        },
    )
    sort_key: int = field(default=0, metadata={"sa": Column(sql.Integer())})
    plugin_filter: str = field(
        default="", metadata={"sa": Column(sql.Text())}
    )  # FIXME default

    _plugins: List["RampToTemplateTab"] = field(
        init=False,
        hash=False,
        repr=False,
        compare=False,
        metadata={
            "sa": relationship(
                lambda: RampToTemplateTab,
                lazy="select",  # TODO figure out a good loading strategy!
                cascade="all, delete, delete-orphan",
                passive_deletes=True,
                back_populates="tab",
            )
        },
    )

    template: Optional[WorkspaceTemplate] = field(
        default=None,
        repr=False,
        hash=False,
        compare=False,
        metadata={
            "sa": relationship(
                WorkspaceTemplate, innerjoin=True, lazy="select", back_populates="tabs"
            )
        },
    )

    plugins: List[RAMP] = field(
        default_factory=list,
        metadata={
            "sa": association_proxy(
                "_plugins", "ramp", creator=lambda ramp: RampToTemplateTab(ramp=ramp)
            )
        },
    )


@REGISTRY.mapped
@dataclass
class RampToTemplateTab:
    __tablename__ = "RampToTemplateTab"

    __sa_dataclass_metadata_key__ = "sa"

    tab_id: int = field(
        init=False,
        metadata={
            "sa": Column(
                sql.Integer,
                ForeignKey(TemplateTab.id, ondelete="CASCADE"),
                primary_key=True,
            )
        },
    )
    ramp_id: int = field(
        init=False,
        metadata={
            "sa": Column(
                sql.Integer,
                ForeignKey(RAMP.id, ondelete="CASCADE"),
                primary_key=True,
            )
        },
    )

    tab: Optional[TemplateTab] = field(
        default=None,
        repr=False,
        hash=False,
        compare=False,
        metadata={
            "sa": relationship(
                TemplateTab, innerjoin=True, lazy="select", back_populates="_plugins"
            )
        },
    )
    ramp: Optional[RAMP] = field(
        default=None,
        hash=False,
        compare=False,
        metadata={"sa": relationship(RAMP, innerjoin=True, lazy="joined")},
    )
