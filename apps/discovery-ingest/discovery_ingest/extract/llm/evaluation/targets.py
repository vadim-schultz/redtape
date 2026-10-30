"""The starting thresholds of decision X14, to be replaced by what the measurements justify."""

from __future__ import annotations

MIN_PRECISION = 0.80
MIN_RECALL = 0.60
MIN_GROUNDED_RATE = 0.95
MIN_TAG_AGREEMENT = 0.60
METRIC_VERSION = "grounded_rate=quote"
"""What the grounded rate means: quote failures over raw items (the kept rate is the old figure, chapter E20)."""
DAILY_NEURON_CAP = 9500
"""The ledger's daily cap (95 percent of the free allowance, chapter E11)."""
