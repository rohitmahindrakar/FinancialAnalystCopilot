import sys
from pathlib import Path

if __package__ is None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

from database import (
    DatabaseConnection,
    DimAccountDAO,
    DimBusinessUnitDAO,
    DimPeriodDAO,
    FinanceActualsDAO,
    QueryLogDAO,
)
from database.models import (
    DimAccount,
    DimBusinessUnit,
    DimPeriod,
    FinanceActuals,
    QueryLog,
)


def main() -> None:
    db = DatabaseConnection("financial_analyst_copilot.db")

    account_dao = DimAccountDAO(db)
    bu_dao = DimBusinessUnitDAO(db)
    period_dao = DimPeriodDAO(db)
    actuals_dao = FinanceActualsDAO(db)
    query_log_dao = QueryLogDAO(db)

    new_account = DimAccount(
        account_code="4000",
        account_name="Revenue",
        account_type="Revenue",
        financial_statement_section="Income Statement",
        normal_balance="Credit",
    )
    account_id = account_dao.create_from_model(new_account)
    print(f"Created DimAccount {account_id}")

    new_bu = DimBusinessUnit(
        business_unit_name="Corporate",
        region="North America",
        segment="Global",
    )
    business_unit_id = bu_dao.create_from_model(new_bu)
    print(f"Created DimBusinessUnit {business_unit_id}")

    new_period = DimPeriod(
        period_name="FY2026-Q1",
        month=3,
        month_name="March",
        quarter=1,
        year=2026,
        period_start_date="2026-01-01",
        period_end_date="2026-03-31",
        fiscal_year=2026,
        fiscal_quarter="Q1",
    )
    period_id = period_dao.create_from_model(new_period)
    print(f"Created DimPeriod {period_id}")

    new_actual = FinanceActuals(
        period_id=period_id,
        business_unit_id=business_unit_id,
        account_id=account_id,
        amount=125000.0,
    )
    actual_id = actuals_dao.create_from_model(new_actual)
    print(f"Created FinanceActuals {actual_id}")

    query_entry = QueryLog(
        user_question="What was total revenue for Q1 2026?",
        classified_intent="metric_calculation",
        response_status="answered",
    )
    query_id = query_log_dao.create_from_model(query_entry)
    print(f"Created QueryLog {query_id}")

    print("Loaded actuals:", actuals_dao.get_by_id(actual_id))
    print("Loaded query:", query_log_dao.get_by_id(query_id))

    account_dao.update_from_model(account_id, DimAccount(account_code="4000", account_name="Revenue Updated", account_type="Revenue", financial_statement_section="Income Statement", normal_balance="Credit"))
    print("Updated account:", account_dao.get_by_id(account_id))

    print("All query logs:", query_log_dao.list_all(limit=5))

def getAccounts() -> None:
    db = DatabaseConnection("financial_analyst_copilot.db")

    account_dao = DimAccountDAO(db)
    print(account_dao.list_all(limit=10))

if __name__ == "__main__":
    getAccounts()
