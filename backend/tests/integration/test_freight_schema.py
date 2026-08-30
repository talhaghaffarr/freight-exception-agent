import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.factories import (
    NOW,
    insert_load,
    insert_stop,
    insert_tracking_point,
    insert_two_tenants,
)

pytestmark = pytest.mark.integration


def test_load_reference_is_unique_only_inside_a_tenant(migrated_connection):
    atlas, meridian = insert_two_tenants(migrated_connection)
    insert_load(migrated_connection, atlas, "LD-1048")
    # The same human reference in a different brokerage is a different load.
    insert_load(migrated_connection, meridian, "LD-1048")
    with pytest.raises(IntegrityError):
        insert_load(migrated_connection, atlas, "LD-1048")


def test_stop_sequence_is_unique_within_a_load(migrated_connection):
    atlas, _ = insert_two_tenants(migrated_connection)
    load = insert_load(migrated_connection, atlas)
    insert_stop(migrated_connection, atlas, load, sequence=1)
    with pytest.raises(IntegrityError):
        insert_stop(migrated_connection, atlas, load, sequence=1)


def test_stop_type_is_constrained(migrated_connection):
    atlas, _ = insert_two_tenants(migrated_connection)
    load = insert_load(migrated_connection, atlas)
    with pytest.raises(IntegrityError):
        insert_stop(migrated_connection, atlas, load, stop_type="teleport")


def test_tracking_source_event_is_unique_for_deduplication(migrated_connection):
    atlas, _ = insert_two_tenants(migrated_connection)
    load = insert_load(migrated_connection, atlas)
    insert_tracking_point(migrated_connection, atlas, load, source_event_id="eld-42")
    with pytest.raises(IntegrityError):
        insert_tracking_point(migrated_connection, atlas, load, source_event_id="eld-42")


def test_a_stop_cannot_reference_a_load_in_another_tenant(migrated_connection):
    atlas, meridian = insert_two_tenants(migrated_connection)
    atlas_load = insert_load(migrated_connection, atlas)
    # Meridian tenant_id against an Atlas load must be refused by the composite FK.
    with pytest.raises(IntegrityError):
        insert_stop(migrated_connection, meridian, atlas_load)


def test_deleting_a_load_cascades_to_its_stops_and_tracking(migrated_engine):
    with migrated_engine.begin() as connection:
        atlas, _ = insert_two_tenants(connection)
        load = insert_load(connection, atlas)
        insert_stop(connection, atlas, load)
        insert_tracking_point(connection, atlas, load)
    with migrated_engine.begin() as connection:
        connection.execute(text("delete from loads where id = :id"), {"id": load})
    with migrated_engine.connect() as connection:
        stops = connection.execute(
            text("select count(*) from stops where load_id = :id"), {"id": load}
        ).scalar_one()
        points = connection.execute(
            text("select count(*) from tracking_points where load_id = :id"), {"id": load}
        ).scalar_one()
    assert stops == 0
    assert points == 0


def test_latest_tracking_index_supports_a_bounded_lookup(migrated_connection):
    atlas, _ = insert_two_tenants(migrated_connection)
    load = insert_load(migrated_connection, atlas)
    for minutes, event in ((10, "a"), (3, "b"), (7, "c")):
        insert_tracking_point(
            migrated_connection,
            atlas,
            load,
            recorded_at=NOW.replace(minute=0) + __import__("datetime").timedelta(minutes=minutes),
            source_event_id=event,
        )
    latest = migrated_connection.execute(
        text(
            "select source_event_id from tracking_points where tenant_id = :t and load_id = :l "
            "order by recorded_at desc limit 1"
        ),
        {"t": atlas, "l": load},
    ).scalar_one()
    assert latest == "a"
