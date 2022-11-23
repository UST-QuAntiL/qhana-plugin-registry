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

"""CLI functions for the db module."""

from typing import Dict, List, Set, cast

import click
from flask import Blueprint, Flask, current_app
from flask.cli import AppGroup, with_appcontext
from sqlalchemy.sql.expression import Insert, insert

from .db import DB
from .models.env import Env
from .models.seeds import Seed
from .models.services import Service
from ..util.logging import get_logger

# make sure all models are imported for CLI to work properly
from . import models  # noqa


DB_CLI_BLP = Blueprint("db_cli", __name__, cli_group=None)
DB_CLI = cast(AppGroup, DB_CLI_BLP.cli)  # expose as attribute for autodoc generation

DB_COMMAND_LOGGER = "db"


@DB_CLI.command("create-db")
@with_appcontext
def create_db():
    """Create all db tables."""
    create_db_function(current_app)
    click.echo("Database created.")


def create_db_function(app: Flask):
    DB.create_all()
    get_logger(app, DB_COMMAND_LOGGER).info("Database created.")


@DB_CLI.command("drop-db")
@with_appcontext
def drop_db():
    """Drop all db tables."""
    drop_db_function(current_app)
    click.echo("Database dropped.")


def drop_db_function(app: Flask):
    DB.drop_all()
    get_logger(app, DB_COMMAND_LOGGER).info("Dropped Database.")


@DB_CLI.command("preload-db")
@with_appcontext
def preload_db():
    """Prelaod the database with values read from app config."""
    click.echo("Preloading env variables into the database.")
    preload_env(current_app)
    click.echo("Preloading seed URLs into the database.")
    preload_seeds(current_app)
    click.echo("Preloading services into the database.")
    preload_services(current_app)
    click.echo("Values loaded.")


def preload_env(app: Flask):
    logger = get_logger(app, DB_COMMAND_LOGGER)
    env_dict: Dict[str, str] = app.config.get("CURRENT_ENV", {})

    for key, value in env_dict.items():
        Env.set(key, value)
        logger.info(f"Set env variable {key}.")
    DB.session.commit()


def preload_seeds(app: Flask):
    logger = get_logger(app, DB_COMMAND_LOGGER)
    initial_seeds: Set[str] = set(app.config.get("INITIAL_PLUGIN_SEEDS", []))
    if not initial_seeds:
        logger.info("No initial seeds configured.")
        return
    if Seed.exists():
        logger.info("Seeds table is not empty, no seeds will be preloaded.")
        return
    insert_q: Insert = insert(Seed)
    DB.session.execute(insert_q, [{"url": s} for s in initial_seeds])
    DB.session.commit()
    logger.info("Loaded initial seeds into database.")


def preload_services(app: Flask):
    logger = get_logger(app, DB_COMMAND_LOGGER)
    services: List[Dict[str, str]] = app.config.get("PRECONFIGURED_SERVICES", [])

    for service in services:
        service_id = service.get("serviceId", "")
        if not service_id:
            logger.info(f"Encountered service with missing serviceId: {service}")
            continue
        if Service.exists((Service.service_id == service_id,)):
            logger.info(
                f"Service with serviceId {service_id} already exists. No changes made to the service."
            )
            continue
        service_url = service.get("url", "")
        if not service_url:
            logger.info(f"Encountered service with missing url: {service}")
            continue
        new_service = Service(
            name=service.get("name", service_id),
            description=service.get("description", ""),
            service_id=service_id,
            url=service_url,
        )
        DB.session.add(new_service)
    DB.session.commit()


def register_cli_blueprint(app: Flask):
    """Method to register the DB CLI blueprint."""
    app.register_blueprint(DB_CLI_BLP)
    app.logger.info("Registered blueprint.")
