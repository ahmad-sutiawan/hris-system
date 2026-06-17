"""Tenant attendance policy helpers."""


def ot_before_overtime_enabled(tenant, plant) -> bool:
    """HR policy (17 Jun 2026): overtime counted after shift only."""
    return False
