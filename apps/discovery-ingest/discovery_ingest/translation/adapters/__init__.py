"""Translation engine adapters; importing the package registers every adapter that ships with the repository."""

from discovery_ingest.translation.adapters import claude_code, cloudflare_llm

__all__ = ["claude_code", "cloudflare_llm"]
