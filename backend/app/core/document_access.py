from __future__ import annotations

PRIVILEGED_ROLES = {"plant_manager", "executive"}

ROLE_OWNER_SCOPES: dict[str, set[str]] = {
    "reliability_engineer": {"operations", "maintenance", "reliability", "demo_seed"},
    "maintenance_engineer": {"operations", "maintenance", "reliability", "demo_seed"},
    "operator": {"operations", "maintenance", "demo_seed"},
    "safety_officer": {"operations", "safety", "compliance", "demo_seed"},
    "quality_manager": {"operations", "quality", "compliance", "demo_seed"},
    "compliance_auditor": {"operations", "quality", "compliance", "demo_seed"},
}


def allowed_owner_roles(user_role: str) -> set[str] | None:
    """Return None for plant-wide roles, otherwise the exact permitted owner scopes."""
    if user_role in PRIVILEGED_ROLES:
        return None
    return ROLE_OWNER_SCOPES.get(user_role, set())


def can_access_document(user_role: str, owner_role: str, permission_level: str) -> bool:
    if permission_level == "public":
        return True
    scopes = allowed_owner_roles(user_role)
    return scopes is None or (permission_level == "plant" and owner_role in scopes)


def azure_document_filter(user_role: str) -> str | None:
    """Build an OData filter that Azure AI Search applies before results reach the model."""
    scopes = allowed_owner_roles(user_role)
    if scopes is None:
        return None
    if not scopes:
        return "permission_level eq 'public'"
    escaped = ",".join(sorted(role.replace("'", "''") for role in scopes))
    return (
        "permission_level eq 'public' or "
        f"(permission_level eq 'plant' and search.in(owner_role, '{escaped}', ','))"
    )
