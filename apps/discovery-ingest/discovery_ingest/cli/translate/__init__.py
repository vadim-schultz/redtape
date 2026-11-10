"""The ``translate`` command group: ``probe`` costs an engine, ``drain`` translates the queue, ``summary`` counts it."""

from discovery_ingest.cli.translate import commands, queue
from discovery_ingest.cli.translate.app import translate_app

__all__ = ["commands", "queue", "translate_app"]
