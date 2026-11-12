"""Bounds of the snapshot pipeline: the cleaner cap, the skip threshold and the block limits the API enforces."""

from __future__ import annotations

from typing import Final

DOCUMENT_MAX_CHARS: Final = 30_000
"""The cap on the cleaned text of a page, passed to the cleaner explicitly.

The card cap cannot change documents this way.
"""

MIN_TEXT_CHARS: Final = 200
"""Cleaned text under this many characters is an empty shell or an error page, and the page is skipped as too short."""

MAX_BLOCK_CHARS: Final = 4000
"""Most characters in one block, the cells of a row counted together. The API refuses a longer block."""

MAX_BLOCKS: Final = 2000
"""Most blocks in one page. The API refuses a longer page, so a page keeps its first blocks and is marked truncated."""
