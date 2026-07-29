"""Sprint 2026-07-29-definition-links, item DL9 — `link-definitions` CLI
(ruling M6: parity with `enrich`; API route optional stretch, no frontend
UI this sprint).

`app.definition_links.cli` does not exist yet -- ModuleNotFoundError is the
expected RED signal. Mirrors `tests/integration/test_enrich_cli.py`'s exact
convention: `main(argv)` (the real entrypoint function, not a subprocess) is
invoked directly, reads `LEXGRAPH_DATABASE_URL` the same way
`app.config.get_settings()` does, and the resulting draft/proposed
assertions are verified through the REAL, ALREADY-REGISTERED
`GET /api/v1/assertions` route (`app/routers/assertions.py`) -- no new route
needed this sprint (M6: API route is optional stretch).

Invocation: `python -m app.definition_links.cli --matter-id <id>
--triggered-by-user-id <id>` (parity with `python -m app.enrich.cli`).
"""

from __future__ import annotations

import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _ingest_asset_protection_law(db_session, m: dict) -> None:
    from app.definition_links.ingest import ingest_wiki_law

    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=_read("חוק להגנת רכוש מופקד.wiki"),
    )


def test_link_definitions_cli_creates_proposed_assertions_from_ingested_articles(
    client, db_session, matter_with_users
):
    from app.definition_links.cli import main

    m = matter_with_users
    _ingest_asset_protection_law(db_session, m)

    exit_code = main(
        ["--matter-id", m["matter_id"], "--triggered-by-user-id", m["contributor_id"]]
    )
    assert exit_code == 0

    listing = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "origin": "system_generated"},
        headers=m["contributor_headers"],
    )
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) >= 1
    assert all(item["status"] == "proposed" for item in items)
    assert all(item["assertion_type"] in {"USES_DEFINITION", "DERIVES_FROM_LAW"} for item in items)


def test_link_definitions_cli_is_idempotent_on_rerun(client, db_session, matter_with_users):
    from app.definition_links.cli import main

    m = matter_with_users
    _ingest_asset_protection_law(db_session, m)

    main(["--matter-id", m["matter_id"], "--triggered-by-user-id", m["contributor_id"]])
    first_count = len(
        client.get(
            "/api/v1/assertions",
            params={"matter_id": m["matter_id"], "origin": "system_generated"},
            headers=m["contributor_headers"],
        ).json()["items"]
    )

    main(["--matter-id", m["matter_id"], "--triggered-by-user-id", m["contributor_id"]])
    second_count = len(
        client.get(
            "/api/v1/assertions",
            params={"matter_id": m["matter_id"], "origin": "system_generated"},
            headers=m["contributor_headers"],
        ).json()["items"]
    )
    assert second_count == first_count


def test_link_definitions_cli_reports_clear_failure_for_unknown_matter(
    matter_with_users, db_session
):
    from app.definition_links.cli import main

    exit_code = main(
        [
            "--matter-id",
            "00000000-0000-0000-0000-000000000000",
            "--triggered-by-user-id",
            matter_with_users["contributor_id"],
        ]
    )
    assert exit_code != 0


def test_link_definitions_cli_uses_definition_assertion_has_article_subject_and_definition_object(
    client, db_session, matter_with_users
):
    """Live-path shape check: a USES_DEFINITION assertion's subject/object
    entity types must actually reference the new Article/Definition
    entities (ruling M1/M2), not the placeholder SourceSpan-subject shape
    `app/enrich/pipeline.py` uses for its own, unrelated assertion type."""
    from app.definition_links.cli import main

    m = matter_with_users
    _ingest_asset_protection_law(db_session, m)
    main(["--matter-id", m["matter_id"], "--triggered-by-user-id", m["contributor_id"]])

    listing = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "origin": "system_generated"},
        headers=m["contributor_headers"],
    )
    uses_items = [
        item for item in listing.json()["items"] if item["assertion_type"] == "USES_DEFINITION"
    ]
    assert len(uses_items) >= 1
    assert uses_items[0]["subject_entity"]["type"] == "Article"
    assert uses_items[0]["object_entity"]["type"] == "Definition"
