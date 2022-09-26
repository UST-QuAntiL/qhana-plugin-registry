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

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship
from sqlalchemy.sql import sqltypes as sql
from sqlalchemy.sql.schema import Column, ForeignKey

from .model_helpers import ExistsMixin, IdMixin, NameDescriptionMixin
from .plugins import RAMP
from ..db import REGISTRY


@REGISTRY.mapped
@dataclass
class WorkspaceTemplate(IdMixin, NameDescriptionMixin, ExistsMixin):
    """DB model of a plugin workspace template."""

    __tablename__ = "WorkspaceTemplate"

    __sa_dataclass_metadata_key__ = "sa"

    _tags = relationship(
        lambda: TagToTemplate,
        lazy="selectin",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
        back_populates="template",
    )

    tabs = relationship(
        lambda: TemplateTab,
        lazy="selectin",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
        back_populates="template",
    )

    tags = association_proxy("_tags", "tag")


@REGISTRY.mapped
@dataclass
class TemplateTag(IdMixin, ExistsMixin):
    __tablename__ = "TemplateTag"

    __sa_dataclass_metadata_key__ = "sa"

    tag: str = field(default="", metadata={"sa": Column(sql.String(100))})
    description: str = field(default="", metadata={"sa": Column(sql.Text())})


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

    template = relationship(
        WorkspaceTemplate, innerjoin=True, lazy="select", back_populates="_tags"
    )
    tag = relationship(TemplateTag, innerjoin=True, lazy="joined")


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

    _plugins = relationship(
        lambda: RampToTemplateTab,
        lazy="select",  # TODO figure out a good loading strategy!
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
        back_populates="tab",
    )

    template = relationship(
        WorkspaceTemplate, innerjoin=True, lazy="select", back_populates="tabs"
    )

    plugins = association_proxy("_plugins", "ramp")


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

    tab = relationship(
        TemplateTab, innerjoin=True, lazy="select", back_populates="_plugins"
    )
    ramp = relationship(RAMP, innerjoin=True, lazy="joined")
