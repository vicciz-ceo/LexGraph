"""Assertion permission matrix (shape only — Developer track B4).

Spec §12. Roles: viewer, contributor, reviewer, admin (each a superset of
the previous). Permissions include assertion:view, assertion:rate,
assertion:suggest, assertion:edit_own, assertion:comment,
assertion:review, assertion:accept, assertion:reject, assertion:dispute,
assertion:manage_types, assertion:view_rating_rationales.
"""

from __future__ import annotations

ROLES = ("viewer", "contributor", "reviewer", "admin")

PERMISSIONS = (
    "assertion:view",
    "assertion:rate",
    "assertion:suggest",
    "assertion:edit_own",
    "assertion:comment",
    "assertion:review",
    "assertion:accept",
    "assertion:reject",
    "assertion:dispute",
    "assertion:manage_types",
    "assertion:view_rating_rationales",
)


def has_permission(role: str, permission: str) -> bool:
    """Return whether `role` grants `permission` per the spec §12 matrix."""
    raise NotImplementedError("developer: implement role/permission matrix (B4)")
