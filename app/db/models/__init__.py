"""Import every model here so it registers itself on Base.metadata."""

from app.db.models.tenant import Tenant

__all__ = ["Tenant"]
