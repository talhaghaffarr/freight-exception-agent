import pytest
from sqlalchemy.exc import IntegrityError

from tests.factories import insert_action, insert_goal, insert_load, insert_stop, insert_two_tenants

pytestmark = pytest.mark.integration


@pytest.fixture
def seeded(migrated_connection):
    atlas, meridian = insert_two_tenants(migrated_connection)
    load = insert_load(migrated_connection, atlas)
    stop = insert_stop(migrated_connection, atlas, load)
    return {"atlas": atlas, "meridian": meridian, "load": load, "stop": stop}


def test_duplicate_goal_key_is_rejected(migrated_connection, seeded):
    insert_goal(
        migrated_connection,
        seeded["atlas"],
        subject_id=seeded["stop"],
        load_id=seeded["load"],
        trigger="pickup:1:appointment:1:late:v1",
    )
    with pytest.raises(IntegrityError):
        insert_goal(
            migrated_connection,
            seeded["atlas"],
            subject_id=seeded["stop"],
            load_id=seeded["load"],
            trigger="pickup:1:appointment:1:late:v1",
        )


def test_the_same_trigger_in_two_tenants_is_two_goals(migrated_connection):
    atlas, meridian = insert_two_tenants(migrated_connection)
    for tenant in (atlas, meridian):
        load = insert_load(migrated_connection, tenant)
        stop = insert_stop(migrated_connection, tenant, load)
        insert_goal(
            migrated_connection,
            tenant,
            subject_id=stop,
            load_id=load,
            trigger="pickup:1:appointment:1:late:v1",
        )
    # No IntegrityError: idempotency is scoped by tenant.


def test_duplicate_action_fingerprint_is_rejected(migrated_connection, seeded):
    goal = insert_goal(
        migrated_connection, seeded["atlas"], subject_id=seeded["stop"], load_id=seeded["load"]
    )
    insert_action(migrated_connection, seeded["atlas"], goal, action_fingerprint="late-v1")
    with pytest.raises(IntegrityError):
        insert_action(migrated_connection, seeded["atlas"], goal, action_fingerprint="late-v1")


def test_a_different_recipient_is_a_different_action(migrated_connection, seeded):
    goal = insert_goal(
        migrated_connection, seeded["atlas"], subject_id=seeded["stop"], load_id=seeded["load"]
    )
    insert_action(
        migrated_connection,
        seeded["atlas"],
        goal,
        recipient="dana@atlas.demo",
        recipient_fingerprint="email:dana@atlas.demo",
        action_fingerprint="late-v1",
    )
    # Escalation to a second recipient for the same alert must be allowed.
    insert_action(
        migrated_connection,
        seeded["atlas"],
        goal,
        recipient="ops@atlas.demo",
        recipient_fingerprint="email:ops@atlas.demo",
        action_fingerprint="late-v1",
    )


def test_goal_state_is_constrained(migrated_connection, seeded):
    with pytest.raises(IntegrityError):
        insert_goal(
            migrated_connection,
            seeded["atlas"],
            subject_id=seeded["stop"],
            load_id=seeded["load"],
            state="vibing",
        )


def test_an_action_cannot_link_a_goal_in_another_tenant(migrated_connection, seeded):
    goal = insert_goal(
        migrated_connection, seeded["atlas"], subject_id=seeded["stop"], load_id=seeded["load"]
    )
    with pytest.raises(IntegrityError):
        insert_action(migrated_connection, seeded["meridian"], goal)
