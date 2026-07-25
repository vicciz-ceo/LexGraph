"""B4 — pure permission-matrix unit tests (spec §12, gate G8).

Exercises `app.services.permissions.has_permission` directly. Body is
`raise NotImplementedError` pending the B4 Developer track.
"""

from __future__ import annotations

import pytest

from app.services.permissions import has_permission


@pytest.mark.parametrize(
    "role,permission,expected",
    [
        ("viewer", "assertion:view", True),
        ("viewer", "assertion:rate", False),
        ("viewer", "assertion:suggest", False),
        ("contributor", "assertion:view", True),
        ("contributor", "assertion:rate", True),
        ("contributor", "assertion:suggest", True),
        ("contributor", "assertion:comment", True),
        ("contributor", "assertion:review", False),
        ("contributor", "assertion:accept", False),
        ("reviewer", "assertion:review", True),
        ("reviewer", "assertion:accept", True),
        ("reviewer", "assertion:reject", True),
        ("reviewer", "assertion:dispute", True),
        ("reviewer", "assertion:manage_types", False),
        ("admin", "assertion:manage_types", True),
        ("admin", "assertion:accept", True),
        ("admin", "assertion:view_rating_rationales", True),
    ],
)
def test_role_permission_matrix(role, permission, expected):
    assert has_permission(role, permission) is expected


def test_unknown_role_grants_nothing():
    assert has_permission("not-a-real-role", "assertion:view") is False


def test_reviewer_is_superset_of_contributor():
    contributor_perms = {"assertion:view", "assertion:rate", "assertion:suggest", "assertion:comment"}
    for perm in contributor_perms:
        assert has_permission("reviewer", perm) is True
