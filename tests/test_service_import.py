import asyncio
import importlib

from database.connection import DatabaseConnection
from database.crud import BaseDAO


def test_import_rag_ingestor_without_api_dependencies():
    services = importlib.import_module("services")
    assert services is not None

    rag_module = importlib.import_module("services.rag.injest")
    assert getattr(rag_module, "Injestor", None) is not None


def test_database_session_supports_async_context_manager():
    db = DatabaseConnection(":memory:")

    async def run():
        async with db.session() as connection:
            row = connection.execute("SELECT 1").fetchone()
            assert row[0] == 1

    asyncio.run(run())


def test_database_session_supports_sync_context_manager():
    db = DatabaseConnection(":memory:")
    with db.session() as connection:
        row = connection.execute("SELECT 1").fetchone()
        assert row[0] == 1


def test_base_dao_async_list_all_uses_sync_sqlite_api():
    db = DatabaseConnection(":memory:")
    with db.session() as connection:
        connection.execute("CREATE TABLE test_items (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute("INSERT INTO test_items (name) VALUES (?)", ("alpha",))
        connection.execute("INSERT INTO test_items (name) VALUES (?)", ("beta",))

    dao = BaseDAO(db, "test_items", "id", ["id", "name"])

    async def run():
        rows = await dao.list_all()
        assert [row["name"] for row in rows] == ["alpha", "beta"]

    asyncio.run(run())
