"""Translation engine adapters; importing the package registers every adapter that ships with the repository."""

from discovery_ingest.translation.adapters import cloudflare_llm

__all__ = ["cloudflare_llm"]
