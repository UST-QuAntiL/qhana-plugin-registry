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
from typing import Optional

from sqlalchemy.sql import select
from sqlalchemy.sql import sqltypes as sql
from sqlalchemy.sql.schema import Column

from .model_helpers import ExistsMixin, IdMixin, NameDescriptionMixin
from ..db import DB, REGISTRY


@REGISTRY.mapped
@dataclass
class Service(IdMixin, NameDescriptionMixin, ExistsMixin):
    """DB model of a (micro) service description."""

    __tablename__ = "Service"

    __sa_dataclass_metadata_key__ = "sa"
    service_id: str = field(
        default="", metadata={"sa": Column(sql.String(255), nullable=False, unique=True)}
    )
    url: str = field(default="", metadata={"sa": Column(sql.Text())})

    @classmethod
    def get_by_service_id(cls, id_: str) -> Optional["Service"]:
        """Get the service instance by its service_id from the database. (None if not found)"""
        return DB.session.execute(
            select(cls).filter_by(service_id=id_)
        ).scalar_one_or_none()
