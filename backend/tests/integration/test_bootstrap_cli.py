"""B1 — bootstrap CLI (`python -m app.bootstrap`) RED tests.

Gate G1 (fresh-instance bootstrap): on an EMPTY database, one documented
command creates an organization + repository + matter + the first user
with the `admin` role on that matter, and prints the sign-in user id
clearly. On a NON-empty database (any `users` row already exists) it
refuses with a non-zero exit and mutates nothing (no silent org/matter/
user creation on top of an existing workspace).

Self-mock ban: `app/bootstrap.py` doesn't exist yet, so these tests invoke
the real command via `subprocess` against a tmp-path SQLite file -- no
mocking of the CLI under test, exactly like `app/seed_demo.py`'s own
"drive the real thing" convention. Today `python -m app.bootstrap` fails
at Python's own import machinery ("No module named app.bootstrap",
nonzero exit, nothing useful on stdout) -- that ModuleNotFoundError is why
every assertion below is expected to fail for the right reason right now.

Table layout asserted via raw sqlite3 (not the ORM) so these tests don't
depend on `app.bootstrap` internals -- only on the schema already defined
in `app/models/*.py`:
  organizations(id, name)
  repositories(id, organization_id, name)
  matters(id, repository_id, name)
  users(id, email, display_name)
  matter_roles(id, user_id, matter_id, role)
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _run_bootstrap(
    args: list[str], *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.bootstrap", *args],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def _rows(db_path: Path, table: str) -> list[tuple]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT * FROM {table}").fetchall()
    finally:
        conn.close()


def test_bootstrap_creates_workspace_and_admin_on_empty_db(tmp_path):
    db_path = tmp_path / "bootstrap.db"

    result = _run_bootstrap(["--db", str(db_path)])

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert db_path.exists(), "bootstrap must create the sqlite file"

    orgs = _rows(db_path, "organizations")
    repos = _rows(db_path, "repositories")
    matters = _rows(db_path, "matters")
    users = _rows(db_path, "users")
    roles = _rows(db_path, "matter_roles")

    assert len(orgs) == 1
    assert len(repos) == 1
    assert len(matters) == 1
    assert len(users) == 1
    assert len(roles) == 1
    assert roles[0][3] == "admin"  # matter_roles(id, user_id, matter_id, role)
    assert roles[0][1] == users[0][0]  # the role belongs to the one user created
    assert roles[0][2] == matters[0][0]  # ... on the one matter created

    # The sign-in credential (the user id) must be printed clearly so an
    # operator can hand it to the first admin (R3: id IS the credential).
    user_id = users[0][0]
    assert user_id in result.stdout


def test_bootstrap_refuses_on_nonempty_db_without_mutating(tmp_path):
    db_path = tmp_path / "bootstrap.db"
    first = _run_bootstrap(["--db", str(db_path)])
    assert first.returncode == 0, f"stdout={first.stdout!r} stderr={first.stderr!r}"

    second = _run_bootstrap(["--db", str(db_path)])

    assert second.returncode != 0, "must refuse on a non-empty database"
    assert (second.stdout + second.stderr).strip() != "", "refusal must print a clear message"

    # No silent mutation: still exactly the one org/matter/user from the
    # first run.
    assert len(_rows(db_path, "organizations")) == 1
    assert len(_rows(db_path, "matters")) == 1
    assert len(_rows(db_path, "users")) == 1


def test_bootstrap_accepts_custom_org_matter_user_names_and_email(tmp_path):
    db_path = tmp_path / "bootstrap.db"

    result = _run_bootstrap(
        [
            "--db",
            str(db_path),
            "--org-name",
            "Acme Legal",
            "--matter-name",
            "Acme v. Zenith",
            "--user-name",
            "Root Admin",
            "--user-email",
            "root@acme.test",
        ]
    )

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"

    orgs = _rows(db_path, "organizations")
    matters = _rows(db_path, "matters")
    users = _rows(db_path, "users")

    assert orgs[0][1] == "Acme Legal"
    assert matters[0][2] == "Acme v. Zenith"
    assert users[0][1] == "root@acme.test"
    assert users[0][2] == "Root Admin"
    assert users[0][0] in result.stdout


def test_bootstrap_reads_database_url_env_when_no_db_flag(tmp_path):
    db_path = tmp_path / "env-bootstrap.db"
    env = {**os.environ, "LEXGRAPH_DATABASE_URL": f"sqlite:///{db_path}"}
    env.pop("LEXGRAPH_DB", None)

    result = _run_bootstrap([], env=env)

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert db_path.exists(), "bootstrap must honor LEXGRAPH_DATABASE_URL like app/config.py"
    assert len(_rows(db_path, "users")) == 1


def test_bootstrap_refuses_on_db_seeded_by_a_different_tool(tmp_path):
    # QA regression (2026-07-31-admin-provisioning): the existing refusal
    # test only proves the guard trips on a DB that bootstrap itself
    # created. The guard's actual implementation (app/bootstrap.py) checks
    # for ANY existing `users` row, origin-agnostic -- so it must also
    # refuse against a database populated by app/seed_demo.py, not just a
    # prior bootstrap run. Pins that origin-agnostic behavior directly
    # rather than assuming it from the other test.
    db_path = tmp_path / "seeded.db"
    seed = subprocess.run(
        [sys.executable, "-m", "app.seed_demo", "--db", str(db_path)],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert seed.returncode == 0, f"stdout={seed.stdout!r} stderr={seed.stderr!r}"
    seeded_user_count = len(_rows(db_path, "users"))
    assert seeded_user_count > 0, "seed_demo must have created users for this test to be valid"

    result = _run_bootstrap(["--db", str(db_path)])

    assert result.returncode != 0, "must refuse on a DB seeded by a different tool"
    assert (result.stdout + result.stderr).strip() != "", "refusal must print a clear message"
    # No silent mutation: still exactly the seed's own users, nothing added.
    assert len(_rows(db_path, "users")) == seeded_user_count
    assert len(_rows(db_path, "organizations")) == 1
