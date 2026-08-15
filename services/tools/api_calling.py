import httpx


BASE_URL = "http://127.0.0.1:8000"


async def api_get(path: str, params: dict | None = None):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}{path}",
                params=params,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "error_type": "http_error",
            "status_code": exc.response.status_code,
            "response_body": exc.response.text,
        }

    except httpx.RequestError as exc:
        return {
            "success": False,
            "error_type": "network_error",
            "message": str(exc),
        }

    except Exception as exc:
        return {
            "success": False,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }


async def api_post(path: str, body: dict):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}{path}",
                json=body,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "error_type": "http_error",
            "status_code": exc.response.status_code,
            "response_body": exc.response.text,
        }

    except httpx.RequestError as exc:
        return {
            "success": False,
            "error_type": "network_error",
            "message": str(exc),
        }

    except Exception as exc:
        return {
            "success": False,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }