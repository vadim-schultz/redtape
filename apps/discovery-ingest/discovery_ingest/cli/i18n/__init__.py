"""The ``i18n`` command group: ``translate-ui`` generates the interface strings of a locale."""

from discovery_ingest.cli.i18n import commands
from discovery_ingest.cli.i18n.app import i18n_app

__all__ = ["commands", "i18n_app"]
