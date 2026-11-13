import pytest

import run_mysql_acceptance_demo as acceptance


class FakeCursor:
    def __init__(self, database_name):
        self.database_name = database_name

    def execute(self, query):
        assert query == "SELECT DATABASE()"

    def fetchone(self):
        return (self.database_name,)

    def close(self):
        pass


class FakeConnection:
    def __init__(self, database_name):
        self.cursor_instance = FakeCursor(database_name)

    def cursor(self):
        return self.cursor_instance

    def is_connected(self):
        return True

    def close(self):
        pass


def test_acceptance_demo_allows_only_disposable_test_database(monkeypatch):
    monkeypatch.setattr(
        acceptance,
        "get_connection",
        lambda: FakeConnection("pharmacy_inventory_test"),
    )

    assert acceptance.check_database_name() == "pharmacy_inventory_test"


def test_acceptance_demo_refuses_normal_project_database(monkeypatch):
    monkeypatch.setattr(
        acceptance,
        "get_connection",
        lambda: FakeConnection("pharmacy_inventory"),
    )

    with pytest.raises(RuntimeError, match="only runs against"):
        acceptance.check_database_name()
