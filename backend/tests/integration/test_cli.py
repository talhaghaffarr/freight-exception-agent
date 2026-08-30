import pytest

from relayops.cli import main

pytestmark = pytest.mark.integration


def test_migrate_check_reports_pending_then_current(postgres_engine, database_url, capsys):
    env = {"DATABASE_URL": database_url}

    assert main(["migrate", "--check"], environ=env) == 1
    assert "pending" in capsys.readouterr().out

    assert main(["migrate"], environ=env) == 0
    assert "001_foundation" in capsys.readouterr().out

    assert main(["migrate", "--check"], environ=env) == 0
    assert "up to date" in capsys.readouterr().out


def test_unknown_command_is_rejected(database_url):
    with pytest.raises(SystemExit):
        main(["not-a-command"], environ={"DATABASE_URL": database_url})
