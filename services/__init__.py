try:
    from .api_app import app
except ModuleNotFoundError:
    app = None

__all__ = ["app"]
