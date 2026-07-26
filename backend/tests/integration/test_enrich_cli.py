"""Track B, item B1 — enrichment CLI command (gate G5).

Director scope amendment (2026-07-26): document acquisition/scraping is out
of scope. This CLI runs the enrichment pass over documents/spans ALREADY in
the local DB (seeded here via the same conftest raw-SQL helpers every other
integration test uses) -- it does not read or parse any file.

`app.enrich.cli` does not exist yet -- ModuleNotFoundError is the expected
RED signal. The CLI's `main(argv)` is invoked directly (the real entrypoint
function, not a subprocess) and must read `LEXGRAPH_DATABASE_URL` the same
way `app.config.get_settings()` does, so it operates on the exact sqlite
file the `client`/`db_session` fixtures already point at.
"""

from __future__ import annotations

from tests.conftest import seed_document, seed_source_span


def _seed_document_with_span(db_session, m: dict) -> tuple[str, str]:
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(
        db_session,
        document_id=doc_id,
        matter_id=m["matter_id"],
        quote_text="This obligation shall survive termination of this Agreement.",
    )
    return doc_id, span_id


def test_enrich_cli_creates_draft_assertions_from_existing_spans(
    client, db_session, matter_with_users
):
    from app.enrich.cli import main

    m = matter_with_users
    _seed_document_with_span(db_session, m)

    exit_code = main(
        [
            "--matter-id",
            m["matter_id"],
            "--triggered-by-user-id",
            m["contributor_id"],
        ]
    )
    assert exit_code == 0

    listing = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "origin": "model_suggested"},
        headers=m["contributor_headers"],
    )
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) >= 1
    assert all(item["status"] != "accepted" for item in items)


def test_enrich_cli_is_idempotent_on_rerun(client, db_session, matter_with_users):
    from app.enrich.cli import main

    m = matter_with_users
    _seed_document_with_span(db_session, m)

    main(["--matter-id", m["matter_id"], "--triggered-by-user-id", m["contributor_id"]])
    first_count = len(
        client.get(
            "/api/v1/assertions",
            params={"matter_id": m["matter_id"], "origin": "model_suggested"},
            headers=m["contributor_headers"],
        ).json()["items"]
    )

    main(["--matter-id", m["matter_id"], "--triggered-by-user-id", m["contributor_id"]])
    second_count = len(
        client.get(
            "/api/v1/assertions",
            params={"matter_id": m["matter_id"], "origin": "model_suggested"},
            headers=m["contributor_headers"],
        ).json()["items"]
    )

    assert second_count == first_count


def test_enrich_cli_reports_clear_failure_for_unknown_matter(matter_with_users, db_session):
    from app.enrich.cli import main

    exit_code = main(
        [
            "--matter-id",
            "00000000-0000-0000-0000-000000000000",
            "--triggered-by-user-id",
            matter_with_users["contributor_id"],
        ]
    )
    assert exit_code != 0
