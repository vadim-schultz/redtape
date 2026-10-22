"""App-level dependency map for the shared paging and locale providers."""

from __future__ import annotations

from litestar.di import Provide

from app.shared.locale import provide_resolved_locale
from app.shared.paging import provide_page_params

shared_dependencies = {
    "page": Provide(provide_page_params, sync_to_thread=False),
    "locale": Provide(provide_resolved_locale, sync_to_thread=False),
}
