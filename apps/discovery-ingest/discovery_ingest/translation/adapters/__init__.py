"""Translation engine adapters; importing the package registers every adapter that ships with the repository."""

from discovery_ingest.translation.adapters import azure_translator, claude_code, cloudflare_llm

__all__ = ["azure_translator", "claude_code", "cloudflare_llm"]
