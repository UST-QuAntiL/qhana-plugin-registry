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
from typing import Optional, Sequence

from sqlalchemy.sql import delete, select
from sqlalchemy.sql import sqltypes as sql
from sqlalchemy.sql.schema import Column

from .model_helpers import ExistsMixin
from ..db import DB, REGISTRY


@REGISTRY.mapped
@dataclass
class Env(ExistsMixin):
    """DB model mimicking environment variables."""

    __tablename__ = "Environ"

    __sa_dataclass_metadata_key__ = "sa"
    name: str = field(
        default="", metadata={"sa": Column(sql.String(255), primary_key=True)}
    )
    value: str = field(default="", metadata={"sa": Column(sql.Text())})

    @classmethod
    def get_names(cls) -> Sequence[str]:
        """Get a list of known env var names."""
        return DB.session.execute(select(cls.name)).scalars()

    @classmethod
    def get_items(cls) -> Sequence["Env"]:
        """Get a list of known env vars."""
        return DB.session.execute(select(cls)).scalars()

    @classmethod
    def get(cls, name: str, default=None) -> Optional["Env"]:
        """Get an env var. (Returns `default` if env var is unset.)"""
        q = select(cls).filter(cls.name == name).limit(1)
        result = DB.session.execute(q).scalar_one_or_none()
        if result is None:
            return default
        return result

    @classmethod
    def get_value(cls, name: str, default=None) -> Optional[str]:
        """Get an env var value. (Returns `default` if env var is unset.)"""
        q = select(cls.value).filter(cls.name == name).limit(1)
        result = DB.session.execute(q).scalar_one_or_none()
        if result is None:
            return default
        return result

    @classmethod
    def set(cls, name: str, value: str) -> "Env":
        """Set an env var value. (Does not commit the session!)"""
        assert value is not None, "Use remove to unset values!"
        q = select(cls).filter(cls.name == name).limit(1)
        env_var: Optional[Env] = DB.session.execute(q).scalar_one_or_none()
        if env_var is None:
            env_var = Env(name, value)
        else:
            env_var.value = value
        DB.session.add(env_var)
        return env_var

    @classmethod
    def remove(cls, name: str):
        """Remove an env var value. (Does not commit the session!)"""
        DB.session.execute(delete(cls).where(cls.name == name))
