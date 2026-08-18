#define a method, that can behave as a tool for agent tool calling. The method should take in as input a FinancialRequest object, understand the request, generate correct sql based on the request, and return the results
import sqlite3

from agents import function_tool

from services.models.models import FinancialRequest


# ------------------------------------------------------------------
# Governed semantic mappings
# ------------------------------------------------------------------

METRICS = {
    "revenue": {
        "account_types": ["Revenue"],
        "sign_multiplier": 1
    },
    "cogs": {
        "account_types": ["COGS"],
        "sign_multiplier": 1
    },
    "expense": {
        "account_types": ["Expense"],
        "sign_multiplier": 1
    },
    "other_income": {
        "account_types": ["Other Income"],
        "sign_multiplier": 1
    },
    "other_expense": {
        "account_types": ["Other Expense"],
        "sign_multiplier": 1
    }
}


SOURCES = {
    "actual": {
        "table": "finance_actuals",
        "version_column": "scenario",
        "version_value": "Actual"
    },
    "budget": {
        "table": "finance_budget",
        "version_column": "version",
        "version_value": "Original Budget"
    },
    "forecast": {
        "table": "finance_forecast",
        "version_column": "forecast_version",
        "version_value": "Q4 Forecast"
    }
}

@function_tool
def query_financial_data(request: FinancialRequest) -> list[dict]:
    """
    Retrieve authoritative financial information from the
    finance database.

    Use this tool for numerical questions involving actual,
    budget, or forecast financial results, including revenue,
    expenses, COGS, business-unit rankings, comparisons,
    and trends.

    Args:
        operation: Type of financial analysis to perform.
        metric: Financial metric to retrieve.
        scenario: Actual, budget, or forecast data.
        fiscal_year: Fiscal year to query.
        fiscal_quarter: Fiscal quarter to query.
        period_name: Optional specific financial period.
        business_unit_names: Optional business unit name to filter.
        top_n: Number of results for ranking operations.
        rank_direction: Highest or lowest for ranking.
        currency_code: Currency code, normally USD.
    """
    return query_financial_data_impl(request)

def query_financial_data_impl(request: FinancialRequest) -> list[dict]:    

    status = True
    #validate the request parameters
    validate_request(request)

    try:
        # Generate sql
        sql_query, parameters = generate_sql_from_request(request)
        
        # Execute the SQL query against the database
        results = execute_sql_query(sql_query, parameters)

        #print results in a readable format for debugging
        print("Query Results:")
        for result in results:
            print(result)
    except Exception as ex:
        status = False
        results = [{"Error": str(ex)}]

    return {
        "status": "success" if status else "fail",

        "query_context": {
            "operation": request.operation,
            "metric": request.metric,
            "scenario": request.scenario,
            "fiscal_year": request.fiscal_year,
            "fiscal_quarter":
                request.fiscal_quarter,
            "business_unit_names":
                request.business_unit_names,
            "currency_code":
                request.currency_code
        },

        "results": results
    }

def validate_request(request):

    # Implement validation logic for the FinancialRequest object
    # For example, check if required fields are present, if the values are within expected ranges
    if request.operation not in ["get_metric", "rank_business_units", "compare_business_units", "trend"]:
        raise ValueError("Invalid operation specified in the request.")
    if request.metric and request.metric not in METRICS:
        raise ValueError(f"Unsupported metric: {request.metric}")
    if request.scenario and request.scenario not in SOURCES:
        raise ValueError(f"Unsupported scenario: {request.scenario}")
    if request.fiscal_quarter and request.fiscal_quarter not in ["Q1", "Q2", "Q3", "Q4"]:
        raise ValueError("Invalid fiscal quarter specified in the request.")
    if request.rank_direction and request.rank_direction not in ["highest", "lowest"]:
        raise ValueError("Invalid rank direction specified in the request.")

from typing import Any


def generate_sql_from_request(request) -> tuple[str, dict[str, Any]]:
    """
    Convert a validated FinancialRequest into parameterized SQL.

    Expected request fields:

        operation
        metric
        scenario
        fiscal_year
        fiscal_quarter
        period_name
        business_unit_names
        top_n
        rank_direction
        currency_code

    Supported operations:

        get_metric
        rank_business_units
        compare_business_units
        trend

    Returns:

        (sql, params)
    """

    # --------------------------------------------------------------
    # 1. Validate semantic mappings
    # --------------------------------------------------------------

    metric_config = METRICS[request.metric]
    source_config = SOURCES[request.scenario]

    # These identifiers come ONLY from trusted application config.
    # They never come directly from the LLM or user.
    fact_table = source_config["table"]
    version_column = source_config["version_column"]
    version_value = source_config["version_value"]

    sign_multiplier = metric_config.get(
        "sign_multiplier",
        1
    )

    params: dict[str, Any] = {}
    where_clauses: list[str] = []

    # --------------------------------------------------------------
    # 2. Source/version filter
    # --------------------------------------------------------------

    where_clauses.append(
        f"f.{version_column} = :version_value"
    )

    params["version_value"] = version_value

    # --------------------------------------------------------------
    # 3. Currency filter
    # --------------------------------------------------------------

    currency_code = request.currency_code or "USD"

    where_clauses.append(
        "f.currency_code = :currency_code"
    )

    params["currency_code"] = currency_code

    # --------------------------------------------------------------
    # 4. Metric -> dim_account mapping
    # --------------------------------------------------------------

    account_types = metric_config["account_types"]

    account_type_placeholders = []

    for index, account_type in enumerate(account_types):
        param_name = f"account_type_{index}"

        account_type_placeholders.append(
            f":{param_name}"
        )

        params[param_name] = account_type

    where_clauses.append(
        "a.account_type IN ("
        + ", ".join(account_type_placeholders)
        + ")"
    )

    # --------------------------------------------------------------
    # 5. Period filters
    # --------------------------------------------------------------

    if request.fiscal_year is not None:
        where_clauses.append(
            "p.fiscal_year = :fiscal_year"
        )
        params["fiscal_year"] = request.fiscal_year

    if request.fiscal_quarter is not None:
        where_clauses.append(
            "p.fiscal_quarter = :fiscal_quarter"
        )
        params["fiscal_quarter"] = request.fiscal_quarter

    if request.period_name is not None and request.period_name != "":
        where_clauses.append(
            "p.period_name = :period_name"
        )
        params["period_name"] = request.period_name

    # --------------------------------------------------------------
    # 6. Business unit filters
    # --------------------------------------------------------------

    if request.business_unit_names is not None and len(request.business_unit_names) > 0:

        business_unit_placeholders = []

        for index, business_unit in enumerate(
            request.business_unit_names
        ):
            param_name = f"business_unit_{index}"

            business_unit_placeholders.append(
                f":{param_name}"
            )

            params[param_name] = business_unit

        where_clauses.append(
            "bu.business_unit_name IN ("
            + ", ".join(business_unit_placeholders)
            + ")"
        )

    where_sql = "\n          AND ".join(
        where_clauses
    )

    # --------------------------------------------------------------
    # 7. Common FROM/JOIN block
    # --------------------------------------------------------------

    base_from = f"""
        FROM {fact_table} f

        JOIN dim_period p
          ON p.period_id = f.period_id

        JOIN dim_business_unit bu
          ON bu.business_unit_id = f.business_unit_id

        JOIN dim_account a
          ON a.account_id = f.account_id
    """

    metric_expression = (
        f"SUM(f.amount * {sign_multiplier})"
    )

    # --------------------------------------------------------------
    # 8. GET METRIC
    #
    # Example:
    # "What was Healthcare revenue in Q2 2025?"
    # --------------------------------------------------------------

    if request.operation == "get_metric":

        sql = f"""
        SELECT
            {metric_expression} AS metric_value

        {base_from}

        WHERE
            {where_sql}
        """

        return sql.strip(), params

    # --------------------------------------------------------------
    # 9. RANK BUSINESS UNITS
    #
    # Example:
    # "Which BU had the highest revenue in Q2?"
    # --------------------------------------------------------------

    if request.operation == "rank_business_units":

        if request.rank_direction == "lowest":
            sort_direction = "ASC"
        else:
            sort_direction = "DESC"

        top_n = request.top_n or 1

        if top_n < 1 or top_n > 20:
            raise ValueError(
                "top_n must be between 1 and 20"
            )

        params["top_n"] = top_n

        sql = f"""
        SELECT
            bu.business_unit_id,
            bu.business_unit_name,
            {metric_expression} AS metric_value

        {base_from}

        WHERE
            {where_sql}

        GROUP BY
            bu.business_unit_id,
            bu.business_unit_name

        ORDER BY
            metric_value {sort_direction}

        LIMIT :top_n
        """

        return sql.strip(), params

    # --------------------------------------------------------------
    # 10. COMPARE BUSINESS UNITS
    #
    # Example:
    # "Compare revenue between Healthcare and Government."
    # --------------------------------------------------------------

    if request.operation == "compare_business_units":

        if not request.business_unit_names:
            raise ValueError(
                "compare_business_units requires "
                "business_unit_names to be specified."
            )

        sql = f"""
        SELECT
            bu.business_unit_id,
            bu.business_unit_name,
            {metric_expression} AS metric_value

        {base_from}

        WHERE
            {where_sql}

        GROUP BY
            bu.business_unit_id,
            bu.business_unit_name

        ORDER BY
            bu.business_unit_name
        """

        return sql.strip(), params

    # --------------------------------------------------------------
    # 11. TREND
    #
    # Example:
    # "Show Healthcare revenue by period for FY2025."
    # --------------------------------------------------------------

    if request.operation == "trend":

        sql = f"""
        SELECT
            p.period_id,
            p.period_name,
            p.month,
            p.month_name,
            p.quarter,
            p.year,
            p.fiscal_year,
            p.fiscal_quarter,
            p.period_start_date,
            bu.business_unit_id,
            bu.business_unit_name,
            {metric_expression} AS metric_value

        {base_from}

        WHERE
            {where_sql}

        GROUP BY
            p.period_id,
            p.period_name,
            p.month,
            p.month_name,
            p.quarter,
            p.year,
            p.fiscal_year,
            p.fiscal_quarter,
            p.period_start_date,
            bu.business_unit_id,
            bu.business_unit_name

        ORDER BY
            p.period_start_date,
            bu.business_unit_name
        """

        return sql.strip(), params

    raise ValueError(
        f"Unhandled operation: {request.operation}"
    )

def execute_sql_query(sql: str, params: dict[str, Any]) -> list[dict]:
    """
    Execute the given SQL query against the database and return the results.

    Args:
        sql (str): The SQL query to execute.
        params (dict): The parameters for the SQL query.

    Returns:
        list[dict]: The results of the SQL query.
    """

    # This is a placeholder for actual database execution logic.
    # In a real implementation, you would use a database connection and execute the query.
    # For example, using an async database library like asyncpg or databases.

    # Example pseudo-code:
    # async with database_connection() as conn:
    #     results = await conn.fetch(sql, *params.values())
    #     return [dict(row) for row in results]

    try:
        conn = sqlite3.connect("C:\\Rohit\\Trainings\\repo\\FinancialAnalystCopilot\\financial_analyst_copilot.db")
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()

        #print the sql and params in a readable format for debugging
        print("Executing SQL Query:")
        print(sql)
        print("With Parameters:")
        for key, value in params.items():
            print(f"{key}: {value}")

        cursor.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    except Exception as ex:
        print(f"Exception occured querying database for metrics: {ex}")
        raise ex


FINANCE_TOOL = {
    "name": "query_financial_data",

    "description": """
Retrieve authoritative financial data from the finance database.

Use this tool for questions about:
- revenue
- expenses
- COGS
- actual financial performance
- budget
- forecast
- business-unit comparisons
- rankings
- financial trends

Do not use this tool for accounting policies, narrative explanations,
business definitions, or information contained in documents.
""",

    "parameters": {
        "type": "object",

        "properties": {

            "operation": {
                "type": "string",
                "enum": [
                    "get_metric",
                    "rank_business_units",
                    "compare_business_units",
                    "trend"
                ]
            },

            "metric": {
                "type": "string",
                "enum": [
                    "revenue",
                    "cogs",
                    "expense",
                    "other_income",
                    "other_expense"
                ]
            },

            "scenario": {
                "type": "string",
                "enum": [
                    "actual",
                    "budget",
                    "forecast"
                ]
            },

            "fiscal_year": {
                "type": ["integer", "null"]
            },

            "fiscal_quarter": {
                "type": ["string", "null"],
                "enum": [
                    "Q1",
                    "Q2",
                    "Q3",
                    "Q4",
                    None
                ]
            },

            "business_units": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },

            "top_n": {
                "type": ["integer", "null"]
            },

            "rank_direction": {
                "type": ["string", "null"],
                "enum": [
                    "highest",
                    "lowest",
                    None
                ]
            }
        },

        "required": [
            "operation",
            "metric",
            "scenario",
            "fiscal_year",
            "fiscal_quarter",
            "business_units",
            "top_n",
            "rank_direction"
        ],

        "additionalProperties": False
    }
}