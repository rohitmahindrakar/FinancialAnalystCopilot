# Financial Analyst Copilot API Documentation

This document describes the generated FastAPI endpoints in `services/api_app.py`.

## Run the API

From the repository root:

```bash
pip install fastapi uvicorn
uvicorn database.api_app:app --reload
```

The API will be available at `http://127.0.0.1:8000` and the OpenAPI docs at `http://127.0.0.1:8000/docs`.

---

## Health

### GET /health

Check service status and database connectivity.

#### Sample response

```json
{
  "status": "ok",
  "database_connected": true
}
```

---

## Intent routing

### GET /tools

List available Ollama-enabled API tools.

#### Sample response

```json
{
  "tools": [
    {
      "name": "health_check",
      "description": "Check API health and database connectivity.",
      "method": "GET",
      "path": "/health"
    }
  ]
}
```

---

### POST /intent/route

Route a user question to the best API tool according to local Ollama.

#### Request body sample

```json
{
  "user_question": "What is the revenue for Q1?"
}
```

#### Sample response

```json
{
  "tool_name": "list_periods",
  "tool_path": "/periods",
  "tool_method": "GET",
  "description": "List period records with optional filters.",
  "intent": "period_lookup",
  "arguments": {}
}
```

---

## Metadata

### GET /metadata/tables

List supported database table names.

#### Sample response

```json
{
  "tables": [
    "answer_citation",
    "calculation_result",
    "dim_account",
    "dim_business_unit",
    "dim_period",
    "document_chunk",
    "evaluation_result",
    "evaluation_test_case",
    "finance_actuals",
    "finance_budget",
    "finance_forecast",
    "kpi_registry",
    "query_log",
    "source_document",
    "user_feedback"
  ]
}
```

---

## Accounts

### GET /accounts

List accounts with optional filters and pagination.

Query parameters:
- `limit` (default `25`)
- `offset` (default `0`)
- `account_code`
- `account_type`
- `active_flag`
- `parent_account_id`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "account_id": 1,
      "account_code": "4000",
      "account_name": "Revenue",
      "account_type": "Revenue",
      "parent_account_id": null,
      "financial_statement_section": "Income Statement",
      "normal_balance": "Credit",
      "active_flag": 1
    }
  ]
}
```

### GET /accounts/{account_id}

Retrieve a single account by ID.

#### Sample response

```json
{
  "account_id": 1,
  "account_code": "4000",
  "account_name": "Revenue",
  "account_type": "Revenue",
  "parent_account_id": null,
  "financial_statement_section": "Income Statement",
  "normal_balance": "Credit",
  "active_flag": 1
}
```

### POST /accounts

Create a new account.

#### Request body sample

```json
{
  "account_code": "4000",
  "account_name": "Revenue",
  "account_type": "Revenue",
  "financial_statement_section": "Income Statement",
  "normal_balance": "Credit"
}
```

#### Sample response

```json
{
  "account_id": 123
}
```

### PUT /accounts/{account_id}

Update an existing account.

#### Request body sample

```json
{
  "account_name": "Revenue Updated",
  "active_flag": 1
}
```

#### Sample response

```json
{
  "account_id": 123
}
```

### DELETE /accounts/{account_id}

Delete an account by ID.

#### Sample response

- HTTP 204 No Content

---

## Business units

### GET /business-units

List business units with optional filters and pagination.

Query parameters:
- `limit`
- `offset`
- `region`
- `segment`
- `active_flag`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "business_unit_id": 1,
      "business_unit_name": "Corporate",
      "parent_business_unit_id": null,
      "region": "North America",
      "segment": "Global",
      "active_flag": 1
    }
  ]
}
```

### GET /business-units/{business_unit_id}

Retrieve a single business unit.

#### Sample response

```json
{
  "business_unit_id": 1,
  "business_unit_name": "Corporate",
  "parent_business_unit_id": null,
  "region": "North America",
  "segment": "Global",
  "active_flag": 1
}
```

### POST /business-units

Create a new business unit.

#### Request body sample

```json
{
  "business_unit_name": "Corporate",
  "region": "North America",
  "segment": "Global"
}
```

#### Sample response

```json
{
  "business_unit_id": 45
}
```

### PUT /business-units/{business_unit_id}

Update a business unit.

#### Sample response

```json
{
  "business_unit_id": 45
}
```

### DELETE /business-units/{business_unit_id}

Delete a business unit.

#### Sample response

- HTTP 204 No Content

---

## Periods

### GET /periods

List periods with optional filters.

Query parameters:
- `year`
- `quarter`
- `month`
- `fiscal_year`
- `is_closed`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "period_id": 1,
      "period_name": "FY2026-Q1",
      "month": 3,
      "month_name": "March",
      "quarter": 1,
      "year": 2026,
      "period_start_date": "2026-01-01",
      "period_end_date": "2026-03-31",
      "fiscal_year": 2026,
      "fiscal_quarter": "Q1",
      "is_closed": 1
    }
  ]
}
```

### GET /periods/{period_id}

#### Sample response

```json
{
  "period_id": 1,
  "period_name": "FY2026-Q1",
  "month": 3,
  "month_name": "March",
  "quarter": 1,
  "year": 2026,
  "period_start_date": "2026-01-01",
  "period_end_date": "2026-03-31",
  "fiscal_year": 2026,
  "fiscal_quarter": "Q1",
  "is_closed": 1
}
```

### POST /periods

Create a period.

#### Request body sample

```json
{
  "period_name": "FY2026-Q1",
  "month": 3,
  "month_name": "March",
  "quarter": 1,
  "year": 2026,
  "period_start_date": "2026-01-01",
  "period_end_date": "2026-03-31",
  "fiscal_year": 2026,
  "fiscal_quarter": "Q1"
}
```

#### Sample response

```json
{
  "period_id": 7
}
```

### PUT /periods/{period_id}

#### Sample response

```json
{
  "period_id": 7
}
```

### DELETE /periods/{period_id}

- HTTP 204 No Content

---

## Source documents

### GET /source-documents

List source documents with optional filters.

Query parameters:
- `document_type`
- `source_category`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "source_document_id": 1,
      "document_name": "Revenue Glossary",
      "document_type": "Glossary",
      "document_path": "/data/revenue_glossary.pdf",
      "source_category": "Glossary",
      "created_date": "2026-01-01",
      "loaded_timestamp": "2026-01-01T12:00:00",
      "checksum": "abc123",
      "description": "Revenue definitions"
    }
  ]
}
```

### GET /source-documents/{source_document_id}

#### Sample response

```json
{
  "source_document_id": 1,
  "document_name": "Revenue Glossary",
  "document_type": "Glossary",
  "document_path": "/data/revenue_glossary.pdf",
  "source_category": "Glossary",
  "created_date": "2026-01-01",
  "loaded_timestamp": "2026-01-01T12:00:00",
  "checksum": "abc123",
  "description": "Revenue definitions"
}
```

### POST /source-documents

#### Request body sample

```json
{
  "document_name": "Revenue Glossary",
  "document_type": "Glossary",
  "document_path": "/data/revenue_glossary.pdf",
  "source_category": "Glossary"
}
```

#### Sample response

```json
{
  "source_document_id": 12
}
```

### PUT /source-documents/{source_document_id}

#### Sample response

```json
{
  "source_document_id": 12
}
```

### DELETE /source-documents/{source_document_id}

- HTTP 204 No Content

---

## Answer citations

### GET /answer-citations

List answer citations with optional filters.

Query parameters:
- `query_id`
- `source_document_id`
- `chunk_id`
- `citation_type`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "citation_id": 1,
      "query_id": 10,
      "source_document_id": 1,
      "chunk_id": 5,
      "source_table": "finance_actuals",
      "source_column": "amount",
      "citation_type": "Data",
      "citation_text": "Q1 actual revenue",
      "created_timestamp": "2026-07-21T12:00:00"
    }
  ]
}
```

### GET /answer-citations/{citation_id}

#### Sample response

```json
{
  "citation_id": 1,
  "query_id": 10,
  "source_document_id": 1,
  "chunk_id": 5,
  "source_table": "finance_actuals",
  "source_column": "amount",
  "citation_type": "Data",
  "citation_text": "Q1 actual revenue",
  "created_timestamp": "2026-07-21T12:00:00"
}
```

### POST /answer-citations

#### Request body sample

```json
{
  "query_id": 10,
  "source_document_id": 1,
  "chunk_id": 5,
  "citation_type": "Data",
  "citation_text": "Q1 actual revenue"
}
```

#### Sample response

```json
{
  "citation_id": 22
}
```

### PUT /answer-citations/{citation_id}

#### Sample response

```json
{
  "citation_id": 22
}
```

### DELETE /answer-citations/{citation_id}

- HTTP 204 No Content

---

## Calculation results

### GET /calculation-results

List calculation results with optional filters.

Query parameters:
- `query_id`
- `kpi_id`
- `period_id`
- `business_unit_id`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "calculation_id": 1,
      "query_id": 10,
      "kpi_id": 2,
      "period_id": 3,
      "business_unit_id": 4,
      "formula_used": "SUM(amount)",
      "result_value": 100000.0,
      "comparison_value": 95000.0,
      "variance_amount": 5000.0,
      "variance_percent": 5.26,
      "calculation_sql": "SELECT SUM(amount) FROM ...",
      "created_timestamp": "2026-07-21T12:00:00"
    }
  ]
}
```

### GET /calculation-results/{calculation_id}

#### Sample response

```json
{
  "calculation_id": 1,
  "query_id": 10,
  "kpi_id": 2,
  "period_id": 3,
  "business_unit_id": 4,
  "formula_used": "SUM(amount)",
  "result_value": 100000.0,
  "comparison_value": 95000.0,
  "variance_amount": 5000.0,
  "variance_percent": 5.26,
  "calculation_sql": "SELECT SUM(amount) FROM ...",
  "created_timestamp": "2026-07-21T12:00:00"
}
```

### POST /calculation-results

#### Request body sample

```json
{
  "query_id": 10,
  "formula_used": "SUM(amount)",
  "result_value": 100000.0,
  "comparison_value": 95000.0,
  "variance_amount": 5000.0,
  "variance_percent": 5.26,
  "calculation_sql": "SELECT SUM(amount) FROM ..."
}
```

#### Sample response

```json
{
  "calculation_id": 33
}
```

### PUT /calculation-results/{calculation_id}

#### Sample response

```json
{
  "calculation_id": 33
}
```

### DELETE /calculation-results/{calculation_id}

- HTTP 204 No Content

---

## Document chunks

### GET /document-chunks

List document chunks with optional filters.

Query parameters:
- `source_document_id`
- `chunk_type`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "chunk_id": 5,
      "source_document_id": 1,
      "chunk_text": "Revenue definition text...",
      "chunk_type": "KPI Definition",
      "page_number": 1,
      "section_title": "Revenue",
      "embedding_id": "embed_123",
      "created_timestamp": "2026-07-21T12:00:00"
    }
  ]
}
```

### GET /document-chunks/{chunk_id}

#### Sample response

```json
{
  "chunk_id": 5,
  "source_document_id": 1,
  "chunk_text": "Revenue definition text...",
  "chunk_type": "KPI Definition",
  "page_number": 1,
  "section_title": "Revenue",
  "embedding_id": "embed_123",
  "created_timestamp": "2026-07-21T12:00:00"
}
```

### POST /document-chunks

#### Request body sample

```json
{
  "source_document_id": 1,
  "chunk_text": "Revenue definition text...",
  "chunk_type": "KPI Definition"
}
```

#### Sample response

```json
{
  "chunk_id": 101
}
```

### PUT /document-chunks/{chunk_id}

#### Sample response

```json
{
  "chunk_id": 101
}
```

### DELETE /document-chunks/{chunk_id}

- HTTP 204 No Content

---

## Evaluation results

### GET /evaluation-results

List evaluation results with optional filters.

Query parameters:
- `test_case_id`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "evaluation_result_id": 1,
      "test_case_id": 10,
      "actual_intent": "definition_lookup",
      "actual_response": "Revenue is ...",
      "citation_present_flag": 1,
      "numeric_answer_correct_flag": 1,
      "fallback_correct_flag": 0,
      "score": 95.0,
      "notes": "Correct result",
      "run_timestamp": "2026-07-21T12:00:00"
    }
  ]
}
```

### GET /evaluation-results/{evaluation_result_id}

#### Sample response

```json
{
  "evaluation_result_id": 1,
  "test_case_id": 10,
  "actual_intent": "definition_lookup",
  "actual_response": "Revenue is ...",
  "citation_present_flag": 1,
  "numeric_answer_correct_flag": 1,
  "fallback_correct_flag": 0,
  "score": 95.0,
  "notes": "Correct result",
  "run_timestamp": "2026-07-21T12:00:00"
}
```

### POST /evaluation-results

#### Request body sample

```json
{
  "test_case_id": 10,
  "actual_intent": "definition_lookup",
  "actual_response": "Revenue is ...",
  "citation_present_flag": 1,
  "numeric_answer_correct_flag": 1,
  "fallback_correct_flag": 0,
  "score": 95.0,
  "notes": "Correct result"
}
```

#### Sample response

```json
{
  "evaluation_result_id": 55
}
```

### PUT /evaluation-results/{evaluation_result_id}

#### Sample response

```json
{
  "evaluation_result_id": 55
}
```

### DELETE /evaluation-results/{evaluation_result_id}

- HTTP 204 No Content

---

## Evaluation test cases

### GET /evaluation-test-cases

List evaluation test cases with optional filters.

Query parameters:
- `active_flag`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "test_case_id": 10,
      "question": "What is revenue?",
      "expected_intent": "definition_lookup",
      "expected_metric": "Revenue",
      "expected_behavior": "answer",
      "expected_source": "Glossary",
      "category": "definition",
      "active_flag": 1
    }
  ]
}
```

### GET /evaluation-test-cases/{test_case_id}

#### Sample response

```json
{
  "test_case_id": 10,
  "question": "What is revenue?",
  "expected_intent": "definition_lookup",
  "expected_metric": "Revenue",
  "expected_behavior": "answer",
  "expected_source": "Glossary",
  "category": "definition",
  "active_flag": 1
}
```

### POST /evaluation-test-cases

#### Request body sample

```json
{
  "question": "What is revenue?",
  "expected_intent": "definition_lookup",
  "expected_behavior": "answer",
  "category": "definition"
}
```

#### Sample response

```json
{
  "test_case_id": 77
}
```

### PUT /evaluation-test-cases/{test_case_id}

#### Sample response

```json
{
  "test_case_id": 77
}
```
```

### DELETE /evaluation-test-cases/{test_case_id}

- HTTP 204 No Content

---

## Finance actuals

### GET /finance/actuals

List finance actuals with optional filters.

Query parameters:
- `period_id`
- `business_unit_id`
- `account_id`
- `scenario`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "actual_id": 1,
      "period_id": 3,
      "business_unit_id": 4,
      "account_id": 1,
      "scenario": "Actual",
      "amount": 125000.0,
      "currency_code": "USD",
      "source_file_id": null,
      "load_timestamp": "2026-07-21T12:00:00"
    }
  ]
}
```

### GET /finance/actuals/{actual_id}

#### Sample response

```json
{
  "actual_id": 1,
  "period_id": 3,
  "business_unit_id": 4,
  "account_id": 1,
  "scenario": "Actual",
  "amount": 125000.0,
  "currency_code": "USD",
  "source_file_id": null,
  "load_timestamp": "2026-07-21T12:00:00"
}
```

### POST /finance/actuals

#### Request body sample

```json
{
  "period_id": 3,
  "business_unit_id": 4,
  "account_id": 1,
  "amount": 125000.0
}
```

#### Sample response

```json
{
  "actual_id": 88
}
```

### PUT /finance/actuals/{actual_id}

#### Sample response

```json
{
  "actual_id": 88
}
```

### DELETE /finance/actuals/{actual_id}

- HTTP 204 No Content

---

## Finance budgets

### GET /finance/budgets

List finance budgets with optional filters.

Query parameters:
- `period_id`
- `business_unit_id`
- `account_id`
- `version`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "budget_id": 1,
      "period_id": 3,
      "business_unit_id": 4,
      "account_id": 1,
      "amount": 130000.0,
      "currency_code": "USD",
      "version": "Original Budget",
      "source_file_id": null,
      "load_timestamp": "2026-07-21T12:00:00"
    }
  ]
}
```

### GET /finance/budgets/{budget_id}

#### Sample response

```json
{
  "budget_id": 1,
  "period_id": 3,
  "business_unit_id": 4,
  "account_id": 1,
  "amount": 130000.0,
  "currency_code": "USD",
  "version": "Original Budget",
  "source_file_id": null,
  "load_timestamp": "2026-07-21T12:00:00"
}
```

### POST /finance/budgets

#### Request body sample

```json
{
  "period_id": 3,
  "business_unit_id": 4,
  "account_id": 1,
  "amount": 130000.0
}
```

#### Sample response

```json
{
  "budget_id": 90
}
```

### PUT /finance/budgets/{budget_id}

#### Sample response

```json
{
  "budget_id": 90
}
```

### DELETE /finance/budgets/{budget_id}

- HTTP 204 No Content

---

## Finance forecasts

### GET /finance/forecasts

List finance forecasts with optional filters.

Query parameters:
- `period_id`
- `business_unit_id`
- `account_id`
- `forecast_version`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "forecast_id": 1,
      "period_id": 3,
      "business_unit_id": 4,
      "account_id": 1,
      "amount": 135000.0,
      "forecast_version": "Q2 Forecast",
      "currency_code": "USD",
      "source_file_id": null,
      "load_timestamp": "2026-07-21T12:00:00"
    }
  ]
}
```

### GET /finance/forecasts/{forecast_id}

#### Sample response

```json
{
  "forecast_id": 1,
  "period_id": 3,
  "business_unit_id": 4,
  "account_id": 1,
  "amount": 135000.0,
  "forecast_version": "Q2 Forecast",
  "currency_code": "USD",
  "source_file_id": null,
  "load_timestamp": "2026-07-21T12:00:00"
}
```

### POST /finance/forecasts

#### Request body sample

```json
{
  "period_id": 3,
  "business_unit_id": 4,
  "account_id": 1,
  "amount": 135000.0
}
```

#### Sample response

```json
{
  "forecast_id": 95
}
```

### PUT /finance/forecasts/{forecast_id}

#### Sample response

```json
{
  "forecast_id": 95
}
```

### DELETE /finance/forecasts/{forecast_id}

- HTTP 204 No Content

---

## KPI registry

### GET /kpis

List KPIs with optional filters.

Query parameters:
- `active_flag`
- `source_table`
- `owner`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "kpi_id": 1,
      "kpi_name": "Revenue Growth",
      "business_definition": "Revenue growth year-over-year",
      "formula": "(current - prior) / prior",
      "source_table": "finance_actuals",
      "required_columns": "amount, period_id",
      "default_grain": "business_unit_period",
      "owner": "Finance",
      "citation_source_id": null,
      "active_flag": 1,
      "notes": null
    }
  ]
}
```

### GET /kpis/{kpi_id}

#### Sample response

```json
{
  "kpi_id": 1,
  "kpi_name": "Revenue Growth",
  "business_definition": "Revenue growth year-over-year",
  "formula": "(current - prior) / prior",
  "source_table": "finance_actuals",
  "required_columns": "amount, period_id",
  "default_grain": "business_unit_period",
  "owner": "Finance",
  "citation_source_id": null,
  "active_flag": 1,
  "notes": null
}
```

### POST /kpis

#### Request body sample

```json
{
  "kpi_name": "Revenue Growth",
  "business_definition": "Revenue growth year-over-year",
  "formula": "(current - prior) / prior",
  "source_table": "finance_actuals",
  "required_columns": "amount, period_id",
  "default_grain": "business_unit_period",
  "owner": "Finance"
}
```

#### Sample response

```json
{
  "kpi_id": 101
}
```

### PUT /kpis/{kpi_id}

#### Sample response

```json
{
  "kpi_id": 101
}
```

### DELETE /kpis/{kpi_id}

- HTTP 204 No Content

---

## Queries

### GET /queries

List queries with optional filters.

Query parameters:
- `classified_intent`
- `response_status`
- `requires_clarification`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "query_id": 1,
      "user_question": "What was total revenue for Q1 2026?",
      "classified_intent": "metric_calculation",
      "resolved_metric": null,
      "resolved_period": null,
      "requires_clarification": 0,
      "response_status": "answered",
      "response_text": null,
      "created_timestamp": "2026-07-21T12:00:00"
    }
  ]
}
```

### GET /queries/{query_id}

#### Sample response

```json
{
  "query_id": 1,
  "user_question": "What was total revenue for Q1 2026?",
  "classified_intent": "metric_calculation",
  "resolved_metric": null,
  "resolved_period": null,
  "requires_clarification": 0,
  "response_status": "answered",
  "response_text": null,
  "created_timestamp": "2026-07-21T12:00:00"
}
```

### POST /queries

#### Request body sample

```json
{
  "user_question": "What was total revenue for Q1 2026?",
  "classified_intent": "metric_calculation",
  "response_status": "answered"
}
```

#### Sample response

```json
{
  "query_id": 1
}
```

### PUT /queries/{query_id}

#### Sample response

```json
{
  "query_id": 1
}
```

### DELETE /queries/{query_id}

- HTTP 204 No Content

---

## Feedback

### GET /feedback

List feedback records with optional filters.

Query parameters:
- `query_id`
- `rating`

#### Sample response

```json
{
  "total": 1,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "feedback_id": 1,
      "query_id": 1,
      "rating": "thumbs_up",
      "confidence_score": 5,
      "comment": "Accurate answer",
      "created_timestamp": "2026-07-21T12:00:00"
    }
  ]
}
```

### GET /feedback/{feedback_id}

#### Sample response

```json
{
  "feedback_id": 1,
  "query_id": 1,
  "rating": "thumbs_up",
  "confidence_score": 5,
  "comment": "Accurate answer",
  "created_timestamp": "2026-07-21T12:00:00"
}
```

### POST /feedback

#### Request body sample

```json
{
  "query_id": 1,
  "rating": "thumbs_up",
  "confidence_score": 5,
  "comment": "Accurate answer"
}
```

#### Sample response

```json
{
  "feedback_id": 10
}
```

### PUT /feedback/{feedback_id}

#### Sample response

```json
{
  "feedback_id": 10
}
```

### DELETE /feedback/{feedback_id}

- HTTP 204 No Content

---

## Notes

- List endpoints return paginated responses using `total`, `limit`, `offset`, and `items`.
- Create endpoints return the generated primary key.
- Update endpoints return the same record ID when successful.
- Delete endpoints return `204 No Content`.
- All endpoints use `application/json` request and response bodies unless otherwise noted.
