from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resource: str
    action: str
    description: str | None

    @computed_field
    @property
    def code(self) -> str:
        """Clients match on this, e.g. "users:delete"."""
        return f"{self.resource}:{self.action}"
