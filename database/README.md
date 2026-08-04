# Database Package

This package provides a lightweight SQLite data access layer for `financial_analyst_copilot.db`.

## Structure

- `connection.py` — database connection manager with transactions and foreign key enforcement
- `crud.py` — generic `BaseDAO` plus table-specific DAO classes
- `models.py` — typed dataclasses for each table

## Quick start

```python
from database import DatabaseConnection, DimAccountDAO
from database.models import DimAccount

db = DatabaseConnection("financial_analyst_copilot.db")
account_dao = DimAccountDAO(db)
new_account = DimAccount(
    account_code="4000",
    account_name="Revenue",
    account_type="Revenue",
    financial_statement_section="Income Statement",
    normal_balance="Credit",
)
account_id = account_dao.create_from_model(new_account)
print("Created account id", account_id)
```

## Run the example script

From the repository root:

```bash
python -m scripts.example_usage
```

## Notes

- DAO methods support both plain dictionaries and dataclass instances
- All database interactions use `PRAGMA foreign_keys = ON`
- `DatabaseConnection.session()` commits on success and rolls back on error
