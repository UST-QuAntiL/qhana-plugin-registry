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
from typing import Any, Optional, Sequence

from sqlalchemy.sql import select
from sqlalchemy.sql.elements import literal

from ..db import DB


class ExistsMixin:
    @classmethod
    def exists(cls, query_filter: Sequence[Any] = tuple()) -> bool:
        exists_q = select(literal(True)).select_from(cls).filter(*query_filter).exists()
        return DB.session.execute(select(literal(True)).where(exists_q)).scalar()


@dataclass
class IdMixin:
    """Add an 'id' column that is the primary key for this table."""

    __sa_dataclass_metadata_key__ = "sa"

    id: Optional[int] = field(
        default=None,
        init=False,
        metadata={"sa": DB.Column(DB.Integer, primary_key=True, autoincrement=True)},
    )

    def save(self, commit: bool = False):
        """Add this object to the current session and optionally commit the session to persist all objects in the session."""
        DB.session.add(self)
        if commit:
            DB.session.commit()

    @classmethod
    def get_by_id(cls, id_: int) -> Optional["IdMixin"]:
        """Get the object instance by the object id from the database. (None if not found)"""
        return DB.session.execute(select(cls).filter_by(id=id_)).scalar_one_or_none()


@dataclass
class NameDescriptionMixin:
    """Add a 'name' and 'description' column to the table."""

    __sa_dataclass_metadata_key__ = "sa"

    name: str = field(
        default="",
        metadata={
            "sa": DB.Column(
                DB.Unicode,
                nullable=False,
                index=True,
                info={
                    "collate": {
                        "postgresql": "POSIX",
                        "mysql": "utf8mb4_bin",
                        "sqlite": "NOCASE",
                        "mssql": "Latin1_General_CI_AS",
                    }
                },
            )
        },
    )
    description: str = field(
        default="", metadata={"sa": DB.Column(DB.UnicodeText, nullable=True, index=True)}
    )
