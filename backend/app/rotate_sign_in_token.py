"""Issue a new sign-in token for an account, or list legacy sign-ins.

Operator tool for lockouts (a lost token, or the only admin's token) and
for retiring legacy credentials after the 2026-11-16 upgrade. It needs
direct access to the database file, not a running server or a token.

Usage (from ``backend/``):

    .venv/bin/python -m app.rotate_sign_in_token --db dev.db --email admin@lexgraph.local
    .venv/bin/python -m app.rotate_sign_in_token --db dev.db --user-id USER_ID
    .venv/bin/python -m app.rotate_sign_in_token --db dev.db --list-legacy

Without ``--db``, ``LEXGRAPH_DATABASE_URL`` is used. Rotating prints the new
token exactly once; only its hash is stored and the previous token stops
working immediately. ``--list-legacy`` lists accounts whose token is still
their public user id (left by the ``m20261116_sign_in_tokens`` migration),
which every member who can see that id could use to sign in as them.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.rotate_sign_in_token", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--db", help="SQLite file (default: LEXGRAPH_DATABASE_URL)")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--user-id", help="rotate the token of the account with this id")
    target.add_argument("--email", help="rotate the token of the account with this email")
    target.add_argument(
        "--list-legacy",
        action="store_true",
        help="list accounts that still sign in with their public user id",
    )
    args = parser.parse_args(argv)

    from sqlalchemy import inspect, select

    from app.auth import issue_sign_in_token, legacy_sign_in_user_ids
    from app.config import get_settings
    from app.db import make_engine, make_session_factory
    from app.models.user import User
    from app.routers.users import find_users_by_email

    url = f"sqlite:///{args.db}" if args.db else get_settings().database_url
    if url in ("sqlite://", "sqlite:///:memory:"):
        print(
            "error: pass --db PATH or set LEXGRAPH_DATABASE_URL to the server's database",
            file=sys.stderr,
        )
        return 1

    engine = make_engine(url)
    try:
        inspector = inspect(engine)
        if not inspector.has_table("users"):
            print("error: no users table; is this the right database?", file=sys.stderr)
            return 1
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "sign_in_token_hash" not in columns:
            print(
                "error: this database predates sign-in tokens; upgrade it first "
                "(python -m app.migrate --db PATH; see docs/RUNBOOK.md, "
                "'Upgrading: sign-in tokens replace user-id sign-in')",
                file=sys.stderr,
            )
            return 1

        with make_session_factory(engine)() as session:
            if args.list_legacy:
                legacy = set(legacy_sign_in_user_ids(session))
                users = [u for u in session.execute(select(User)).scalars() if u.id in legacy]
                if not users:
                    print("No accounts sign in with their public user id.")
                    return 0
                print(f"{len(users)} account(s) still sign in with their public user id:")
                for user in sorted(users, key=lambda u: (u.display_name, u.id)):
                    print(f"  {user.id}  {user.email}  {user.display_name}")
                print("Rotate each with --user-id ID (or Admin -> User accounts).")
                return 0

            if args.user_id is not None:
                user = session.get(User, args.user_id)
            else:
                # Emails compare normalized, as everywhere (finding api:24).
                matches = find_users_by_email(session, args.email)
                if len(matches) > 1:
                    print(
                        "error: several accounts share that email address (ignoring letter "
                        "case): " + ", ".join(u.id for u in matches) + "; pass --user-id",
                        file=sys.stderr,
                    )
                    return 1
                user = matches[0] if matches else None
            if user is None:
                print("error: no such user account", file=sys.stderr)
                return 1

            token = issue_sign_in_token(user)
            session.commit()
            print(f"New sign-in token for {user.display_name} <{user.email}> (user id {user.id}).")
            print("Shown once; the previous token no longer works:")
            print(token)
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
