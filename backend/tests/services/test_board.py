"""The operations board is the facts engine applied to real rows.

These tests run against PostgreSQL with the demo freight seed, so they assert
the same numbers an operator reads on the screen.
"""

from __future__ import annotations

import pytest

from relayops.seed_freight import ATLAS, MERIDIAN
from relayops.services.board import load_board

pytestmark = pytest.mark.integration


def test_the_flagship_load_is_late_by_the_seeded_margin(seeded_freight_connection) -> None:
    rows = {row.reference: row for row in load_board(seeded_freight_connection, ATLAS)}

    flagship = rows["LD-1048"]
    assert flagship.facts.classification == "late"
    assert flagship.facts.minutes_late == 38
    assert flagship.facts.eta.available is True


def test_a_load_without_a_recent_position_reports_unknown_not_a_guess(
    seeded_freight_connection,
) -> None:
    rows = {row.reference: row for row in load_board(seeded_freight_connection, ATLAS)}

    dark = rows["LD-1051"]
    assert dark.facts.classification == "unknown"
    assert dark.facts.reason == "tracking_stale"
    assert dark.facts.minutes_late is None


def test_lateness_under_the_threshold_is_at_risk(seeded_freight_connection) -> None:
    rows = {row.reference: row for row in load_board(seeded_freight_connection, ATLAS)}

    assert rows["LD-1090"].facts.classification == "at_risk"


def test_the_board_never_leaks_a_load_from_another_tenant(seeded_freight_connection) -> None:
    atlas = {row.reference: row for row in load_board(seeded_freight_connection, ATLAS)}
    meridian = {row.reference: row for row in load_board(seeded_freight_connection, MERIDIAN)}

    # Both tenants have an LD-1048; they are different loads with different
    # customers, and neither board contains the other's row.
    assert atlas["LD-1048"].customer_name == "ACME Retail"
    assert meridian["LD-1048"].customer_name == "Sonora Distribution"
    assert atlas["LD-1048"].load_id != meridian["LD-1048"].load_id
    assert "LD-1090" not in meridian
