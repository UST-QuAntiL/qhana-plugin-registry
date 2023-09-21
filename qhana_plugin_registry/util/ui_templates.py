import json
from pathlib import Path
from typing import Optional, Union
from flask import Flask
from json import load

from qhana_plugin_registry.tasks.plugin_filter import evaluate_plugin_filter

from ..db.db import DB
from ..db.models.templates import TemplateTab, TemplateTag, UiTemplate


def _load_template_from_file(app: Flask, file: Union[str, Path]) -> None:
    """Load a template from a file.

    Args:
        app (Flask): the app instance
        file (Union[str, Path]): the file path
    """
    if isinstance(file, str):
        file = Path(file)

    file = file.resolve()

    if not file.exists():
        app.logger.info(
            f"Tried to load template from file '{file}' but it does not exist."
        )
        return

    try:
        with file.open("r") as f:
            template_json = load(f)
            app.logger.info(f"Loaded template from file '{file}'.")
    except Exception:
        app.logger.warning(
            f"Tried to load template from file '{file}' but an error occurred.",
            exc_info=True,
        )
        return

    template: Optional[UiTemplate] = UiTemplate.get_by_name(template_json["name"])
    if template is None:
        template = UiTemplate(
            name=template_json["name"],
            description=template_json["description"],
            tags=TemplateTag.get_or_create_all(template_json["tags"]),
            tabs=[],  # will be added later
        )
        DB.session.add(template)
        for tab in template_json["tabs"]:
            tab["filter_string"] = json.dumps(tab.pop("filter"))
            new_tab = TemplateTab.get_or_create(template=template, **tab)
            template.tabs.append(new_tab)
        DB.session.commit()
    app.logger.info(f"Loaded template '{template.name}' from file '{file}'.")


def _load_templates_from_folder(app: Flask, folder: Union[str, Path]) -> None:
    """Load templates from a folder.

    Args:
        app (Flask): the app instance
        folder (Union[str, Path]): the folder path
    """
    if isinstance(folder, str):
        folder = Path(folder)

    folder = folder.resolve()

    if not folder.exists():
        app.logger.info(
            f"Tried to load templates from folder '{folder}' but it does not exist."
        )
        return

    files = folder.glob("*.json")
    for file in files:
        _load_template_from_file(app, file)


def load_ui_templates(app: Flask) -> None:
    """Load templates from the plugin folders.

    Args:
        app (Flask): the app instance
    """

    template_folders = app.config.get("UI_TEMPLATE_PATHS", [])

    for folder in template_folders:
        path = Path(folder)
        if path.is_dir():
            _load_templates_from_folder(app, path)
        elif path.is_file():
            _load_template_from_file(app, path)
        else:
            app.logger.warning(
                f"Tried to load templates from '{path}' but it is neither a file nor a folder."
            )
