"""Bootstrap the FIRST workspace + admin on an EMPTY database (Gate G1).

Usage (from ``backend/``, after ``pip install -e '.[dev]'``):

    .venv/bin/python -m app.bootstrap --db dev.db
    .venv/bin/python -m app.bootstrap --org-name "Acme Legal" \\
        --matter-name "Acme v. Zenith" --user-name "Root Admin" \\
        --user-email root@acme.test

    LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/python -m app.bootstrap

Creates one organization + repository + matter + the first user, with an
``admin`` ``matter_roles`` row on that matter, then prints the new user's
id clearly — that id IS the sign-in credential (R3, ``app/auth.py``'s
test-token seam: ``Authorization: Bearer <user_id>``), so an operator can
hand it straight to the first admin.

Refuses to run on a NON-empty database (any existing ``users`` row) — no
silent mutation on top of an already-bootstrapped workspace. Serve the
result the same way ``app/seed_demo.py`` does:

    LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/uvicorn app.main:app --port 8000
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite file to create (sets LEXGRAPH_DATABASE_URL; mirrors app/seed_demo.py). "
        "If omitted, LEXGRAPH_DATABASE_URL is read directly from the environment.",
    )
    parser.add_argument("--org-name", default="LexGraph", help="organization name")
    parser.add_argument("--matter-name", default="General Matter", help="first matter's name")
    parser.add_argument("--user-name", default="Admin", help="first admin's display name")
    parser.add_argument(
        "--user-email", default="admin@lexgraph.local", help="first admin's email"
    )
    args = parser.parse_args(argv)

    if args.db:
        os.environ["LEXGRAPH_DATABASE_URL"] = f"sqlite:///{args.db}"

    # Imports happen after the env var is set so create_app() binds to the
    # target database (same convention as app/seed_demo.py).
    from sqlalchemy import select

    from app.db import Base
    from app.main import create_app
    from app.models.matter import Matter
    from app.models.matter_role import MatterRole
    from app.models.organization import Organization
    from app.models.repository import Repository
    from app.models.user import User

    app = create_app()
    Base.metadata.create_all(bind=app.state.engine)
    session = app.state.session_factory()

    try:
        # Empty-DB guard: refuse on top of an already-bootstrapped
        # workspace instead of silently creating a second org/matter/user.
        existing_user = session.execute(select(User.id).limit(1)).first()
        if existing_user is not None:
            print(
                "Refusing to bootstrap: the database already has users. "
                "Bootstrap only runs on an empty database — nothing was changed."
            )
            return 1

        org = Organization(id=str(uuid.uuid4()), name=args.org_name)
        repo = Repository(
            id=str(uuid.uuid4()), organization_id=org.id, name=f"{args.org_name} Repository"
        )
        matter = Matter(id=str(uuid.uuid4()), repository_id=repo.id, name=args.matter_name)
        user = User(id=str(uuid.uuid4()), email=args.user_email, display_name=args.user_name)
        admin_role = MatterRole(
            id=str(uuid.uuid4()), user_id=user.id, matter_id=matter.id, role="admin"
        )
        session.add_all([org, repo, matter, user, admin_role])
        session.commit()

        print(f"Bootstrapped organization {org.name!r}, matter {matter.name!r}.")
        print(f"Sign-in user id (this IS the credential, R3): {user.id}")
        print("Serve it:")
        print("  LEXGRAPH_DATABASE_URL=<same db> .venv/bin/uvicorn app.main:app --port 8000")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
