"""The deterministic freight fact engine.

Nothing in this package consults a language model. Location, freshness, ETA and
lateness are arithmetic over recorded evidence, and every value carries the
timestamp it was derived from so the operator can audit it. When the evidence
does not support a value, these functions return an explicit unavailable fact
with a reason -- never a guess, and never a blank that a template might fill.
"""

from relayops.facts.eta import EtaFact, RouteEstimate, compute_eta
from relayops.facts.late_pickup import LatePickupConfig, LatePickupFacts, late_pickup_facts
from relayops.facts.tracking import Freshness, classify_tracking_freshness

__all__ = [
    "EtaFact",
    "Freshness",
    "LatePickupConfig",
    "LatePickupFacts",
    "RouteEstimate",
    "classify_tracking_freshness",
    "compute_eta",
    "late_pickup_facts",
]
