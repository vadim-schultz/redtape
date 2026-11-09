"""The served machine vocabulary the crosswalk tests read: the API's fixture, rendered from the contract artifact."""

from __future__ import annotations

import json
from pathlib import Path

from discovery_ingest.json_types import JsonObject
from discovery_ingest.pvog.category_mapping import MachineCrosswalk
from discovery_ingest.pvog.crosswalk_check import parse_crosswalk

VOCABULARY_PATH = Path(__file__).parents[2] / "api" / "tests" / "fixtures" / "machine_vocabulary.json"
VOCABULARY: JsonObject = json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))
CROSSWALK: MachineCrosswalk = parse_crosswalk(VOCABULARY)
