"""Server-resolved request context for organization-scoped API operations."""

from dataclasses import dataclass
from typing import Literal

import app._paths  # noqa: F401

from src.database.connection import DEFAULT_ORGANIZATION_ID


@dataclass(frozen=True)
class OrganizationContext:
    organization_id: int
    user_id: int | None = None
    role: Literal["admin", "hr_officer"] = "admin"


def get_organization_context() -> OrganizationContext:
    """Resolve the local organization without accepting tenant data from clients.

    Supabase authentication can replace this dependency with verified claim
    resolution while preserving the endpoint and service contracts.
    """
    return OrganizationContext(organization_id=DEFAULT_ORGANIZATION_ID, role="admin")
