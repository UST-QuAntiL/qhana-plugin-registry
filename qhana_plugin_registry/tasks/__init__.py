from flask import Flask

from ..celery import CELERY

from .tasks import start_plugin_discovery


def register_periodic_tasks(app: Flask):
    plugin_discovery_intervall = 20  # FIXME make period configurable

    @CELERY.on_after_finalize.connect
    def setup_periodic_tasks(sender, **kwargs):
        sender.add_periodic_task(
            plugin_discovery_intervall,
            start_plugin_discovery.s(),
            name="Plugin discovery",
        )
