"""Bootstrap the FIRST workspace + admin on an EMPTY database (Gate G1).

Usage (from ``backend/``, after ``pip install -e '.[dev]'``):

    .venv/bin/python -m app.bootstrap --db dev.db
    .venv/bin/python -m app.bootstrap --db dev.db --org-name "Acme Legal" \\
        --matter-name "Acme v. Zenith" --user-name "Root Admin" \\
        --user-email root@acme.test

    LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/python -m app.bootstrap

Creates one organization + repository + matter + the first user, with an
``admin`` ``matter_roles`` row on that matter, then prints the new admin's
sign-in token. The token is generated randomly, stored only as a hash, and
shown this one time (``app/auth.py``): the operator hands it to the first
admin, who enters it on the sign-in page. A lost token is replaced with
``python -m app.rotate_sign_in_token``.

A database is required: ``--db PATH`` or ``LEXGRAPH_DATABASE_URL``. The
settings default is a throwaway in-memory database, so without either (or
with an in-memory URL) bootstrap exits 2 instead of reporting success for
an account that vanishes when it exits (findings api:26, ops:13). The
flags are checked before the database is touched, with the Users API's
rules (``app.routers.users.clean_account_fields``: a valid email, stored
lowercased; a non-blank display name); organization and matter names must
not be blank. Invalid input also exits 2.

Refuses (exit 1) to run on a NON-empty database (any existing ``users``
row) -- no silent mutation on top of an already-bootstrapped workspace --
and on a database whose ``users`` table predates sign-in tokens (upgrade it
first). Both checks run before any table is created, so the refusal really
changes nothing. Serve the result the way the printed hint says.
"""

from __future__ import annotations

import argparse
import os
import shlex
import sys
import uuid
from pathlib import Path

#: Organization/matter names; the repository is named "<org> Repository",
#: and all three columns are VARCHAR(255).
NAME_MAX_LENGTH = 200

_ACCOUNT_FLAGS = {"email": "--user-email", "display_name": "--user-name"}


def _usage_error(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def _is_in_memory(url) -> bool:
    if url.get_backend_name() != "sqlite":
        return False
    database = url.database or ""
    return database == "" or ":memory:" in database or url.query.get("mode") == "memory"


def _clean_name(value: str, flag: str) -> str:
    name = value.strip()
    if not name:
        raise ValueError(f"{flag} must not be blank")
    if len(name) > NAME_MAX_LENGTH:
        raise ValueError(f"{flag} must be at most {NAME_MAX_LENGTH} characters")
    return name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite file to create (sets LEXGRAPH_DATABASE_URL; mirrors app/seed_demo.py). "
        "If omitted, LEXGRAPH_DATABASE_URL is used; one of the two is required.",
    )
    parser.add_argument("--org-name", default="LexGraph", help="organization name")
    parser.add_argument("--matter-name", default="General Matter", help="first matter's name")
    parser.add_argument("--user-name", default="Admin", help="first admin's display name")
    parser.add_argument(
        "--user-email", default="admin@lexgraph.local", help="first admin's email"
    )
    args = parser.parse_args(argv)

    from sqlalchemy import inspect, select, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import ArgumentError, SQLAlchemyError

    from app.routers.users import AccountInputError, clean_account_fields

    # --- Where to write: a persistent database, never the in-memory default.
    if args.db is not None:
        if not args.db.strip():
            return _usage_error("--db must not be empty")
        parent = Path(args.db).resolve().parent
        if not parent.is_dir():
            return _usage_error(f"--db: directory {parent} does not exist")
        url_text = f"sqlite:///{args.db}"
    else:
        url_text = os.environ.get("LEXGRAPH_DATABASE_URL", "").strip()
        if not url_text:
            return _usage_error(
                "no database given: pass --db PATH or set LEXGRAPH_DATABASE_URL to the database "
                "the server will use (the default is an in-memory database that is discarded "
                "when bootstrap exits)"
            )
    try:
        url = make_url(url_text)
    except ArgumentError:
        return _usage_error(f"LEXGRAPH_DATABASE_URL is not a database URL: {url_text!r}")
    if _is_in_memory(url):
        return _usage_error(
            f"{url_text} is an in-memory database: nothing bootstrap creates would outlive "
            "this command. Pass --db PATH or set LEXGRAPH_DATABASE_URL to a persistent database."
        )

    # --- What to write: the Users API's rules, before touching the database.
    try:
        email, user_name, _ = clean_account_fields(args.user_email, args.user_name)
    except AccountInputError as exc:
        return _usage_error(f"{_ACCOUNT_FLAGS[exc.field]}: {exc}")
    try:
        org_name = _clean_name(args.org_name, "--org-name")
        matter_name = _clean_name(args.matter_name, "--matter-name")
    except ValueError as exc:
        return _usage_error(str(exc))

    import app.models  # noqa: F401  (register ORM mappings)
    from app.auth import issue_sign_in_token
    from app.db import Base, make_engine, make_session_factory
    from app.models.matter import Matter
    from app.models.matter_role import MatterRole
    from app.models.organization import Organization
    from app.models.repository import Repository
    from app.models.user import User

    from app.migrate import upgrade_command

    engine = make_engine(url_text)
    try:
        # Guards first, so a refusal really leaves the database untouched.
        inspector = inspect(engine)
        if inspector.has_table("users"):
            with engine.connect() as conn:
                has_users = conn.execute(text("SELECT 1 FROM users LIMIT 1")).first() is not None
            if has_users:
                print(
                    "Refusing to bootstrap: the database already has users. "
                    "Bootstrap only runs on an empty database — nothing was changed.\n"
                    "To bring an existing workspace up to this version of LexGraph, run instead "
                    f"(safe to re-run):\n    {upgrade_command(url)}"
                )
                return 1
            columns = {column["name"] for column in inspector.get_columns("users")}
            if "sign_in_token_hash" not in columns:
                print(
                    "Refusing to bootstrap: this database's users table predates sign-in "
                    "tokens — nothing was changed. Upgrade it first (see docs/RUNBOOK.md):\n"
                    f"    {upgrade_command(url)}"
                )
                return 1

        Base.metadata.create_all(bind=engine)
        with make_session_factory(engine)() as session:
            # Checked again now that the schema exists: another bootstrap may
            # have run in the meantime.
            if session.execute(select(User.id).limit(1)).first() is not None:
                print(
                    "Refusing to bootstrap: the database already has users. "
                    "Bootstrap only runs on an empty database — nothing was changed."
                )
                return 1
            org = Organization(id=str(uuid.uuid4()), name=org_name)
            repo = Repository(
                id=str(uuid.uuid4()), organization_id=org.id, name=f"{org_name} Repository"
            )
            matter = Matter(id=str(uuid.uuid4()), repository_id=repo.id, name=matter_name)
            user = User(id=str(uuid.uuid4()), email=email, display_name=user_name)
            sign_in_token = issue_sign_in_token(user)
            admin_role = MatterRole(
                id=str(uuid.uuid4()), user_id=user.id, matter_id=matter.id, role="admin"
            )
            session.add_all([org, repo, matter, user, admin_role])
            session.commit()
    except SQLAlchemyError as exc:
        shown = url.render_as_string(hide_password=True)
        print(f"error: could not bootstrap {shown}: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    # The real database in every hint (it used to say "<same db>"); a
    # password in the URL is masked.
    shown_url = shlex.quote(url.render_as_string(hide_password=True))
    if args.db is not None:
        rotate = f".venv/bin/python -m app.rotate_sign_in_token --db {shlex.quote(args.db)}"
    else:
        rotate = f"LEXGRAPH_DATABASE_URL={shown_url} .venv/bin/python -m app.rotate_sign_in_token"
    print(f"Bootstrapped organization {org.name!r}, matter {matter.name!r} in {shown_url}.")
    print(f"Admin sign-in token (shown once, keep it secret): {sign_in_token}")
    print("Only a hash is stored. If it is lost:")
    print(f"  {rotate} --email {shlex.quote(email)}")
    print("Serve it:")
    print(f"  LEXGRAPH_DATABASE_URL={shown_url} .venv/bin/uvicorn app.main:app --port 8000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
