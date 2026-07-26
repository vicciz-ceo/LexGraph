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


_VIEWER_PERMISSIONS = frozenset({"assertion:view"})

_CONTRIBUTOR_PERMISSIONS = _VIEWER_PERMISSIONS | frozenset(
    {
        "assertion:rate",
        "assertion:suggest",
        "assertion:edit_own",
        "assertion:comment",
    }
)

_REVIEWER_PERMISSIONS = _CONTRIBUTOR_PERMISSIONS | frozenset(
    {
        "assertion:review",
        "assertion:accept",
        "assertion:reject",
        "assertion:dispute",
        "assertion:view_rating_rationales",
    }
)

_ADMIN_PERMISSIONS = _REVIEWER_PERMISSIONS | frozenset({"assertion:manage_types"})

# Each role is an explicit superset of the previous one, per spec §12's
# "Suggested roles" (Reviewer = "All Contributor permissions" + ...,
# Administrator = "All Reviewer permissions" + ...).
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": _VIEWER_PERMISSIONS,
    "contributor": _CONTRIBUTOR_PERMISSIONS,
    "reviewer": _REVIEWER_PERMISSIONS,
    "admin": _ADMIN_PERMISSIONS,
}


def has_permission(role: str, permission: str) -> bool:
    """Return whether `role` grants `permission` per the spec §12 matrix.

    Unknown roles (including `None`/empty string, used for callers with no
    matter_roles row at all) grant nothing.
    """
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
